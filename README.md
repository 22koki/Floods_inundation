# FloodSentry — Impact-Based Flood Monitoring, Forecasting & Damage Assessment

An end-to-end flood intelligence system for **Nairobi, Kenya** that bypasses river-gauge dependency: multi-source meteorological forcings → machine-learning precipitation–runoff → Muskingum routing → inundation polygons → PostGIS asset exposure → **KES damage and ward-level risk indices**. The MVP is calibrated against the **February–March 2026 Nairobi flash floods** (Nairobi River burst its banks on 6–7 March after 160 mm fell in 3–5 hours at Wilson Airport).

**Pipeline:** Forcings → ML Streamflow → Routing / Inundation → Exposure → Damage / Risk → Alerting

## Core Modules

| # | Module | Summary |
|---|--------|---------|
| 1 | Data Ingestion & Basin Features | ECMWF HRES/ENS, GPM IMERG, ERA5-Land; HydroBASINS/HydroATLAS + GLO-30 DEM (HAND, TWI) |
| 2 | ML Forecasting Engine | Caravan-pretrained LSTM seq2seq, GNN routing, transfer learning for ungauged basins |
| 3 | Volumetric Runoff & Routing | Runoff depth → m³ per cell/sub-basin/ward; Muskingum-Cunge, RAPID, LISFLOOD-FP |
| 4 | Asset Exposure | GeoDjango/PostGIS spatial joins: submerged roads, buildings, critical facilities |
| 5 | Damage & Risk (KES) | JRC depth-damage curves with local KES calibration, WorldPop displacement, ward risk index |
| 6 | MLOps & Deployment | Dagster, S3/Zarr, PostGIS, Django/DRF, Docker, MLflow; urban downscaling |

Full technical specification: **[ARCHITECTURE.md](ARCHITECTURE.md)** · User-facing capability guide: **[FEATURES.md](FEATURES.md)**

## Calibration: February–March 2026 Nairobi flash floods

The MVP's synthetic reconstruction reproduces the observed event profile:

| Observed (Feb–Mar 2026) | Value | Used as |
|---|---|---|
| Design rainfall (Wilson Airport, 6 Mar, 3–5 h) | **160 mm** | default `--storm-mm` |
| Other gauges (Moi Air Base / Kabete / Dagoretti) | 145 / 117 / 112 mm | ensemble spread context |
| Nairobi households affected | ~3,500 | displacement order-of-magnitude check |
| People displaced nationally by end March | ~34,765 | scenario scale reference |
| Vehicles swept away in Nairobi | 71 (day 1) | exposure sanity check |
| Corridor | Nairobi River, Mathare, Gitathuru, Ngong, Mbagathi; Mombasa Rd & Uhuru Hwy flooded | demo ward/river/road geography |

Demo wards: **Mathare, Mukuru kwa Njenga, Kibra, Embakasi South B** — vulnerability indices reflect informal-settlement density. A reconstruction run (`run_forecast`) flags Mukuru kwa Njenga as the highest-risk ward, consistent with reported impacts.

## Seasonal outlook — El Niño OND 2026

The `outlook` app converts the current seasonal forecast into scenario projections through the same pipeline. Forecast basis: **Kenya Met (26 Aug 2026)** above-average OND short rains with 85–90% likelihood of above-normal rainfall; **IRI (19 Aug 2026)** El Niño intensifying toward an OND 2026 peak (>90% odds of a strong event), compounded by a positive IOD.

| Scenario | Design storm (3–5 h) | Anchored to |
|---|---|---|
| Baseline (neutral OND) | 100 mm | typical short-rain event |
| Moderate El Niño (+30%) | 130 mm | 2019/2023-class OND seasons |
| Strong El Niño (+60%) | 160 mm | 6 Mar 2026 observed (Wilson Airport) |

```bash
python manage.py run_seasonal_outlook    # runs all 3 scenarios end-to-end
```

Results (reconstruction, Nairobi corridor): Mukuru kwa Njenga displaced **4,712 → 5,856 → 6,984** (Warning → Extreme → Extreme), Mathare **144 → 175 → 207**. API: `/api/seasonal-outlooks/latest/`; dashboard shows a per-ward scenario table.

## Tech Stack

- **Web:** Django 4.2 + GeoDjango + Django REST Framework on local PostgreSQL/PostGIS
- **ML:** Python, PyTorch + NeuralHydrology (planned Phase 2), ONNX Runtime
- **Geospatial:** GeoDjango ORM, GEOS/GDAL (bundled with Postgres.app), numpy
- **Viz:** Django templates + MapLibre GL (CDN)
- **Ops:** management commands as pipeline entry points, gunicorn + Docker for deploy

## Repository Layout

```
hackathon/
├── config/                # Django project (settings, urls, wsgi)
├── hydrology/             # Basin/River/Forecast models, m³ accounting, Muskingum routing
│   ├── services/          # volumes.py, routing.py
│   └── management/commands/
│       ├── load_demo_data.py   # Nairobi flood-corridor demo geodata
│       └── run_forecast.py     # storm → runoff → routing → polygons → impact
├── exposure/              # Ward/Road/Building/CriticalFacility/FloodPolygon + spatial services
├── impact/                # JRC depth-damage (KES), risk index, impact service
├── outlook/               # El Niño seasonal scenarios (baseline/moderate/strong) + aggregation
├── api/                   # DRF endpoints + GeoJSON views
├── dashboard/             # MapLibre dashboard view
├── templates/             # dashboard/index.html
└── tests/                 # per-app Django test suites (34 tests)
```

## Quickstart

```bash
# 1. Database (Postgres.app; empty POSTGRES_HOST = socket auth)
createdb floodsentry
psql -d floodsentry -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 2. Environment (see .env: DB credentials, GDAL/GEOS paths, loss cap)
pip install -r requirements.txt

# 3. Migrate + demo pipeline
python manage.py migrate
python manage.py load_demo_data
python manage.py run_forecast            # 160mm design storm (6 Mar 2026 analogue)
python manage.py run_seasonal_outlook    # El Nino OND 2026 scenario ensemble

# 4. Dashboard
python manage.py runserver               # http://localhost:8000
```

API: `/api/events/`, `/api/events/{id}/ward-risk/`, `/api/events/{id}/flood-polygons.geojson`, `/api/forecast/{hybas_id}/`

## Roadmap

1. **MVP (this repo)** — Django/GeoDjango pipeline, synthetic forcing, Muskingum routing, KES impact engine, MapLibre dashboard, calibrated to the 6–7 March 2026 event.
2. **Phase 2** — real ECMWF/IMERG ingestion (Dagster), Caravan-pretrained LSTM, ENS probabilistics, OSM/Overture assets, SMS alerts.
3. **Phase 3** — GNN routing surrogate, urban downscaling + pluvial surrogate, full MLOps hardening, multi-country scale-out.
