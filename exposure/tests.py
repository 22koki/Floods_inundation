from django.contrib.gis.geos import LineString, MultiPolygon, Point, Polygon
from django.test import TestCase

from exposure.models import Building, FloodEvent, FloodPolygon, Road, Ward
from exposure.services.exposure import depth_at, flooded_area_fraction, submerged_length_m
from impact.models import WardRisk
from impact.services.impact import compute_event_impact


def unit_square(lon, lat, half=0.002):
    return Polygon(
        [
            (lon - half, lat - half),
            (lon + half, lat - half),
            (lon + half, lat + half),
            (lon - half, lat + half),
            (lon - half, lat - half),
        ],
        srid=4326,
    )


class ExposureServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ward = Ward.objects.create(
            code="W1",
            name="Test Ward",
            population=1000,
            vulnerability_index=0.5,
            geom=MultiPolygon(unit_square(36.85, -1.28, 0.01), srid=4326),
        )
        cls.road = Road.objects.create(
            osm_id="r1",
            highway="primary",
            geom=LineString([(36.84, -1.28), (36.86, -1.28)], srid=4326),
        )
        cls.building = Building.objects.create(
            osm_id="b1",
            bldg_type="residential",
            footprint=unit_square(36.85, -1.28, 0.0005),
            area_m2=4000.0,
            replacement_value_per_m2=500.0,
        )
        cls.event = FloodEvent.objects.create(name="Test flood", duration_h=48.0)
        FloodPolygon.objects.create(
            event=cls.event, lead_h=24, depth_m=1.2, geom=unit_square(36.85, -1.28, 0.003)
        )

    def test_submerged_length_positive(self):
        polys = list(self.event.flood_polygons.all())
        self.assertGreater(submerged_length_m(self.road.geom, polys), 0.0)

    def test_depth_at_point(self):
        polys = list(self.event.flood_polygons.all())
        self.assertAlmostEqual(depth_at(Point(36.85, -1.28, srid=4326), polys), 1.2)
        self.assertEqual(depth_at(Point(36.70, -1.28, srid=4326), polys), 0.0)

    def test_flooded_area_fraction_bounds(self):
        polys = list(self.event.flood_polygons.all())
        frac = flooded_area_fraction(self.ward.geom, polys)
        self.assertGreater(frac, 0.0)
        self.assertLessEqual(frac, 1.0)

    def test_compute_event_impact_persists_ward_risk(self):
        rows = compute_event_impact(self.event)
        self.assertEqual(len(rows), 1)
        risk = rows[0]
        self.assertEqual(risk.ward, self.ward)
        self.assertGreater(risk.loss_kes, 0.0)
        self.assertGreater(risk.people_affected, 0)
        self.assertGreaterEqual(risk.buildings_affected, 1)
        self.assertEqual(WardRisk.objects.filter(event=self.event).count(), 1)
