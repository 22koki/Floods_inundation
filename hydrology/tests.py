import numpy as np
from django.test import SimpleTestCase

from hydrology.services.routing import muskingum_route, travel_time_h
from hydrology.services.volumes import (
    apportion_to_ward,
    basin_runoff_volume_m3,
    cell_runoff_volume_m3,
    hydrograph_volume_m3,
)


class VolumeTests(SimpleTestCase):
    def test_cell_runoff_volume(self):
        self.assertAlmostEqual(cell_runoff_volume_m3(100.0, 1000.0), 100.0)

    def test_basin_runoff_volume(self):
        self.assertAlmostEqual(basin_runoff_volume_m3([10.0, 20.0, 30.0], 1000.0), 60.0)

    def test_hydrograph_volume_constant(self):
        self.assertAlmostEqual(hydrograph_volume_m3([10.0, 10.0], 3.0), 108000.0)
        self.assertAlmostEqual(hydrograph_volume_m3([10.0, 10.0, 10.0], 3.0), 216000.0)

    def test_hydrograph_volume_triangular(self):
        self.assertAlmostEqual(hydrograph_volume_m3([0.0, 10.0, 0.0], 1.0), 36000.0)

    def test_ward_apportion(self):
        self.assertAlmostEqual(apportion_to_ward(1000.0, 2000.0, 500.0), 250.0)
        self.assertAlmostEqual(apportion_to_ward(1000.0, 500.0, 2000.0), 1000.0)
        self.assertAlmostEqual(apportion_to_ward(1000.0, 0.0, 500.0), 0.0)


class RoutingTests(SimpleTestCase):
    def test_steady_flow_passes_through(self):
        outflow = muskingum_route([10.0] * 20, dt_h=3.0, K_h=6.0)
        self.assertTrue(np.allclose(outflow, 10.0))

    def test_peak_attenuation(self):
        inflow = [0.0, 10.0, 30.0, 90.0, 40.0, 15.0, 5.0, 0.0, 0.0]
        outflow = muskingum_route(inflow, dt_h=3.0, K_h=12.0)
        self.assertLess(outflow.max(), max(inflow))

    def test_volume_conservation(self):
        inflow = np.zeros(72)
        inflow[8:20] = 120.0
        outflow = muskingum_route(inflow, dt_h=1.0, K_h=6.0)
        self.assertAlmostEqual(outflow.sum() / inflow.sum(), 1.0, places=2)

    def test_no_negative_flows(self):
        outflow = muskingum_route([0.0, 50.0, 0.0, 0.0, 0.0], dt_h=1.0, K_h=8.0)
        self.assertGreaterEqual(outflow.min(), 0.0)

    def test_travel_time_positive(self):
        self.assertGreater(travel_time_h(5000.0, 0.002, 0.035), 0.0)
        self.assertLess(travel_time_h(5000.0, 0.002, 0.035), 24.0)
