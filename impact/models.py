from django.db import models

from exposure.models import Building, FloodEvent, Ward


class DamageResult(models.Model):
    event = models.ForeignKey(FloodEvent, on_delete=models.CASCADE, related_name="damage_results")
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="damage_results")
    ward = models.ForeignKey(Ward, null=True, blank=True, on_delete=models.SET_NULL, related_name="damage_results")
    depth_m = models.FloatField()
    duration_h = models.FloatField()
    damage_pct = models.FloatField()
    loss_kes = models.FloatField()

    def __str__(self):
        return f"{self.building_id} d={self.depth_m:.2f}m loss=KES {self.loss_kes:,.0f}"


class WardRisk(models.Model):
    event = models.ForeignKey(FloodEvent, on_delete=models.CASCADE, related_name="ward_risk")
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="risk_results")
    max_depth_m = models.FloatField(default=0.0)
    extent_fraction = models.FloatField(default=0.0)
    duration_h = models.FloatField(default=0.0)
    people_affected = models.PositiveIntegerField(default=0)
    people_displaced = models.PositiveIntegerField(default=0)
    buildings_affected = models.PositiveIntegerField(default=0)
    roads_submerged_m = models.FloatField(default=0.0)
    facilities_at_risk = models.JSONField(default=list, blank=True)
    loss_kes = models.FloatField(default=0.0)
    hazard_index = models.FloatField(default=0.0)
    exposure_index = models.FloatField(default=0.0)
    vulnerability_index = models.FloatField(default=0.0)
    risk_score = models.FloatField(default=0.0)
    risk_band = models.CharField(max_length=16, default="Low")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "ward"], name="unique_event_ward_risk")
        ]
        ordering = ["-risk_score"]

    def __str__(self):
        return f"{self.ward.name}: {self.risk_score:.1f} ({self.risk_band})"
