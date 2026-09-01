from django.core.management import call_command
from django.core.management.base import BaseCommand

from exposure.models import FloodEvent, Ward
from outlook.models import ScenarioRun, SeasonalOutlook, SeasonalWardRisk
from outlook.services import OUTLOOK_DEFAULTS, SCENARIOS


class Command(BaseCommand):
    help = (
        "Run the El Nino OND 2026 seasonal outlook: execute baseline, moderate, "
        "and strong design-storm scenarios through the full flood pipeline and "
        "aggregate per-ward impacts."
    )

    def handle(self, *args, **options):
        if not Ward.objects.exists():
            self.stderr.write("No demo geodata found. Run `python manage.py load_demo_data` first.")
            return

        outlook = SeasonalOutlook.objects.create(**OUTLOOK_DEFAULTS)
        rows_by_scenario = {}

        for spec in SCENARIOS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Scenario: {spec['name']} ({spec['storm_mm']:.0f} mm)"))
            event_pk = int(call_command("run_forecast", storm_mm=spec["storm_mm"]))
            event = FloodEvent.objects.get(pk=event_pk)
            scenario = ScenarioRun.objects.create(
                outlook=outlook,
                key=spec["key"],
                name=spec["name"],
                storm_mm=spec["storm_mm"],
                multiplier=spec["multiplier"],
                run=event.run,
                event=event,
            )
            rows_by_scenario[spec["key"]] = {
                r.ward_id: r for r in event.ward_risk.select_related("ward")
            }

        wards = Ward.objects.order_by("name")
        for ward in wards:
            for key, rows in rows_by_scenario.items():
                row = rows.get(ward.pk)
                if row is None:
                    continue
                SeasonalWardRisk.objects.create(
                    outlook=outlook,
                    ward=row.ward,
                    scenario=ScenarioRun.objects.get(outlook=outlook, key=key),
                    displaced=row.people_displaced,
                    buildings_affected=row.buildings_affected,
                    loss_kes=row.loss_kes,
                    risk_band=row.risk_band,
                )

        self.stdout.write(self.style.SUCCESS(f"SeasonalOutlook {outlook.pk}: {outlook.season_label} {outlook.enso_phase}"))
        header = f"{'Ward':<22}" + "".join(f"{key:>24}" for key in ("baseline", "moderate", "strong"))
        self.stdout.write(header + "   (displaced / loss KES / band)")
        for ward in wards:
            cells = ""
            for key in ("baseline", "moderate", "strong"):
                row = rows_by_scenario[key].get(ward.pk)
                if row:
                    cells += f"{row.people_displaced:>12} {row.loss_kes:>9,.0f} {row.risk_band[:4]:>5}"
                else:
                    cells += f"{'-':>26}"
            self.stdout.write(f"{ward.name:<22}{cells}")
        self.stdout.write(self.style.SUCCESS("Done."))
        # str so command execution can print it; tests/clients parse the int.
        return str(outlook.pk)
