"""Event impact computation: exposure x depth-damage x population -> ward risk."""
import os

from exposure.models import Building, CriticalFacility, Road, Ward
from exposure.services.exposure import (
    depth_at,
    flooded_area_fraction,
    footprint_flood_fraction,
    submerged_length_m,
)
from impact.models import DamageResult, WardRisk
from impact.services.damage import building_loss, damage_fraction, duration_multiplier
from impact.services.risk import composite_risk, exposure_index, hazard_index, risk_band

LOSS_CAP_KES = float(os.environ.get("FLOODSENTRY_LOSS_CAP_KES", 200_000_000))


def compute_event_impact(event):
    """Compute and persist per-ward exposure, damage, and risk for one event."""
    polys = list(event.flood_polygons.all())
    rows = []
    for ward in Ward.objects.all():
        extent = flooded_area_fraction(ward.geom, polys)

        roads = list(Road.objects.filter(geom__intersects=ward.geom))
        submerged_m = sum(submerged_length_m(road.geom, polys) for road in roads)

        buildings = list(Building.objects.filter(footprint__intersects=ward.geom))
        affected = 0
        loss = 0.0
        for building in buildings:
            frac = footprint_flood_fraction(building.footprint, polys)
            centroid_depth = depth_at(building.footprint.centroid, polys)
            if frac <= 0.0 and centroid_depth <= 0.0:
                continue
            depth = centroid_depth if centroid_depth > 0 else 0.3
            damage_pct = min(1.0, damage_fraction(depth, building.bldg_type) * duration_multiplier(event.duration_h))
            building_loss_kes = building_loss(
                depth,
                building.bldg_type,
                building.area_m2,
                building.replacement_value_per_m2,
                duration_h=event.duration_h,
            )
            affected += 1
            loss += building_loss_kes
            DamageResult.objects.create(
                event=event,
                building=building,
                ward=ward,
                depth_m=depth,
                duration_h=event.duration_h,
                damage_pct=round(damage_pct * 100.0, 2),
                loss_kes=building_loss_kes,
            )

        facilities_at_risk = []
        for facility in CriticalFacility.objects.all():
            facility_depth = depth_at(facility.geom, polys)
            if facility_depth > 0.1:
                facilities_at_risk.append(
                    {"name": facility.name, "fclass": facility.fclass, "depth_m": round(facility_depth, 2)}
                )

        max_depth = max((poly.depth_m for poly in polys if ward.geom.intersects(poly.geom)), default=0.0)
        people_affected = int(round(ward.population * extent))
        displacement_rate = min(1.0, 0.1 + 0.4 * (max_depth / 2.0)) if extent > 0 else 0.0
        people_displaced = int(round(people_affected * displacement_rate))

        hazard = hazard_index(max_depth, extent, event.duration_h)
        exposure = exposure_index(loss, LOSS_CAP_KES)
        vulnerability = min(1.0, max(0.0, ward.vulnerability_index))
        score = composite_risk(hazard, exposure, vulnerability)

        risk, _ = WardRisk.objects.update_or_create(
            event=event,
            ward=ward,
            defaults={
                "max_depth_m": max_depth,
                "extent_fraction": extent,
                "duration_h": event.duration_h,
                "people_affected": people_affected,
                "people_displaced": people_displaced,
                "buildings_affected": affected,
                "roads_submerged_m": submerged_m,
                "facilities_at_risk": facilities_at_risk,
                "loss_kes": loss,
                "hazard_index": hazard,
                "exposure_index": exposure,
                "vulnerability_index": vulnerability,
                "risk_score": score,
                "risk_band": risk_band(score),
            },
        )
        rows.append(risk)
    return rows
