from django.db import models

from exposure.models import FloodEvent, Ward
from hydrology.models import ForecastRun


class SeasonalOutlook(models.Model):
    season_label = models.CharField(max_length=32, default="OND 2026")
    enso_phase = models.CharField(max_length=32, default="El Nino")
    probability_above_normal = models.FloatField(default=0.875)
    source_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.season_label} {self.enso_phase} outlook"


class ScenarioRun(models.Model):
    outlook = models.ForeignKey(SeasonalOutlook, on_delete=models.CASCADE, related_name="scenario_runs")
    key = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    storm_mm = models.FloatField()
    multiplier = models.FloatField()
    run = models.ForeignKey(ForecastRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    event = models.ForeignKey(FloodEvent, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["outlook", "key"], name="unique_outlook_scenario")
        ]

    def __str__(self):
        return f"{self.outlook_id}:{self.key} @ {self.storm_mm:.0f}mm"


class SeasonalWardRisk(models.Model):
    outlook = models.ForeignKey(SeasonalOutlook, on_delete=models.CASCADE, related_name="ward_risks")
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="seasonal_risks")
    scenario = models.ForeignKey(ScenarioRun, on_delete=models.CASCADE, related_name="ward_risks")
    displaced = models.PositiveIntegerField(default=0)
    buildings_affected = models.PositiveIntegerField(default=0)
    loss_kes = models.FloatField(default=0.0)
    risk_band = models.CharField(max_length=16, default="Low")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["outlook", "ward", "scenario"], name="unique_outlook_ward_scenario")
        ]
        ordering = ["ward", "scenario__multiplier"]

    def __str__(self):
        return f"{self.ward.name}/{self.scenario.key}: {self.displaced} displaced"
