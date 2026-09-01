"""Volumetric runoff accounting: forecast depths and discharge to cubic meters."""
import numpy as np

try:
    _trapz = np.trapezoid
except AttributeError:  # numpy < 2.0
    _trapz = np.trapz


def cell_runoff_volume_m3(depth_mm, cell_area_m2):
    """V = r [mm] x A [m2] / 1000 for a single grid cell."""
    return float(depth_mm) * float(cell_area_m2) / 1000.0


def basin_runoff_volume_m3(depths_mm, cell_area_m2):
    """Total event volume generated over the cells of a sub-basin."""
    depths = np.asarray(depths_mm, dtype=float)
    return float(depths.sum() * cell_area_m2 / 1000.0)


def hydrograph_volume_m3(q_m3s, dt_h):
    """Trapezoidal integration of a discharge hydrograph: V = integral(Q dt)."""
    q = np.asarray(q_m3s, dtype=float)
    if q.size == 0:
        return 0.0
    dt_s = dt_h * 3600.0
    if q.size == 1:
        return float(q[0]) * dt_s
    return float(_trapz(q, dx=dt_s))


def apportion_to_ward(basin_volume_m3, basin_area_m2, ward_area_m2):
    """Area-weighted share of a sub-basin volume attributed to a ward."""
    if basin_area_m2 <= 0:
        return 0.0
    return basin_volume_m3 * min(1.0, ward_area_m2 / basin_area_m2)
