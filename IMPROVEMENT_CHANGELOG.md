# FloodSentry — Improvement Changelog

## Project
**FloodSentry — Impact-Based Flood Monitoring, Forecasting & Damage Assessment**

## Intended users
FloodSentry is intended for county disaster-management teams, emergency-response planners,
meteorological/hydrological analysts, GIS officers, infrastructure planners, and humanitarian-response organisations.

## User bottleneck
Flood information often describes rainfall or flooding without directly answering operational questions:
- Which wards are most threatened?
- How deep could the water become?
- How many people may be affected or displaced?
- Which roads, buildings, and critical facilities are exposed?
- What could the approximate economic damage be?
- Where should response resources be prioritised?

FloodSentry converts a flood scenario into ward-level decision-support information.

## Baseline solution
The baseline is a deterministic single-event flood simulation. It:
1. converts rainfall to runoff;
2. routes water through the river system;
3. estimates inundation;
4. displays flood depth;
5. calculates basic ward-level impacts.

The demonstration is calibrated around the February–March 2026 Nairobi flash-flood event,
with a 160 mm design rainfall event over approximately 3–5 hours.

### Baseline limitation
The baseline mainly answers: **“What happens if this particular flood event occurs?”**

It is less useful for preparedness decisions that require comparing multiple plausible scenarios.

## Advanced solution
The advanced solution extends the baseline with:
- vulnerability-aware ward risk scoring;
- asset and infrastructure exposure;
- population and displacement estimates;
- economic damage estimates in KES;
- seasonal scenario comparison;
- an interactive dashboard;
- JSON/GeoJSON API access;
- deterministic testing and reproducibility controls.

## Iteration 1 — Impact-based ward risk
Flood depth alone does not describe consequences. The advanced workflow combines hazard,
exposure and vulnerability into a 0–100 ward risk score and groups wards into alert bands:
Low, Watch, Warning and Extreme.

## Iteration 2 — Asset and infrastructure exposure
Spatial analysis identifies roads, buildings, hospitals, schools, water-treatment facilities
and other critical infrastructure intersecting flood areas.

## Iteration 3 — Human impact estimation
The system estimates people affected and people displaced at ward level, allowing emergency
teams to plan shelter, relief and response resources.

## Iteration 4 — Economic damage estimation
Flood depth is converted into approximate economic losses in Kenyan shillings using
depth-damage relationships and locally calibrated reconstruction values.

## Iteration 5 — Seasonal scenario intelligence
The advanced workflow compares three design-storm scenarios:

| Scenario | Design storm |
|---|---:|
| Baseline | 100 mm |
| Moderate El Niño | 130 mm |
| Strong El Niño | 160 mm |

### Demonstrated improvement
Scenario coverage increases from **1 scenario to 3 scenarios**, a **3× increase in scenario coverage**.
The workflow therefore moves beyond single-event reconstruction toward seasonal preparedness.

## Iteration 6 — Decision-support dashboard
The dashboard lets users inspect flood depth, affected wards, population impacts,
infrastructure exposure, economic losses and ward risk interactively.

## Iteration 7 — Machine-readable API
Example endpoints include:

```text
/api/events/
/api/events/{id}/ward-risk/
/api/events/{id}/flood-polygons.geojson
/api/events/{id}/wards.geojson
/api/forecast/{basin}/
/api/seasonal-outlooks/latest/
```

## Iteration 8 — Reliability and reproducibility
The implementation includes deterministic simulations and automated tests covering model
mathematics, routing, spatial logic, risk bands, APIs and the end-to-end workflow.

## Final advanced pipeline
**Meteorological forcing → runoff → river routing → inundation → asset exposure → human impact → economic damage → ward risk → dashboard/API**

## Main failure mode
The current MVP is not yet a fully operational live-warning service. The present release
focuses on controlled/design scenarios and demonstration data. Live meteorological ingestion,
complete real-world asset inventories, probabilistic forecasting and SMS/email alerting remain
future work.

## Hot take
**Useful flood AI is not only about predicting water; the harder engineering challenge is turning uncertain physical forecasts into transparent, reproducible decisions about people, infrastructure and resources.**
