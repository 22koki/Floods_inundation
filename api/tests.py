from django.contrib.gis.geos import MultiPolygon, Polygon
from django.test import TestCase

from exposure.models import FloodEvent, Ward
from impact.models import WardRisk


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


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = FloodEvent.objects.create(name="API flood")
        cls.ward = Ward.objects.create(
            code="W1",
            name="Ward One",
            population=100,
            vulnerability_index=0.5,
            geom=MultiPolygon(unit_square(36.85, -1.28), srid=4326),
        )
        cls.risk = WardRisk.objects.create(
            event=cls.event,
            ward=cls.ward,
            risk_score=30.0,
            risk_band="Watch",
            people_displaced=5,
            loss_kes=1000.0,
        )

    def test_ward_risk_endpoint(self):
        resp = self.client.get(f"/api/events/{self.event.id}/ward-risk/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data[0]["ward"], "Ward One")
        self.assertEqual(data[0]["risk_band"], "Watch")

    def test_flood_polygons_geojson_empty(self):
        resp = self.client.get(f"/api/events/{self.event.id}/flood-polygons.geojson")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["type"], "FeatureCollection")

    def test_wards_geojson_includes_risk_properties(self):
        resp = self.client.get(f"/api/events/{self.event.id}/wards.geojson")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["type"], "FeatureCollection")
        props = data["features"][0]["properties"]
        self.assertEqual(props["name"], "Ward One")
        self.assertEqual(props["risk_band"], "Watch")
        self.assertIn("center_lon", props)

    def test_missing_event_returns_404(self):
        for url in [
            "/api/events/999/ward-risk/",
            "/api/events/999/flood-polygons.geojson",
            "/api/events/999/wards.geojson",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_dashboard_index_renders(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "FloodSentry")
