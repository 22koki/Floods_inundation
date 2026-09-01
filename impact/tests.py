from django.test import SimpleTestCase

from impact.services.damage import building_loss, damage_fraction, duration_multiplier
from impact.services.risk import composite_risk, hazard_index, exposure_index, risk_band


class DamageCurveTests(SimpleTestCase):
    def test_residential_breakpoints(self):
        self.assertAlmostEqual(damage_fraction(0.0, "residential"), 0.0)
        self.assertAlmostEqual(damage_fraction(0.5, "residential"), 0.39)
        self.assertAlmostEqual(damage_fraction(1.0, "residential"), 0.59)
        self.assertAlmostEqual(damage_fraction(6.0, "residential"), 1.0)

    def test_interpolation(self):
        self.assertAlmostEqual(damage_fraction(0.25, "residential"), 0.195)

    def test_unknown_class_falls_back_to_residential(self):
        self.assertEqual(damage_fraction(1.0, "unknown"), damage_fraction(1.0, "residential"))

    def test_negative_depth_is_zero_damage(self):
        self.assertEqual(damage_fraction(-0.5, "residential"), 0.0)

    def test_duration_multiplier(self):
        self.assertEqual(duration_multiplier(12), 1.0)
        self.assertEqual(duration_multiplier(24), 1.0)
        self.assertEqual(duration_multiplier(48), 1.05)
        self.assertEqual(duration_multiplier(72), 1.10)
        self.assertEqual(duration_multiplier(96), 1.20)

    def test_building_loss_kes_local_calibration(self):
        loss = building_loss(1.0, "residential", 100.0, 45000.0, duration_h=24.0)
        self.assertAlmostEqual(loss, 0.59 * 100.0 * 45000.0)

    def test_jrc_regional_factor_opt_in(self):
        loss = building_loss(1.0, "residential", 100.0, 1000.0, duration_h=24.0, region="africa")
        self.assertAlmostEqual(loss, 0.59 * 100.0 * 1000.0 * 0.47)

    def test_loss_never_exceeds_replacement_value(self):
        loss = building_loss(6.0, "residential", 100.0, 45000.0, duration_h=120.0)
        self.assertLessEqual(loss, 100.0 * 45000.0)


class RiskIndexTests(SimpleTestCase):
    def test_hazard_components(self):
        self.assertEqual(hazard_index(0.0, 0.0, 0.0), 0.0)
        self.assertAlmostEqual(hazard_index(4.0, 1.0, 96.0), 1.0)

    def test_exposure_index(self):
        self.assertEqual(exposure_index(1000.0, 0.0), 0.0)
        self.assertAlmostEqual(exposure_index(50_000_000.0, 200_000_000.0), 0.25)
        self.assertEqual(exposure_index(300_000_000.0, 200_000_000.0), 1.0)

    def test_composite_risk(self):
        self.assertAlmostEqual(composite_risk(1.0, 1.0, 1.0), 100.0)
        self.assertAlmostEqual(composite_risk(0.0, 1.0, 1.0), 0.0)
        self.assertAlmostEqual(composite_risk(0.5, 0.5, 0.5), 50.0)

    def test_bands(self):
        self.assertEqual(risk_band(10.0), "Low")
        self.assertEqual(risk_band(30.0), "Watch")
        self.assertEqual(risk_band(60.0), "Warning")
        self.assertEqual(risk_band(90.0), "Extreme")
