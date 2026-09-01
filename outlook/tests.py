from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from exposure.models import Ward
from outlook.models import ScenarioRun, SeasonalOutlook, SeasonalWardRisk
from outlook.services import SCENARIOS


class ScenarioDefinitionTests(SimpleTestCase):
    def test_multipliers_ascending_from_neutral(self):
        mults = [s["multiplier"] for s in SCENARIOS]
        self.assertEqual(mults, sorted(mults))
        self.assertEqual(SCENARIOS[0]["multiplier"], 1.0)

    def test_strong_scenario_matches_march_2026_observed(self):
        self.assertEqual(SCENARIOS[-1]["storm_mm"], 160.0)


class SeasonalOutlookCommandTests(TestCase):
    def test_command_runs_all_scenarios_and_aggregates(self):
        call_command("load_demo_data", verbosity=0)
        outlook_pk = int(call_command("run_seasonal_outlook"))
        outlook = SeasonalOutlook.objects.get(pk=outlook_pk)
        self.assertEqual(outlook.scenario_runs.count(), len(SCENARIOS))
        self.assertEqual(
            SeasonalWardRisk.objects.filter(outlook=outlook).count(),
            Ward.objects.count() * len(SCENARIOS),
        )
        worst_strong = (
            SeasonalWardRisk.objects.filter(outlook=outlook, scenario__key="strong")
            .select_related("ward")
            .order_by("-displaced")
            .first()
        )
        baseline = SeasonalWardRisk.objects.get(
            outlook=outlook, ward=worst_strong.ward, scenario__key="baseline"
        )
        self.assertGreaterEqual(worst_strong.displaced, baseline.displaced)
        self.assertGreaterEqual(worst_strong.loss_kes, baseline.loss_kes)
