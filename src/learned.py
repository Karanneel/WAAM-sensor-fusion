"""
learned estimator for the waam testbed.

one gradient-boosted regressor per output state (H, standoff, T), trained on
supervised data from the simulator. features are the current obs plus the
previous layer's obs plus the known controls.

training set is a list of (dwell, seed) builds. for the planted-error sweep,
the main generator's parameter range is used, NOT the sealed variant
"""

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from simulator import run_build, WFS_CMD, TS_CMD, R_Z_CMD
from sensors import SensorState, observe


OUTPUTS = ("H", "standoff", "T")


def _blank_obs():
    return {"scanner": None, "pyro": 0.0, "ctwd": 0.0}


def _features(obs, prev_obs, dwell, layer):
    """fixed-length vector: current obs + prev obs + dwell + layer index"""
    scan = obs["scanner"] if obs["scanner"] is not None else -1.0
    scan_miss = 1.0 if obs["scanner"] is None else 0.0
    p_scan = prev_obs["scanner"] if prev_obs["scanner"] is not None else -1.0
    return np.array([
        scan, scan_miss, obs["pyro"], obs["ctwd"],
        float(dwell), float(layer),
        p_scan, prev_obs["pyro"], prev_obs["ctwd"],
    ])


def _collect_open_loop(builds):
    """training data from open-loop sims (fixed r_z). legacy, kept for comparison"""
    X_rows, Y = [], {k: [] for k in OUTPUTS}
    for dwell, seed in builds:
        rows = run_build(31, dwell=dwell, seed=seed)
        rng = np.random.default_rng(seed + 1000)
        state = SensorState(rng)
        prev_H = 0.0
        prev_obs = _blank_obs()
        for r in rows:
            obs = observe(r, prev_H, state)
            X_rows.append(_features(obs, prev_obs, dwell, r["layer"]))
            Y["H"].append(r["H_out"])
            Y["standoff"].append(r["standoff"])
            Y["T"].append(r["T_out"])
            prev_H = r["H_out"]
            prev_obs = obs
    return np.array(X_rows), {k: np.array(v) for k, v in Y.items()}


def _collect_closed_loop(builds, pilot_est_builder):
    """training data from closed-loop sims piloted by a known-good estimator.
    this matches the inference regime, avoiding the distribution shift that
    broke the model when trained on open-loop only"""
    # imported lazily to avoid a circular import between harness and learned
    from harness import run_closed_loop

    X_rows, Y = [], {k: [] for k in OUTPUTS}
    for dwell, seed in builds:
        rows, _, _, _, obs_list = run_closed_loop(
            31, dwell=dwell, seed=seed,
            estimator_builder=pilot_est_builder,
        )
        prev_obs = _blank_obs()
        for r, o in zip(rows, obs_list):
            X_rows.append(_features(o, prev_obs, dwell, r["layer"]))
            Y["H"].append(r["H_out"])
            Y["standoff"].append(r["standoff"])
            Y["T"].append(r["T_out"])
            prev_obs = o
    return np.array(X_rows), {k: np.array(v) for k, v in Y.items()}


def train_models(builds, pilot_est_builder=None, mix_open_loop=True,
                 n_estimators=120, max_depth=4):
    """train one GBR per output. returns dict of fitted models.

    pilot_est_builder: an estimator builder (zero-arg callable) used to pilot
    the closed-loop training runs. defaults to the EKF, which gives the
    learned model trajectories that look like closed-loop inference

    mix_open_loop: if True, train on a 50/50 mix of open-loop and closed-loop
    data. this helps the model generalize across inference regimes"""
    if pilot_est_builder is None:
        from ekf import EKF
        pilot_est_builder = lambda: EKF()

    X_cl, Y_cl = _collect_closed_loop(builds, pilot_est_builder)
    if mix_open_loop:
        X_ol, Y_ol = _collect_open_loop(builds)
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

    def __init__(self, models):
        self.models = models
        self.prev_obs = _blank_obs()
        self.layer = 0

    def update(self, obs, control):
        self.layer += 1
        dwell = control.get("dwell", 0.0)
        feats = _features(obs, self.prev_obs, dwell, self.layer).reshape(1, -1)
        out = {k: float(m.predict(feats)[0]) for k, m in self.models.items()}
        self.prev_obs = obs
        return out
