"""Composite ward risk index (WMO impact-based forecast convention).

Risk = (Hazard x Exposure x Vulnerability)^(1/3), normalized to 0-100 and
classified into four color-coded alert bands.
"""
import math

BANDS = (
    (25.0, "Low"),
    (50.0, "Watch"),
    (75.0, "Warning"),
    (float("inf"), "Extreme"),
)


def hazard_index(max_depth_m, extent_fraction, duration_h):
    """Hazard (0-1) from max depth, flooded extent fraction, and duration."""
    depth = min(1.0, max(0.0, max_depth_m) / 2.0)
    extent = min(1.0, max(0.0, extent_fraction))
    duration = min(1.0, max(0.0, duration_h) / 72.0)
    return depth * 0.5 + extent * 0.3 + duration * 0.2


def exposure_index(loss_kes, loss_cap_kes):
    """Exposure (0-1) normalized against a ward loss cap."""
    if loss_cap_kes <= 0:
        return 0.0
    return min(1.0, max(0.0, loss_kes) / loss_cap_kes)


def composite_risk(hazard, exposure, vulnerability):
    """Geometric-mean composite score on a 0-100 scale."""
    factors = [max(0.0, hazard), max(0.0, exposure), max(0.0, vulnerability)]
    if any(f <= 0.0 for f in factors):
        return 0.0
    return 100.0 * math.prod(factors) ** (1.0 / 3.0)


def risk_band(score):
    for upper, label in BANDS:
        if score < upper:
            return label
    return BANDS[-1][1]
