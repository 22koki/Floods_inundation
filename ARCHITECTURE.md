# FloodSentry — End-to-End Impact-Based Flood Intelligence System

**Design thesis:** Bypass gauge dependency by treating *satellite precipitation + global hydrography + deep learning* as a virtual gauge network, then convert discharge forecasts into *volumetric, asset-level, monetary impact* — the unit disaster agencies actually act on. The system is organized as a directed pipeline: **Forcings → ML Streamflow → Routing/Inundation → Exposure → Damage/Risk → Alerting**, with every intermediate artifact versioned and queryable.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ INGEST (Dagster assets → S3)                                            │
│  ECMWF HRES/ENS (GRIB)  GPM IMERG-Early (HDF5)  ERA5-Land/CHIRPS (NC)   │
│  Copernicus GLO-30 DEM  HydroBASINS/HydroATLAS  OSM/Overture  WorldPop  │
└──────────────┬──────────────────────────────────────────────────────────┘
               ▼
┌──────────────────────────────┐   ┌────────────────────────────────────┐
│ FEATURE ENGINEERING          │   │ FEATURE STORE                      │
│ bias correction, HRES grid → │──▶│ Zarr (gridded) · Parquet (tabular) │
│ HydroBASINS L12, HAND, TWI,  │   │ PostGIS (vector) · static attrs    │
│ flow accumulation, upstream  │   │ keyed by hybas_id / valid_time     │
└──────────────────────────────┘   └──────────────┬─────────────────────┘
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ML FORECAST ENGINE (NeuralHydrology, MLflow registry)                   │
│ LSTM seq2seq (global Caravan-pretrained) → Q(t) per L12 basin, 0–168h   │
│ GNN river-network routing → Q at every river node                       │
│ Flash-flood module: IMERG nowcast + saturation index (0–3h)             │
└──────────────┬──────────────────────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────┐   ┌──────────────────────────────┐
│ VOLUMETRIC & HYDRODYNAMIC LAYER      │   │ INUNDATION                   │
│ m³/cell → m³/sub-basin → m³/ward     │──▶│ RIM2D/HAND depth grids       │
│ Muskingum-Cunge / RAPID / LISFLOOD-  │   │ (COG, tiled) per lead time   │
│ FP for priority urban reaches        │   └──────────────┬───────────────┘
└──────────────────────────────────────┘                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ IMPACT ENGINE (PostGIS + GeoPandas)                                     │
│ ST_Intersection(flood, assets) → exposed km, buildings, critical sites  │
│ JRC depth-damage × duration → USD loss · fragility → network disruption │
│ WorldPop × depth → displaced persons · composite ward risk index        │
└──────────────┬──────────────────────────────────────────────────────────┘
               ▼
   FastAPI (async) + Redis  ──▶  MapLibre/deck.gl dashboard, TiTiler/PMTiles
                              └▶  SMS/email/webhook impact-based alerts
```

---

## 1. Multi-Source Data Ingestion & Basin Feature Engineering

### 1.1 Meteorological forcing pipelines

| Source | Role | Resolution / latency | Access |
|---|---|---|---|
| **ECMWF HRES** | Deterministic forecast forcing (0–144 h) | 0.25°, 3-hourly, 2 runs/day, ~4–7 h latency | ECMWF Open Data (AWS/Azure mirrors), GRIB2 |
| **ECMWF ENS** | Probabilistic ensemble (51 members) → uncertainty bands | 0.25°/0.5° | ECMWF Open Data, MARS if licensed |
| **GPM IMERG Early/Late** | Observed precip, nowcast initialization, flash floods | 0.1°, 30-min, 4 h/14 h latency | GES DISC, S3 bucket |
| **IMERG Final / MSWEP / CHIRPS** | Historical training + bias correction | 0.1°/0.05°, monthly lag | GES DISC / GloH2O / UCSB |
| **ERA5-Land** | Historical forcing (training), PET, 2 m temp, radiation | ~9 km, hourly | Copernicus CDS |
| **National Met Service + gauges** | Validation & bias-correction anchors only — *never a system dependency* | station | partner feeds, WIS |

**Pipeline design (Dagster software-defined assets):**

- One idempotent asset per `(source, variable, init_time)`; downloads land in `s3://floodsentry/raw/{source}/{yyyymmdd}/` with original formats (GRIB2/HDF5/NetCDF) kept as the immutable raw zone.
- Conversion stage: `cfgrib` / `xarray` open GRIB → normalize units (`tp` m→mm, accumulate windows → rates) → **regrid to the HydroSHEDS 0.05° analysis grid** (`xesmf` conservative regridding) → write chunked **Zarr** (`chunks = {time: 720, lat: 100, lon: 100}`) with a kerchunk index for lazy reads.
- **Bias correction:** quantile delta mapping (QDM) of HRES/ENS against IMERG-Final/MSWEP climatology per basin and season (monsoon regimes dominate error); correction factors cached per `hybas_id`.
- QA gates: physical range checks, cross-source divergence flags (HRES vs IMERG > 3σ raises a degraded-mode asset event), provenance stamped into a PostGIS `data_lineage` table.

### 1.2 Terrain, drainage, and basin features

- **DEM:** Copernicus **GLO-30** (30 m) or **FABDEM** (forest/buildings removed — preferred for hydrology). Tiles staged in S3, mosaicked per region of interest.
- **Hydro-conditioning:** `pysheds`/`whitebox` produce D8 flow direction, **flow accumulation**, stream ordering; **HAND** (Height Above Nearest Drainage) and **TWI** rasters — these two are the backbone of Module 3's inundation mapping.
- **HydroBASINS level 12** (~3 km² median polygons) = the atomic spatial unit of the whole system. Each polygon stores: `hybas_id`, Pfafstetter code, upstream area, **flow length to outlet**, downstream `hybas_id` (network graph for routing).
- **HydroATLAS v1.1** supplies ~287 static attributes per basin (climate, land cover, soil, geology, population, dams, upstream mean precip) — consumed *directly as LSTM static features*, guaranteeing training (Caravan) and inference use identical feature semantics.
- **HydroRIVERS** (vectors) enriched with RiverATLAS attributes: width, depth, discharge, slope, Manning's n estimate → routing parameters (Module 3).
- Precompute once, version as `features_v{n}`: Zarr for rasters (HAND, TWI, flowdir, accum), Parquet keyed by `hybas_id` for tabular statics, PostGIS for basin/river/ward polygons with GIST indexes.

---

## 2. Hydrological & ML Forecasting Engine

### 2.1 Core streamflow model — LSTM sequence-to-sequence

Trained with the **NeuralHydrology** library (Kratzert et al. lineage) on **Caravan (~7,000 basins)** + CAMELS families:

- **Encoder:** 365 days of history (precip, tmin/tmax, PET via Hargreaves, ERA5-Land soil moisture, IMERG obs).
- **Decoder:** 168 h (7 days) using bias-corrected HRES/ENS forcing.
- Architecture: 2-layer LSTM, hidden 256, dropout 0.4; static attributes injected at cell state (Kratzert **EA-LSTM** variant — embedding of statics, proven best for regionalization).
- Loss: composite — `0.6·NSE + 0.25·log-space MSE (low flows) + 0.15·weighted peak-flow MSE`, plus a flow-matching score term on the top 2% quantile. Optimize for *warning skill at flood stage*, not mean flow.
- **Probabilistic mode:** run the 51-member ENS through the decoder → discharge quantiles (Q10/Q50/Q90); cheap alternative: MC-dropout ensembles (5 members) when ENS download budget is tight.

### 2.2 Alternative/complementary architectures

- **Transformer (temporal):** PatchTST / Temporal Fusion Transformer head for long-horizon dependence; TFT's variable-selection network doubles as interpretability ("this alert driven by 72 h HRES precip over the upper basin"). Kept as challenger model, promoted via MLflow champion/challenger gating on KGE.
- **Graph Neural Network:** nodes = HydroBASINS L12 outlets, edges = drainage topology; message passing lets upstream states inform downstream basins — the research-backed path for **routing emulation and ungauged transfer** (Section 2.4), matching the design of large-scale operational systems (e.g., Google's flood-hub LSTM + network routing; Nearing et al. 2024).

### 2.3 Flash-flood module (0–3 h, pluvial/convective)

- IMERG-Early 30-min + `pysteps` optical-flow extrapolation nowcast → saturation-conditioned flash-flood index: `FFI = f(nowcast depth, HAND, TWI, LSTM antecedent soil state, basin response time from Caravan attributes)`. This catches urban cloudbursts that HRES at 0.25° cannot see.

### 2.4 Ungauged basins — transfer learning strategy

1. **Global pretraining** on all of Caravan (shared-feature EA-LSTM).
2. **Spatial-embedding transfer:** learn catchment embeddings via contrastive pretraining (similar climate/terrain/land-cover basins embed close); for a target ungauged basin, initialize with the embedding-nearest gauged basins' weights, then fine-tune — the Feng et al. spatial-embedding approach, which shows larger skill gains in data-sparse (African) basins than in gauge-rich ones.
3. **Foundation-model anchor:** where available, blend predictions from pretrained global foundation forecasts (e.g., Google flood-hub–class models) as a prior; the local LSTM learns residual corrections wherever even a few historic gauges exist.
4. **Validation without gauges:** compare against GloFAS reforecasts and satellite-observed inundation (Sentinel-1, JRC GFM) — event-level recall, not continuous flow, becomes the metric.

---

## 3. Volumetric Runoff & Hydrodynamic Routing

### 3.1 Discharge depth → volume (m³) — the accounting layer

Per grid cell *i* at time *t*: `V_i(t) = r_i(t)·A_i / 1000` (runoff depth mm × cell area m² → m³). Aggregation is a masked Zarr reduction over HydroBASINS L12 with area-weighted overlap for ward boundaries:

```python
# per sub-basin, per timestep
V_basin = (runoff_zarr.where(basin_mask, drop=True).sum() * cell_area_m2 / 1000)  # m³
V_ward  = sum(V_cell * areal_fraction(cell, ward))                                  # GeoPandas overlay
```

Cumulative event volume at any node: `V = ∫₀ᵀ Q(t) dt` (trapezoidal over the forecast horizon) — reported per **grid cell, sub-basin, and administrative ward**. These volumetrics are the headline numbers for reservoir managers and the coupling input to hydrodynamics.

### 3.2 Routing ML discharge through the network

Three tiers, chosen per reach by order/criticality:

1. **Muskingum-Cunge (kinematic wave)** on HydroRIVERS segments — channel geometry from RiverATLAS (`w ∝ Q^b`), slope from DEM; wave celerity `c_k = 5v/3`; sub-stepped to satisfy the Courant condition. Fast, stable, parameter-free at scale.
2. **RAPID** (Muskingum on >10⁴ reaches solved as a matrix ODE with `scipy.linalg.expm`) for the full national network — this is what NFIE/NWM-class systems use.
3. **2D hydrodynamics (LISFLOOD-FP subgrid / HEC-RAS 2D)** *only* for priority urban reaches and below major dams — full shallow-water propagation, 10–30 m grid, driven by routed boundary Q and rainfall (pluvial + fluvial combined).
4. **GNN routing surrogate** (trained on Muskingum-Cunge + LISFLOOD outputs) replaces tiers 1–2 in production inference — 100–1000× faster, enabling 51-member ensembles through the network.

**Discharge → depth:** at every river node, `Q(t)` maps to depth via **synthetic rating curves** precomputed from RIM2D (Bristol's event-based global flood model) per HydroBASINS unit — the same coupling GloFAS uses operationally — or via HAND reach-specific depth-area curves where RIM2D tiles are unavailable.

**Inundation extent & depth profiling:** rasterize routed depth per lead time onto GLO-30 → publish as **COGs**; per-ward water-depth time series and duration-above-threshold (e.g., hours > 0.3 m) feed directly into Module 5. Coupling loop: LSTM Q → routing → depth → (optional) feedback into the flash-flood saturation index.

---

## 4. Asset Exposure & Infrastructure Vulnerability Mapping

### 4.1 Vector asset warehouse (PostGIS)

- **OSM via osm2pgsql** (`--hstore`): `highway=*` hierarchy, `railway`, `bridge`, `building` (+ `building:type`), `amenity=hospital/school`, `man_made=water_works`, `power=substation/plant`.
- **Building completeness fix for data-sparse regions:** Overture/Microsoft/Google Open Buildings footprints as the geometric truth layer, OSM for classification; reconcile by spatial join (footprint ↔ nearest classified OSM building).
- National layers where available (ward boundaries, gazetted roads) stored in `assets.*` schemas; everything indexed: `CREATE INDEX ON assets.buildings USING GIST (geom);`

### 4.2 Intersection pipeline

Ingest the depth COG into PostGIS raster, then set-based analysis (or GeoPandas/Shapely 2.0 + rasterio for offline batch — same logic, both paths maintained):

```sql
-- submerged road length per ward and road class (meters, geodesic)
SELECT w.ward_id, a.highway,
       SUM(ST_Length(ST_Intersection(ST_Transform(a.geom, 4326), f.geom)::geography)) AS submerged_m
FROM flood_polygons f
JOIN assets.roads a ON ST_Intersects(a.geom, f.geom)
JOIN admin.wards w  ON ST_Intersects(a.geom, w.geom)
GROUP BY 1, 2;
```

- **Depth attribution per asset:** roads/rail → max depth sampled at 10 m intervals along the intersecting segment (`ST_LineSubstring` + `ST_Value`); buildings → depth at centroid + flood-area ratio of footprint; bridges → upstream/downstream node depth + scour check against river velocity.
- **Outputs per event/lead time:** km of road by class, rail km, bridge count, buildings (count + m² by type), critical-facility list with *predicted water depth at the facility* — precomputed and cached per event in `impact.exposure_{event_id}` (PostGIS partitions by ward).

---

## 5. Impact-Based Damage & Risk Estimation

### 5.1 Depth–damage economic loss

- **JRC global depth–damage functions** (Huizinga et al. 2017): per-building-class curves `d(%) = f(h)`; monetary values in **Kenyan Shillings (KES)** with locally calibrated per-m² replacement costs; JRC continental adjustment factors (Africa ≈ 0.47× European baseline) apply only when importing JRC European unit values.
- Building → curve class mapping from OSM tags; **duration uplift**: damage multiplier increases for submergence > 48–72 h (curve extension); velocity-based fragility caps (structural washout) for high-energy zones.
- `Loss_building = Damage% (h, duration) × replacement_value(m² × area)`; aggregated to ward/event with ensemble quantiles (Q10–Q90 loss, propagated from ENS discharge spread).

### 5.2 Fragility & network disruption

- Threshold/fragility functions per asset class: substation switchgear outage at ~0.5–0.6 m, rail ballast washout by velocity, bridge scour fragility curves, road impassability at depth > 0.3 m (light vehicle) / 0.6 m.
- Feed disrupted edges into an **OSMnx network analysis**: disconnected population, detour ratios, hospital-accessibility loss — "which communities lose their nearest hospital" is a headline alert.

### 5.3 Population & displacement

- **WorldPop constrained 100 m** (plus GRID3 settlement masks) intersected with depth grids: `People_affected = Σ pop(depth > 0.1 m)`, `Displaced ≈ Σ pop·p_displace(depth)` with depth-tiered displacement rates (low/moderate/high bands).
- **Composite ward risk index** (WMO impact-based-forecast convention):
  `Risk = (Hazard · Exposure · Vulnerability)^(1/3)`, normalized 0–100 → four alert bands (Low/Watch/Warning/Extreme, color-coded). Hazard = depth×extent×duration; Exposure = USD loss + asset counts; Vulnerability = WorldPop poverty/SVI + informal-settlement share + age structure.
- Every ward row on the dashboard carries the **why-line**: "Extreme — Q50 exceeds 1-in-20y at X river; 4,200 people, KES Y in assets, 2 schools exposed; uncertainty Q10–Q90 = …".

---

## 6. MLOps, Deployment & Scalability

### 6.1 Stack & runtime topology

| Layer | Technology |
|---|---|
| Orchestration | **Dagster** (asset lineage, partitions by `init_time`), cron-triggered per model cycle |
| Storage | **AWS S3** raw/processed zones; **Zarr** + kerchunk for gridded, Parquet for tabular, COG for inundation rasters |
| Database | **PostgreSQL 16 + PostGIS 3.4** (RDS), `pg_partman` on event tables, Redis cache |
| ML | **PyTorch + NeuralHydrology**, **MLflow** registry, ONNX export for serving; GPU batch inference (EKS/Fargate Spot + one GPU node) |
| Serving | **Django 4.2 + Django REST Framework** (GeoDjango on PostGIS): `/api/forecast/{hybas_id}/`, `/api/events/{id}/ward-risk/`, `/api/events/{id}/flood-polygons.geojson` |
| Viz | **Django templates + MapLibre GL** (CDN); TiTiler for dynamic COG tiles, PMTiles for static vector tiles |
| Alerts | SMS/email (e.g., Africa's Talking / Twilio) + webhook to disaster-ops platforms, driven by risk-band crossings |
| Delivery | Gunicorn + Docker, docker-compose (dev) → ECS/EKS; GitHub Actions CI |

**Event-driven flow per model cycle (2×/day + 30-min flash-flood ticks):** ingest assets materialize → feature view refreshed → LSTM/GNN inference → routing → depth COGs published → PostGIS impact tables rebuilt → dashboard + alerts. Everything idempotent and restartable from any asset node.

### 6.2 Engineering discipline

- **Data contracts:** Pydantic schemas per API asset; Great Expectations on ingest (ranges, completeness, timeliness SLAs — an alert if HRES is >9 h late).
- **Testing:** pytest unit tests on routing/volume math against analytical solutions (SCS triangular hydrograph, mass conservation in Muskingum); golden-file tests on damage aggregation; seeded mini-basin integration test in CI.
- **Model governance:** MLflow champion/challenger with KGE + flood-event CSI gates; Evidently monitors for forcing drift (IMERG vs HRES divergence); scheduled backtesting against ERA5 reforecasts and satellite-observed flood events.
- **Scalability:** partition inference across basins (embarrassingly parallel), Zarr chunk-aligned reads, impact recomputation only for basins where Q50 exceeds alert threshold (lazy impact cascades).

### 6.3 Hyper-local downscaling (urban flash floods from coarse grids)

1. **Precipitation super-resolution:** UNet/ESRGAN-style model mapping HRES 0.25° → 0.01° conditioned on GLO-30 terrain, land mask, and IMERG 0.1° texture (trained on paired ERA5-Land/IMERG–radar-era events); mass budget preserved via conservative rescaling of the field post-inference.
2. **Nowcast fusion:** IMERG-Early extrapolation (`pysteps`) blends with the downscaled field for 0–3 h.
3. **Pluvial surrogate:** CNN trained on hundreds of synthetic SWMM + LISFLOOD-FP urban simulations (rainfall × drainage × DEM parameter sweeps) predicts 10 m urban water depth in seconds — replacing 2D hydrodynamics in routine inference; the physical 1D-2D model runs nightly for the top-5 riskiest wards as ground truth.
4. **Uncertainty communication:** every downscaled product ships with an ensemble spread layer; the dashboard shows depth bands, not single-value illusions.

---

## 7. Validation, Phasing & Repository Layout

**Validation protocol:**
- (a) hydrology — KGE/NSE vs held-out gauges and Caravan test basins;
- (b) inundation — CSI/F1 vs Sentinel-1 JRC-GFM historical events;
- (c) impact — reconstruction against documented disaster reports (EM-DAT / national bulletins);
- (d) operational — end-to-end latency from HRES publication to ward alert on the dashboard.

**Phasing (MVP → production):**

- **MVP:** HRES + IMERG ingest → Caravan-pretrained LSTM (no fine-tuning) → HAND/RIM2D-SRC depth mapping → OSM exposure + JRC damage → ward table + MapLibre dashboard. Single region, deterministic forcing only.
- **Phase 2:** ENS probabilistics, RAPID routing, fragility/network disruption, displacement module, SMS alerts.
- **Phase 3:** GNN routing surrogate, urban downscaling + pluvial surrogate, full MLOps hardening, multi-country scale-out.

**Repo skeleton:**

```
hackathon/  (Django monorepo)
├── config/            # settings, urls, wsgi
├── hydrology/         # models + services (volumes, routing) + management commands
├── exposure/          # asset/flood models + spatial services
├── impact/            # damage (KES), risk index, impact service
├── api/               # DRF serializers/views/urls
├── dashboard/         # MapLibre view
├── templates/         # dashboard template
└── tests              # per-app Django test suites
```

**Validation anchor — February–March 2026 Nairobi flash floods.** The MVP is calibrated to the observed event: Kenya Met warning 25 Feb 2026; on 6 March ~18:30 a 3–5 h deluge delivered **160 mm at Wilson Airport, 145 mm at Moi Air Base, 117 mm at Kabete, 112 mm at Dagoretti**; the Nairobi River burst its banks flooding Mombasa Road and Uhuru Highway; **71 vehicles swept away in Nairobi on day one, ~3,500 Nairobi households affected, 27 Nairobi deaths in a single night**, and ~34,765 people displaced nationally by end of March. The demo corridor uses the real river system (Nairobi, Mathare, Gitathuru, Ngong, Mbagathi) and affected informal-settlement wards (Mathare, Mukuru kwa Njenga, Kibra), with vulnerability indices reflecting settlement density; reconstruction output (highest risk in Mukuru kwa Njenga, ~10³–10⁴ displaced corridor-wide) is validated against these reported figures.

**Seasonal outlook module (El Niño OND 2026).** ENSO-conditioned scenario planning: the `outlook` app translates the seasonal forecast (Kenya Met 26 Aug 2026: above-average OND rains, 85–90% probability of above-normal; IRI 19 Aug 2026: El Niño intensifying, OND peak, >90% odds of a strong event; positive IOD compounding) into three design storms run through the full pipeline — baseline neutral OND 100 mm, moderate El Niño +30% (130 mm), strong El Niño +60% (160 mm = the 6 March 2026 analogue) — and aggregates per-ward displaced/loss/band into `SeasonalWardRisk` (API: `/api/seasonal-outlooks/latest/`). This is the S2S layer: LSTM 7-day skill → flash-flood 0–3 h → seasonal El Niño scenarios for preparedness planning.

**Key differentiators:** identical feature semantics between Caravan training and inference (HydroATLAS-native design), volume (m³) as the first-class currency connecting ML output to hydrodynamics and impact, local KES impact accounting, and the gauge-optional validation loop via satellite flood observations.
