from datetime import timedelta

import numpy as np
from django.contrib.gis.geos import Polygon
from django.core.management.base import BaseCommand
from django.utils import timezone

from exposure.models import FloodEvent, FloodPolygon
from exposure.services.exposure import METRIC_SRID
from hydrology.models import Basin, DischargeForecast, ForecastRun, River
from hydrology.services.routing import muskingum_route, travel_time_h
from hydrology.services.volumes import _trapz, hydrograph_volume_m3
from impact.models import WardRisk
from impact.services.impact import compute_event_impact

DT_H = 3.0
HORIZON_H = 168


def unit_hydrograph_shape(n_steps, tp_h, dt_h):
    """Gamma-like synthetic unit hydrograph shape (peaks at tp_h)."""
    t = np.arange(1, n_steps + 1) * dt_h
    shape = (t / tp_h) * np.exp(1.0 - t / tp_h)
    return np.maximum(shape, 0.0)


class Command(BaseCommand):
    help = (
        "Generate a synthetic 7-day design-storm forecast, route it through the "
        "river network (Muskingum), map inundation polygons, and compute ward impact."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--storm-mm",
            type=float,
            default=160.0,
            help="Design storm total (mm). Default 160 mm matches the 3-5h total "
            "recorded at Wilson Airport during the 6 March 2026 Nairobi flash floods.",
        )
        parser.add_argument("--runoff-coeff", type=float, default=0.35)

    def handle(self, *args, **options):
        basins = list(Basin.objects.select_related("downstream").order_by("upstream_area_km2"))
        if not basins:
            self.stderr.write("No basins found. Run `python manage.py load_demo_data` first.")
            return
        rivers = {river.basin_id: river for river in River.objects.select_related("basin")}

        init_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        n_steps = int(HORIZON_H // DT_H)
        run = ForecastRun.objects.create(
            init_time=init_time, horizon_h=HORIZON_H, source="synthetic-design-storm"
        )

        local = {}
        for basin in basins:
            shape = unit_hydrograph_shape(n_steps, basin.response_time_h, DT_H)
            area_m2 = basin.upstream_area_km2 * 1e6
            runoff_m3 = options["runoff_coeff"] * (options["storm_mm"] / 1000.0) * area_m2
            norm = _trapz(shape, dx=DT_H * 3600.0)
            local[basin.pk] = shape * (runoff_m3 / norm if norm > 0 else 0.0)

        routed_by_basin = {}
        by_pk = {basin.pk: basin for basin in basins}
        event_duration_h = 12.0
        event = FloodEvent.objects.create(
            run=run,
            name=(
                f"Nairobi River flash floods reconstruction - 6/7 Mar 2026 "
                f"({options['storm_mm']:.0f} mm design storm)"
            ),
        )

        for basin in basins:
            inflow = local[basin.pk].copy()
            for upstream_pk, upstream in by_pk.items():
                if upstream.downstream_id == basin.pk:
                    inflow = inflow + routed_by_basin[upstream_pk]

            river = rivers.get(basin.pk)
            if river is not None:
                length_m = river.geom.clone()
                length_m.transform(METRIC_SRID)
                K_h = travel_time_h(length_m.length, river.slope, river.manning_n)
            else:
                K_h = 3.0

            q50 = muskingum_route(inflow, DT_H, K_h)
            routed_by_basin[basin.pk] = q50

            DischargeForecast.objects.bulk_create(
                DischargeForecast(
                    run=run,
                    basin=basin,
                    valid_time=init_time + timedelta(hours=(step + 1) * DT_H),
                    lead_h=int((step + 1) * DT_H),
                    q50_m3s=float(q50[step]),
                    q10_m3s=float(0.8 * q50[step]),
                    q90_m3s=float(1.25 * q50[step]),
                )
                for step in range(n_steps)
            )

            if river is None:
                continue
            peak_step = int(np.argmax(q50))
            peak_q = float(q50[peak_step])
            ratio = max(peak_q / river.bankfull_q_m3s, 0.1)
            depth_m = min(3.5, 0.3 + 0.9 * ratio ** 0.5)
            width_m = 60.0 + 120.0 * ratio ** 0.6
            duration_h = float((q50 > river.bankfull_q_m3s).sum() * DT_H)
            event_duration_h = max(event_duration_h, duration_h)

            line_metric = river.geom.clone()
            line_metric.transform(METRIC_SRID)
            poly_metric = line_metric.buffer(width_m / 2.0)
            poly_metric.transform(4326)
            if isinstance(poly_metric, Polygon):
                FloodPolygon.objects.create(
                    event=event,
                    lead_h=int((peak_step + 1) * DT_H),
                    depth_m=round(depth_m, 2),
                    geom=poly_metric,
                )

        event.duration_h = event_duration_h
        event.save(update_fields=["duration_h"])

        rows = compute_event_impact(event)
        volume_m3 = sum(
            hydrograph_volume_m3(q, DT_H) for q in routed_by_basin.values()
        )

        self.stdout.write(self.style.SUCCESS(f"ForecastRun {run.pk} -> FloodEvent {event.pk}"))
        self.stdout.write(f"Routed outlet volume: {volume_m3:,.0f} m3 over {HORIZON_H}h")
        self.stdout.write(f"{'Ward':<20} {'Risk':>6} {'Band':<9} {'Bldgs':>6} {'Displaced':>10} {'Loss KES':>16}")
        for row in rows:
            self.stdout.write(
                f"{row.ward.name:<20} {row.risk_score:>6.1f} {row.risk_band:<9} "
                f"{row.buildings_affected:>6} {row.people_displaced:>10} {row.loss_kes:>16,.0f}"
            )
        # Return the created event id (as str so command execution can print it);
        # run_seasonal_outlook parses this to link scenario -> event.
        return str(event.pk)
