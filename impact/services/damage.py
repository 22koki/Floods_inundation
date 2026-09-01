"""Depth-damage estimation using JRC global curves (Huizinga et al. 2017).

Breakpoints are the JRC residential/commercial/industrial depth-damage
fractions. Monetary values are in Kenyan Shillings (KES) using locally
calibrated replacement costs per m2; the JRC continental adjustment
factors only apply when adopting the JRC European baseline values.
"""

JRC_CURVES = {
    "residential": [
        (0.0, 0.0), (0.5, 0.39), (1.0, 0.59), (1.5, 0.72),
        (2.0, 0.85), (3.0, 0.95), (4.0, 0.98), (5.0, 1.0), (6.0, 1.0),
    ],
    "commercial": [
        (0.0, 0.0), (0.5, 0.11), (1.0, 0.34), (1.5, 0.49),
        (2.0, 0.60), (3.0, 0.92), (4.0, 1.0), (5.0, 1.0), (6.0, 1.0),
    ],
    "industrial": [
        (0.0, 0.0), (0.5, 0.11), (1.0, 0.34), (1.5, 0.49),
        (2.0, 0.60), (3.0, 0.92), (4.0, 1.0), (5.0, 1.0), (6.0, 1.0),
    ],
    "infrastructure": [
        (0.0, 0.0), (0.5, 0.10), (1.0, 0.30), (1.5, 0.45),
        (2.0, 0.60), (3.0, 0.90), (4.0, 1.0), (5.0, 1.0), (6.0, 1.0),
    ],
}

REGION_FACTORS = {
    "europe": 1.0,
    "africa": 0.47,
    "asia": 0.51,
    "north_america": 0.49,
    "south_america": 0.42,
    "oceania": 0.55,
}


def damage_fraction(depth_m, bldg_class="residential"):
    """Damage fraction (0-1) at a water depth, piecewise-linear on the JRC curve."""
    curve = JRC_CURVES.get(bldg_class, JRC_CURVES["residential"])
    depth = max(0.0, float(depth_m))
    if depth >= curve[-1][0]:
        return curve[-1][1]
    for (d0, f0), (d1, f1) in zip(curve, curve[1:]):
        if d0 <= depth <= d1:
            if d1 == d0:
                return f1
            return f0 + (f1 - f0) * (depth - d0) / (d1 - d0)
    return 0.0


def duration_multiplier(duration_h):
    """Damage uplift for prolonged submergence."""
    if duration_h <= 24:
        return 1.0
    if duration_h <= 48:
        return 1.05
    if duration_h <= 72:
        return 1.10
    return 1.20


def building_loss(depth_m, bldg_class, area_m2, value_per_m2, duration_h=24.0, region=None):
    """Economic loss (KES) for one building: fraction x replacement value.

    region: optionally apply a JRC continental adjustment factor when the
    per-m2 value comes from the JRC European baseline (e.g. region="africa").
    Local KES calibration should pass region=None (factor 1.0).
    """
    fraction = min(1.0, damage_fraction(depth_m, bldg_class) * duration_multiplier(duration_h))
    factor = REGION_FACTORS.get(region, 1.0) if region else 1.0
    return fraction * float(area_m2) * float(value_per_m2) * factor
