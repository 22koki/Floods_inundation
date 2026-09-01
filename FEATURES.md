# FloodSentry — Features Guide

A plain-language guide to everything the FloodSentry tool can do. It is written for first-time users — disaster-management staff, county officers, planners, and hackathon judges — no GIS or programming background required.

---

## 1. Interactive Flood Map (Dashboard)

**What it is:** a live map of Nairobi in your browser at `http://localhost:8000` — no login, no extra software.

- **See where the water goes.** Flooded areas are drawn on a real street map (OpenStreetMap) along the Nairobi River, Mathare, Gitathuru, Ngong, and Mbagathi river corridors.
- **Read depth at a glance.** Water depth is color-coded: light blue = ankle-deep (0.3–1 m), through to dark navy = above 3 m (life-threatening). A legend on the left explains every color.
- **Identify wards instantly.** Ward boundaries are outlined in the color of their risk band — green (Low), yellow (Watch), orange (Warning), red (Extreme).
- **Hover for the story.** Move your mouse over any ward to see its population, people affected, people displaced, buildings affected, submerged road length, facilities at risk, and the estimated loss in Kenyan Shillings.
- **Click a flooded area** to see its exact forecast depth and the lead time (hours from forecast start) at which it floods.
- **Click a ward in the table** to fly the map to it and inspect it up close.
- **Judge confidence.** A scale bar, zoom controls, and the event's submergence duration are always visible.

## 2. Flood Event Simulation ("What will 6 March 2026 look like?")

**What it is:** one command rebuilds the February–March 2026 Nairobi flash floods and shows the impacts that would follow the same rainfall today.

- **Calibrated to a real event.** The default simulation uses **160 mm of rain in 3–5 hours** — exactly what Wilson Airport recorded on 6 March 2026, when the Nairobi River burst its banks. You can simulate any other rainfall with a single option (e.g. 200 mm for a more extreme scenario).
- **Physically routed water.** Rainfall is converted to runoff, then routed downstream through the river network with the Muskingum method (which accounts for how flood waves travel and attenuate), so downstream wards flood *after* upstream ones — as in reality.
- **Full water accounting.** The system reports total event volume in cubic metres (m³) — the number reservoir and drainage engineers need.
- **Ends in impacts, not just maps.** Every simulation produces ward-level displaced persons, buildings affected, submerged roads, and economic loss in KES.

## 3. Ward Risk Assessment

**What it is:** a 0–100 risk score and an alert band for every ward, the way national meteorological services communicate warnings.

- **Four alert bands** follow international impact-based-forecasting practice: **Low / Watch / Warning / Extreme**, each shown in its standard color everywhere in the tool.
- **A transparent formula.** Risk combines three factors — hazard (how deep, how widespread, how long), exposure (value and assets hit), and vulnerability (how fragile the community is). The score is the geometric mean of the three, so no single factor can hide the others.
- **Vulnerability-aware.** Wards with dense informal settlements (Mathare, Mukuru kwa Njenga, Kibra) carry higher vulnerability weights, so equal flood depth produces higher risk where people are least able to cope.
- **Ranked table.** The dashboard sidebar lists wards from most to least at risk with displaced persons and KES loss per ward.

## 4. Asset & Infrastructure Exposure

**What it is:** a spatial database that answers "what exactly is in the water?"

- **Roads:** submerged length per ward, by road class — including key corridors like Mombasa Road and Uhuru Highway in the demo geography.
- **Buildings:** footprints intersected with flood polygons, each classified (residential / commercial / industrial) with its floor area.
- **Critical facilities:** hospitals, schools, water-treatment works, and power substations — each with the predicted water depth at its exact location. Facilities taking more than 10 cm of water are flagged "at risk".
- **Geodesic accuracy.** All length and area calculations are done in a metric projection (UTM 37S), so "3.2 km of road submerged" means 3,200 real metres.

## 5. Economic Damage Estimation (KES)

**What it is:** water depth converted into shillings, building by building.

- **International standards, local prices.** Damage percentages come from the Joint Research Centre (JRC) global depth–damage curves — the EU's reference method — but reconstruction values are **calibrated locally in Kenyan Shillings** (e.g. ~KES 45,000 per m² for residential construction), not converted from European prices.
- **Depth-dependent.** 50 cm of water damages ~39% of a home's value; 1 m ~59%; above 5 m the building is a total loss. Commercial and industrial buildings follow their own curves.
- **Duration matters.** Damage increases the longer a building stays submerged (a multiplier from 1.0 at 24 h up to 1.2 beyond 72 h), because the simulation tracks how long each area stays under water.
- **Every loss is traceable.** Each building's individual damage record (depth, duration, percentage, KES) is stored — ward totals are just the sum of auditable parts.

## 6. Population & Displacement Estimation

**What it is:** the human toll, estimated before it happens.

- **People affected** = population living inside the flooded extent.
- **People displaced** = affected population scaled by how deep and how long the flooding is — shallow brief flooding displaces few, deep prolonged flooding displaces most.
- **Ward-level numbers** that a county emergency team can plan shelters and relief food around.

## 7. Seasonal Outlook — El Niño OND 2026

**What it is:** the same flood pipeline driven by the *seasonal* forecast, so planners can prepare months ahead, not hours.

- **Based on the live forecast.** Kenya Met (26 Aug 2026) projects above-average October–December short rains with 85–90% likelihood of above-normal rainfall as the El Niño intensifies and peaks; the tool turns that outlook into concrete flood scenarios.
- **Three scenarios, one command.**
  - **Baseline** — a neutral-season short-rain event (100 mm)
  - **Moderate El Niño** (+30%, 130 mm) — comparable to recent enhanced short-rain seasons
  - **Strong El Niño** (+60%, 160 mm) — the 6 March 2026 event as the worst-case analogue
- **Side-by-side comparison.** The dashboard shows, per ward, how displaced-population figures escalate across the three scenarios, plus the worst-case risk band — e.g. Mukuru kwa Njenga escalates from ~4,700 displaced (baseline) to ~7,000 (strong), Warning → Extreme.
- **For budgeting and pre-positioning.** The KES loss spread across scenarios gives an evidence base for relief allocations before the rains start.

## 8. Data Access (API)

**What it is:** every number in the dashboard is also machine-readable for other systems.

| Endpoint | What you get |
|---|---|
| `/api/events/` | all simulated flood events |
| `/api/events/{id}/ward-risk/` | full ward risk table for one event |
| `/api/events/{id}/flood-polygons.geojson` | flood polygons as GeoJSON (drop into QGIS or any map tool) |
| `/api/events/{id}/wards.geojson` | ward boundaries with risk attributes |
| `/api/forecast/{basin}/` | the 7-day discharge forecast series for a river basin |
| `/api/seasonal-outlooks/latest/` | the full El Niño scenario matrix |

All JSON/GeoJSON — consumable by QGIS, Excel (via plugins), dashboards, SMS-gateway scripts, or the county GIS.

## 9. Data Management

- **One command setup.** `load_demo_data` builds the entire Nairobi demo geography — 5 river-corridor basins, 4 wards with real names and population, roads, ~120 buildings, 8 critical facilities — deterministically, so results are reproducible.
- **Admin interface.** Django's admin at `/admin` lets you inspect and edit every model (basins, rivers, wards, assets, events, results) without SQL.
- **Everything is queryable.** All data lives in your local PostgreSQL/PostGIS — the same database engine used by national spatial-data infrastructures.

## 10. Quality & Reliability

- **34 automated tests** cover the maths (volume integration, routing mass-conservation, damage curves, risk bands), the spatial logic (intersection services), the end-to-end pipeline, and every API endpoint.
- **Deterministic simulations.** The same command always produces the same result — essential for briefing documents and comparisons.
- **Validated against reality.** The reconstruction is calibrated to reported February–March 2026 impacts (rainfall gauge totals, households affected, displacement scale), and the model correctly ranks Mukuru kwa Njenga as the highest-risk ward.

---

## What FloodSentry Does *Not* Do (yet)

Being clear about scope — these are the next phases on the roadmap:

- **Live forecasts.** The current release simulates design storms (including the observed 6 March 2026 event). Ingesting live ECMWF/GPM forecasts and the machine-learning streamflow model (Caravan-pretrained LSTM) is Phase 2 — the architecture in `ARCHITECTURE.md` specifies it.
- **Real asset data.** The demo uses a stylized asset set in the real flood corridor; Phase 2 loads OpenStreetMap/Overture building footprints and road networks.
- **Alerts.** SMS/email dispatch is Phase 2; today the dashboard and API are the delivery channels.

---

## Quick Start (3 commands)

```bash
python manage.py load_demo_data        # build the Nairobi demo geography
python manage.py run_seasonal_outlook  # run baseline + moderate + strong El Niño scenarios
python manage.py runserver             # open http://localhost:8000
```

One single-event simulation instead: `python manage.py run_forecast` (160 mm, the 6 March 2026 analogue).
