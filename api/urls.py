from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.event_list),
    path("events/<int:event_id>/ward-risk/", views.WardRiskList.as_view()),
    path("events/<int:event_id>/flood-polygons.geojson", views.flood_polygons_geojson),
    path("events/<int:event_id>/wards.geojson", views.wards_geojson),
    path("forecast/<str:hybas_id>/", views.forecast_series),
    path("seasonal-outlooks/latest/", views.seasonal_outlook_latest),
]
