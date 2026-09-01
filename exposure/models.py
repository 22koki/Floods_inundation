from django.contrib.gis.db import models as gis_models
from django.db import models


class Ward(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    county = models.CharField(max_length=128, blank=True)
    population = models.PositiveIntegerField(default=0)
    vulnerability_index = models.FloatField(default=0.5)
    geom = gis_models.MultiPolygonField(srid=4326)

    def __str__(self):
        return self.name


class Road(models.Model):
    osm_id = models.CharField(max_length=32, unique=True)
    highway = models.CharField(max_length=32, blank=True)
    geom = gis_models.LineStringField(srid=4326)

    def __str__(self):
        return f"{self.highway} {self.osm_id}"


class Building(models.Model):
    TYPE_CHOICES = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("industrial", "Industrial"),
    ]
    osm_id = models.CharField(max_length=32, unique=True)
    bldg_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="residential")
    footprint = gis_models.PolygonField(srid=4326)
    area_m2 = models.FloatField(default=100.0)
    replacement_value_per_m2 = models.FloatField(default=400.0)

    def __str__(self):
        return self.osm_id


class CriticalFacility(models.Model):
    FCLASS_CHOICES = [
        ("hospital", "Hospital"),
        ("school", "School"),
        ("water_works", "Water treatment"),
        ("substation", "Power substation"),
    ]
    name = models.CharField(max_length=128)
    fclass = models.CharField(max_length=16, choices=FCLASS_CHOICES)
    geom = gis_models.PointField(srid=4326)

    def __str__(self):
        return self.name


class FloodEvent(models.Model):
    run = models.ForeignKey(
        "hydrology.ForecastRun", null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    name = models.CharField(max_length=200)
    duration_h = models.FloatField(default=24.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class FloodPolygon(models.Model):
    event = models.ForeignKey(FloodEvent, on_delete=models.CASCADE, related_name="flood_polygons")
    lead_h = models.PositiveIntegerField(default=0)
    depth_m = models.FloatField()
    geom = gis_models.PolygonField(srid=4326)

    def __str__(self):
        return f"Flood {self.event_id} +{self.lead_h}h d={self.depth_m:.2f}m"
