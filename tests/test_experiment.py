"""Regression checks for the experiment's timing and evaluation assumptions."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ekf import EKF, KFParams, _thermal_predict, _thermal_derivatives
from evaluation import paired_improvement, tied_winners
from harness import run_closed_loop
from learned import TRAIN_SEEDS
from sensors import SensorState, observe
from simulator import run_build
from sweep import score_build


class PredictionOnly(EKF):
    def update(self, obs, control):
        return super().update(obs, control, active_sensors=set())


class HeightOffset:
    def __init__(self, offset):
        self.offset = offset

    def update(self, obs, control):
        return {"H": (obs["scanner"] or 0) + 1.8 + self.offset,
                "standoff": obs["ctwd"], "T": obs["pyro"]}


class ExperimentTests(unittest.TestCase):
    def test_prediction_matches_truth_without_parameter_variation(self):
        rows, estimates, _, metrics, _ = run_closed_loop(
            12, 60, 0, PredictionOnly, varied=False)
        for row, estimate in zip(rows, estimates):
            for state, truth in [("H", "H_out"), ("standoff", "standoff"), ("T", "T_out")]:
                self.assertAlmostEqual(estimate[state], row[truth], places=10)
        self.assertAlmostEqual(metrics["final_standoff"], rows[-1]["Z"] - rows[-1]["H_out"])

    def test_height_estimate_changes_the_physical_wall(self):
        low = run_closed_loop(31, 60, 0, lambda: HeightOffset(-3))
        high = run_closed_loop(31, 60, 0, lambda: HeightOffset(3))
        self.assertGreater(abs(low[3]["final_H"] - high[3]["final_H"]), 0.5)

    def test_custom_target_changes_control(self):
        low = run_closed_loop(31, 60, 0, PredictionOnly, target_wall_height=45)
        high = run_closed_loop(31, 60, 0, PredictionOnly, target_wall_height=65)
        self.assertLess(low[3]["final_H"], high[3]["final_H"])
        self.assertEqual(low[3]["target_H"], 45)

    def test_build_seeds_change_physical_parameters(self):
        a, b = run_build(31, 60, seed=0), run_build(31, 60, seed=1)
        self.assertNotEqual(a[-1]["H_out"], b[-1]["H_out"])
        self.assertTrue(set(TRAIN_SEEDS).isdisjoint(range(30)))

    def test_dropout_does_not_change_other_sensor_noise(self):
        states = [SensorState(np.random.default_rng(1000)) for _ in range(2)]
        for row in run_build(12, 60):
            blocked = dict(row, spatter=True)
            clear = dict(row, spatter=False)
            a = observe(blocked, row["H_in"], states[0])
            b = observe(clear, row["H_in"], states[1])
            self.assertEqual(a["pyro"], b["pyro"])
            self.assertEqual(a["ctwd"], b["ctwd"])

    def test_thermal_derivatives(self):
        for beta in [1, 0.85]:
            p = KFParams(cooling_exponent=beta)
            dH, dT = _thermal_derivatives(110, 40, 60, 10, p)
            epsilon = 1e-4
            numerical_H = (_thermal_predict(110, 40+epsilon, 60, 10, p)
                           - _thermal_predict(110, 40-epsilon, 60, 10, p))/(2*epsilon)
            numerical_T = (_thermal_predict(110+epsilon, 40, 60, 10, p)
                           - _thermal_predict(110-epsilon, 40, 60, 10, p))/(2*epsilon)
            self.assertAlmostEqual(dH, numerical_H, places=7)
            self.assertAlmostEqual(dT, numerical_T, places=7)

    def test_paired_gate_requires_thirty_builds(self):
        records = [dict(seed=s, estimator=e, error=v)
                   for s in range(30) for e, v in [("naive", 2), ("EKF", 1)]]
        frame = pd.DataFrame(records)
        score = paired_improvement(frame, "EKF", "error")
        self.assertTrue(score["passed"])
        self.assertEqual(score["improvement_pct"], 50)
        self.assertFalse(paired_improvement(frame[frame.seed < 29], "EKF", "error")["passed"])

    def test_first_layer_is_not_a_dropout(self):
        rows, estimates, _, metrics, obs = run_closed_loop(4, 60, 0, EKF, spatter_p=0)
        self.assertIsNone(obs[0]["scanner"])
        self.assertEqual(score_build(rows, estimates, obs, metrics)["dropout_count"], 0)
        self.assertTrue(np.isnan(score_build(rows, estimates, obs, metrics)["dropout_joint"]))

    def test_ties_are_preserved(self):
        frame = pd.DataFrame([dict(error_type="width_temperature", level=0, gain=1,
                                   estimator=name, error=1) for name in ["EKF", "naive"]])
        self.assertEqual(tied_winners(frame, "error")[("width_temperature", 0, 1)], ["EKF", "naive"])

    def test_filter_covariance_remains_positive(self):
        model = EKF()
        run_closed_loop(31, 60, 0, lambda: model)
        self.assertGreaterEqual(np.linalg.eigvalsh(model.P).min(), -1e-10)


if __name__ == "__main__":
    unittest.main()
