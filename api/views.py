import json

from django.http import Http404, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from exposure.models import FloodEvent, FloodPolygon, Ward
from hydrology.models import DischargeForecast, ForecastRun
from impact.models import WardRisk
from outlook.models import SeasonalOutlook, SeasonalWardRisk

from .serializers import DischargeForecastSerializer, FloodEventSerializer, WardRiskSerializer


@api_view(["GET"])
def event_list(request):
    events = FloodEvent.objects.all()
    return Response(FloodEventSerializer(events, many=True).data)


class WardRiskList(ListAPIView):
    serializer_class = WardRiskSerializer

    def get_queryset(self):
        event_id = self.kwargs["event_id"]
        if not FloodEvent.objects.filter(pk=event_id).exists():
            raise Http404
        return WardRisk.objects.filter(event_id=event_id).select_related("ward").order_by("-risk_score")


def flood_polygons_geojson(request, event_id):
    if not FloodEvent.objects.filter(pk=event_id).exists():
        raise Http404
    features = []
    for poly in FloodPolygon.objects.filter(event_id=event_id):
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(poly.geom.geojson),
                "properties": {"depth_m": round(poly.depth_m, 2), "lead_h": poly.lead_h},
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


def wards_geojson(request, event_id):
    if not FloodEvent.objects.filter(pk=event_id).exists():
        raise Http404
    risks = {risk.ward_id: risk for risk in WardRisk.objects.filter(event_id=event_id)}
    features = []
    for ward in Ward.objects.all():
        risk = risks.get(ward.pk)
        center = ward.geom.centroid
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(ward.geom.geojson),
                "properties": {
                    "name": ward.name,
                    "population": ward.population,
                    "risk_score": round(risk.risk_score, 1) if risk else 0.0,
                    "risk_band": risk.risk_band if risk else "Low",
                    "people_displaced": risk.people_displaced if risk else 0,
                    "people_affected": risk.people_affected if risk else 0,
                    "loss_kes": round(risk.loss_kes) if risk else 0,
                    "buildings_affected": risk.buildings_affected if risk else 0,
                    "roads_submerged_m": round(risk.roads_submerged_m) if risk else 0,
                    "facilities_at_risk": len(risk.facilities_at_risk) if risk else 0,
                    "center_lon": round(center.x, 5),
                    "center_lat": round(center.y, 5),
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


def seasonal_outlook_latest(request):
    outlook = SeasonalOutlook.objects.order_by("-created_at").first()
    if outlook is None:
        return JsonResponse({"outlook": None})
    scenarios = [
        {"key": s.key, "name": s.name, "storm_mm": s.storm_mm, "multiplier": s.multiplier}
        for s in outlook.scenario_runs.order_by("multiplier")
    ]
    wards = []
    for ward in Ward.objects.order_by("name"):
        rows = {
            r.scenario.key: r
            for r in SeasonalWardRisk.objects.filter(outlook=outlook, ward=ward).select_related("scenario")
        }
        entry = {"ward": ward.name, "population": ward.population, "scenarios": {}}
        for s in scenarios:
            r = rows.get(s["key"])
            entry["scenarios"][s["key"]] = {
                "displaced": r.displaced if r else 0,
                "buildings_affected": r.buildings_affected if r else 0,
                "loss_kes": round(r.loss_kes) if r else 0,
                "risk_band": r.risk_band if r else "Low",
            }
        wards.append(entry)
    return JsonResponse(
        {
            "season": outlook.season_label,
            "enso_phase": outlook.enso_phase,
            "probability_above_normal": outlook.probability_above_normal,
            "source_note": outlook.source_note,
            "scenarios": scenarios,
            "wards": wards,
        }
    )


def forecast_series(request, hybas_id):
    run = ForecastRun.objects.order_by("-init_time").first()
    if run is None:
        return JsonResponse({"run": None, "series": []})
    series = DischargeForecast.objects.filter(run=run, basin__hybas_id=hybas_id).order_by("lead_h")
    return JsonResponse(
        {
            "run": run.pk,
            "init_time": run.init_time,
            "horizon_h": run.horizon_h,
            "source": run.source,
            "series": DischargeForecastSerializer(series, many=True).data,
        }
    )
