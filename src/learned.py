"""
learned estimator for the waam testbed.

one gradient-boosted regressor per output state (H, standoff, T), trained on
supervised data from the simulator. features are the current obs plus the
previous layer's obs plus the known controls (including travel speed, which
varies under the closed-loop controller).

training seeds and evaluation seeds are kept separate to avoid leakage
"""

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from simulator import run_build, WFS_CMD, TS_CMD, R_Z_CMD
from sensors import SensorState, observe


OUTPUTS = ("H", "standoff", "T")
TRAIN_DWELLS = (0, 30, 60, 120, 240)
ALL_SENSORS = {"scanner", "pyro", "ctwd"}

def mask_observations(obs, subset):
    return {"scanner": obs["scanner"] if "scanner" in subset else None,
            "pyro": obs["pyro"] if "pyro" in subset else 0.0,
            "ctwd": obs["ctwd"] if "ctwd" in subset else 0.0}


# seed ranges: training uses seeds 100-149, evaluation uses 0-29
TRAIN_SEEDS = range(100, 150)


def _blank_obs():
    return {"scanner": None, "pyro": 0.0, "ctwd": 0.0}


def _features(obs, prev_obs, dwell, layer, ts):
    """fixed-length vector: current obs + prev obs + dwell + layer + ts"""
    scan = obs["scanner"] if obs["scanner"] is not None else -1.0
    scan_miss = 1.0 if obs["scanner"] is None else 0.0
    p_scan = prev_obs["scanner"] if prev_obs["scanner"] is not None else -1.0
    return np.array([
        scan, scan_miss, obs["pyro"], obs["ctwd"],
        float(dwell), float(layer), float(ts),
        p_scan, prev_obs["pyro"], prev_obs["ctwd"],
    ])


def _collect_open_loop(builds, subset):
    """training data from open-loop sims (fixed r_z, fixed ts)"""
    X_rows, Y = [], {k: [] for k in OUTPUTS}
    for dwell, seed in builds:
        rows = run_build(31, dwell=dwell, seed=seed)
        rng = np.random.default_rng(seed + 1000)
        state = SensorState(rng)
        prev_H = 0.0
        prev_obs = _blank_obs()
        for r in rows:
            obs = observe(r, prev_H, state)
            X_rows.append(_features(mask_observations(obs, subset), mask_observations(prev_obs, subset), dwell, r["layer"], TS_CMD))
            Y["H"].append(r["H_out"])
            Y["standoff"].append(r["standoff"])
            Y["T"].append(r["T_out"])
            prev_H = r["H_out"]
            prev_obs = obs
    return np.array(X_rows), {k: np.array(v) for k, v in Y.items()}


def _collect_closed_loop(builds, pilot_est_builder, subset):
    """training data from closed-loop sims. ts varies per layer under the
    controller, so it must be included as a feature"""
    from harness import run_closed_loop

    X_rows, Y = [], {k: [] for k in OUTPUTS}
    for dwell, seed in builds:
        rows, _, _, _, obs_list = run_closed_loop(
            31, dwell=dwell, seed=seed,
            estimator_builder=pilot_est_builder,
        )
        prev_obs = _blank_obs()
        for r, o in zip(rows, obs_list):
            X_rows.append(_features(mask_observations(o, subset), mask_observations(prev_obs, subset), dwell, r["layer"], r["ts"]))
            Y["H"].append(r["H_out"])
            Y["standoff"].append(r["standoff"])
            Y["T"].append(r["T_out"])
            prev_obs = o
    return np.array(X_rows), {k: np.array(v) for k, v in Y.items()}


def train_models(builds=None, pilot_est_builder=None, mix_open_loop=True,
                 n_estimators=120, max_depth=4, subset=None):
    """train one GBR per output. returns dict of fitted models.

    builds: list of (dwell, seed) pairs. defaults to TRAIN_SEEDS x dwells
    to keep training data separate from evaluation seeds (0-29)"""
    subset = ALL_SENSORS if subset is None else set(subset)
    if builds is None:
        builds = [(d, s) for d in TRAIN_DWELLS
                  for s in TRAIN_SEEDS]

    if pilot_est_builder is None:
        from ekf import EKF
        pilot_est_builder = lambda: EKF()

    X_cl, Y_cl = _collect_closed_loop(builds, pilot_est_builder, subset)
    if mix_open_loop:
        X_ol, Y_ol = _collect_open_loop(builds, subset)
        X = np.vstack([X_cl, X_ol])
        Y = {k: np.concatenate([Y_cl[k], Y_ol[k]]) for k in OUTPUTS}
    else:
        X, Y = X_cl, Y_cl
    models = {}
    for k in OUTPUTS:
        m = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.08,
            random_state=0,
        )
        m.fit(X, Y[k])
        models[k] = m
    return models


class Learned:
    """learned estimator, same interface as estimators.Naive and ekf.EKF"""

    def __init__(self, models, subset=None):
        self.models = models
        self.subset = ALL_SENSORS if subset is None else set(subset)
        self.prev_obs = _blank_obs()
        self.layer = 0

    def update(self, obs, control):
        self.layer += 1
        dwell = control.get("dwell", 0.0)
        ts = control.get("ts", TS_CMD)
        feats = _features(mask_observations(obs, self.subset), mask_observations(self.prev_obs, self.subset), dwell, self.layer, ts).reshape(1, -1)
        out = {k: float(m.predict(feats)[0]) for k, m in self.models.items()}
        self.prev_obs = obs
        return out
