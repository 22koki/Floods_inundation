"""El Nino seasonal outlook: scenario definitions and helpers.

Scenarios translate the OND 2026 seasonal forecast (Kenya Met, 26 Aug 2026:
above-average short rains with 85-90% likelihood of above-normal rainfall
in some areas; IRI 19 Aug 2026: El Nino intensifying toward an OND peak
with >90% odds of a strong event) into flash-flood-producing design
storms run through the same pipeline as the March 2026 reconstruction.
"""

SCENARIOS = [
    {
        "key": "baseline",
        "name": "Baseline (neutral OND short rains)",
        "storm_mm": 100.0,
        "multiplier": 1.0,
    },
    {
        "key": "moderate",
        "name": "El Nino moderate OND (+30%)",
        "storm_mm": 130.0,
        "multiplier": 1.3,
    },
    {
        "key": "strong",
        "name": "El Nino strong OND (+60%, 6 Mar 2026 analogue)",
        "storm_mm": 160.0,
        "multiplier": 1.6,
    },
]

OUTLOOK_DEFAULTS = {
    "season_label": "OND 2026",
    "enso_phase": "El Nino",
    "probability_above_normal": 0.875,
    "source_note": (
        "Kenya Met OND 2026 seasonal forecast (issued 26 Aug 2026): above-average "
        "short rains, 85-90% likelihood of above-normal rainfall in some areas; "
        "El Nino intensifying (IRI quick look, 19 Aug 2026), expected to peak "
        "Oct-Dec 2026; positive IOD compounding. Scenarios express the flood-"
        "relevant 3-5h design storm: baseline neutral OND 100mm, moderate +30%, "
        "strong +60% (= 6 March 2026 Wilson Airport observed total)."
    ),
}
