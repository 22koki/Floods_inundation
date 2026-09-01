from django.contrib.gis.db import models as gis_models
from django.db import models


class Basin(models.Model):
    hybas_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    geom = gis_models.MultiPolygonField(srid=4326)
    upstream_area_km2 = models.FloatField(default=0.0)
    response_time_h = models.FloatField(default=6.0)
    downstream = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="upstream_basins"
    )

    def __str__(self):
        return f"{self.name} ({self.hybas_id})"


class River(models.Model):
    name = models.CharField(max_length=128)
    basin = models.OneToOneField(Basin, on_delete=models.CASCADE, related_name="river")
    geom = gis_models.LineStringField(srid=4326)
    manning_n = models.FloatField(default=0.035)
    bankfull_q_m3s = models.FloatField(default=50.0)
    slope = models.FloatField(default=0.002)

    def __str__(self):
        return self.name


class ForecastRun(models.Model):
    init_time = models.DateTimeField()
    horizon_h = models.PositiveIntegerField(default=168)
    source = models.CharField(max_length=64, default="synthetic")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-init_time"]

    def __str__(self):
        return f"Run {self.pk} @ {self.init_time:%Y-%m-%d %H:%M}Z"


class DischargeForecast(models.Model):
    run = models.ForeignKey(ForecastRun, on_delete=models.CASCADE, related_name="series")
    basin = models.ForeignKey(Basin, on_delete=models.CASCADE, related_name="forecasts")
    valid_time = models.DateTimeField()
    lead_h = models.PositiveIntegerField()
    q50_m3s = models.FloatField()
    q10_m3s = models.FloatField(null=True, blank=True)
    q90_m3s = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["basin", "lead_h"]
        indexes = [models.Index(fields=["run", "basin"])]

    def __str__(self):
        return f"{self.basin.name} +{self.lead_h}h Q50={self.q50_m3s:.1f}"
