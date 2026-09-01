"""Spatial exposure primitives: flood polygons x assets via GEOS geometry ops.

Flood polygons and assets are stored in EPSG:4326; all length/area math is
done in a local metric CRS (UTM 37S for Kenya).
"""

METRIC_SRID = 32737


def _to_metric(geom):
    metric = geom.clone()
    metric.transform(METRIC_SRID)
    return metric


def submerged_length_m(line_geom, flood_polys):
    """Total length (m) of a line asset covered by the flood polygons."""
    line_m = _to_metric(line_geom)
    total = 0.0
    for poly in flood_polys:
        poly_m = _to_metric(poly.geom)
        if line_m.intersects(poly_m):
            total += line_m.intersection(poly_m).length
    return total


def depth_at(point, flood_polys):
    """Max forecast depth (m) at a point across all flood polygons."""
    depth = 0.0
    for poly in flood_polys:
        if poly.geom.covers(point):
            depth = max(depth, poly.depth_m)
    return depth


def flooded_area_fraction(area_geom, flood_polys):
    """Fraction (0-1) of a polygon's area covered by flood polygons."""
    area_m = _to_metric(area_geom)
    if area_m.area <= 0:
        return 0.0
    flooded = 0.0
    for poly in flood_polys:
        poly_m = _to_metric(poly.geom)
        if area_m.intersects(poly_m):
            flooded += area_m.intersection(poly_m).area
    return min(1.0, flooded / area_m.area)


def footprint_flood_fraction(polygon_geom, flood_polys):
    """Fraction (0-1) of a building footprint covered by flood polygons."""
    return flooded_area_fraction(polygon_geom, flood_polys)


def as_metric(geom):
    """Public helper: clone a geometry into the metric CRS."""
    return _to_metric(geom)


__all__ = [
    "METRIC_SRID",
    "as_metric",
    "depth_at",
    "flooded_area_fraction",
    "footprint_flood_fraction",
    "submerged_length_m",
]
