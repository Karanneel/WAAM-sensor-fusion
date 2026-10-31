"""
planted-error sweep.

three error types perturbed one at a time:
  fw     scale KF's fw_slope by (1 + level)
  tau    scale KF's tau_base by (1 + level)
  ctwd   scale truth's CTWD quadratic coefficient by (1 + level); KF's linear
         model is unchanged, so its measurement-model error grows

at every (error_type, level, controller_gain) cell, run n_seeds builds per
estimator and record the state RMSE and the final wall-height error
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd

from harness import run_closed_loop
from estimators import Naive
from ekf import EKF, KFParams
from learned import Learned
from oracle import Oracle


def _make_naive_builder():
    return lambda: Naive()


def _make_ekf_builder(error_type, level):
    p = KFParams()
    if error_type == "fw":
        p.fw_slope *= (1.0 + level)
    elif error_type == "tau":
        p.tau_base *= (1.0 + level)
    return lambda: EKF(params=p)


def _make_learned_builder(models):
    return lambda: Learned(models)


def _run_cell(dwell, seed, gain, error_type, level, models, sealed=False,
              scanner_dropout_p=None):
    """one build per estimator at a single sweep cell"""
    # truth sensor state is only perturbed under ctwd error
    sens_kwargs = {}
    truth_ctwd_quad = 0.005
    if error_type == "ctwd":
        truth_ctwd_quad = 0.005 * (1.0 + level)
        sens_kwargs["ctwd_quad"] = truth_ctwd_quad

    builders = {
        "naive":   _make_naive_builder(),
        "EKF":     _make_ekf_builder(error_type, level),
        "learned": _make_learned_builder(models),
        "oracle":  lambda: Oracle(ctwd_quad=truth_ctwd_quad),
    }

    spatter_p = 0.02 if scanner_dropout_p is None else scanner_dropout_p

    out = {}
    for name, b in builders.items():
        rows, est, _, m, _ = run_closed_loop(
            31, dwell, seed, estimator_builder=b,
            controller_gain=gain, sealed=sealed,
            spatter_p=spatter_p, **sens_kwargs,
        )
        H_true = [r["H_out"] for r in rows]
        T_true = [r["T_out"] for r in rows]
        s_true = [r["standoff"] for r in rows]
        H_est = [e["H"] for e in est]
        T_est = [e["T"] for e in est]
        s_est = [e["standoff"] for e in est]
        out[name] = {
            "wall_err":  m["wall_err"],
            "last_S":    m["last_standoff"],
            "rmse_H":    float(np.sqrt(np.mean((np.array(H_est) - H_true) ** 2))),
            "rmse_T":    float(np.sqrt(np.mean((np.array(T_est) - T_true) ** 2))),
            "rmse_s":    float(np.sqrt(np.mean((np.array(s_est) - s_true) ** 2))),
        }
    return out


def run_sweep(models, error_types=("fw", "tau", "ctwd"),
              levels=(0.0, 0.15, 0.30, 0.60),
              gains=(1.0, 0.5),
              n_seeds=30, dwell=60, sealed=False,
              dropout_p=None):
    """returns a long-form pandas DataFrame of all runs"""
    rows = []
    for et in error_types:
        for lv in levels:
            for g in gains:
                for seed in range(n_seeds):
                    cell = _run_cell(dwell, seed, g, et, lv, models,
                                     sealed=sealed, scanner_dropout_p=dropout_p)
                    for name, m in cell.items():
                        rows.append({
                            "error_type":   et,
                            "level":        lv,
                            "gain":         g,
                            "seed":         seed,
                            "estimator":    name,
                            **m,
                        })
    return pd.DataFrame(rows)
