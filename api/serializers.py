from rest_framework import serializers

from exposure.models import FloodEvent
from hydrology.models import DischargeForecast
from impact.models import WardRisk


class FloodEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = FloodEvent
        fields = ["id", "name", "duration_h", "created_at"]


class WardRiskSerializer(serializers.ModelSerializer):
    ward = serializers.CharField(source="ward.name")
    ward_code = serializers.CharField(source="ward.code")

    class Meta:
        model = WardRisk
        fields = [
            "ward",
            "ward_code",
            "max_depth_m",
            "extent_fraction",
            "duration_h",
            "people_affected",
            "people_displaced",
            "buildings_affected",
            "roads_submerged_m",
            "facilities_at_risk",
            "loss_kes",
            "hazard_index",
            "exposure_index",
            "vulnerability_index",
            "risk_score",
            "risk_band",
        ]


class DischargeForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargeForecast
        fields = ["lead_h", "valid_time", "q50_m3s", "q10_m3s", "q90_m3s"]
