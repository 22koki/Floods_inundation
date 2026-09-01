"""Muskingum channel routing with automatic reach sub-division.

The stability condition 2KX <= dt <= 2K(1-X) must hold for each routing
step; long reaches are split into N sub-reaches (Ponce 1978) so it holds
without changing the reporting timestep.
"""
import math

import numpy as np


def muskingum_coefficients(dt_h, K_h, X):
    denom = K_h - K_h * X + 0.5 * dt_h
    C0 = (-K_h * X + 0.5 * dt_h) / denom
    C1 = (K_h * X + 0.5 * dt_h) / denom
    C2 = (K_h - K_h * X - 0.5 * dt_h) / denom
    return C0, C1, C2


def muskingum_route(inflow, dt_h, K_h, X=0.2):
    """Route an inflow hydrograph (m3/s) through a reach of storage time K_h."""
    inflow = np.asarray(inflow, dtype=float)
    if inflow.size < 2 or K_h <= 0:
        return inflow.copy()
    n_reaches = max(
        1,
        math.ceil(2.0 * K_h * X / dt_h),
        math.ceil(2.0 * K_h * (1.0 - X) / dt_h),
    )
    k = K_h / n_reaches
    C0, C1, C2 = muskingum_coefficients(dt_h, k, X)
    out = inflow.copy()
    for _ in range(n_reaches):
        routed = np.empty_like(out)
        routed[0] = out[0]
        prev_in = out[0]
        prev_out = out[0]
        for i in range(1, out.size):
            o = C0 * out[i] + C1 * prev_in + C2 * prev_out
            routed[i] = max(o, 0.0)
            prev_in = out[i]
            prev_out = routed[i]
        out = routed
    return out


def travel_time_h(length_m, slope, manning_n, hydraulic_radius_m=2.0):
    """Reach travel time K from Manning velocity at a reference depth."""
    slope = max(slope, 1e-6)
    velocity = (1.0 / manning_n) * hydraulic_radius_m ** (2.0 / 3.0) * math.sqrt(slope)
    if velocity <= 0:
        return 1.0
    return length_m / velocity / 3600.0
