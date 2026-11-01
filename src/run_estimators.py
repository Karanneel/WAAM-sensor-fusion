"""Compare estimators on a fixed-speed build with a held-out seed."""

import io
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from simulator import run_build, WFS_CMD, TS_CMD, R_Z_CMD
from sensors import SensorState, observe
from estimators import Naive
from ekf import EKF
from learned import Learned, train_models


OUT = Path(__file__).resolve().parents[1] / "reports" / "experiments"
OUT.mkdir(parents=True, exist_ok=True)


def run_one(n_layers, dwell, seed, est_builder):
    rows = run_build(n_layers, dwell=dwell, seed=seed)
    rng = np.random.default_rng(seed + 1000)
    state = SensorState(rng)
    est = est_builder()
    estimates = []
    prev_H = 0.0
    for r in rows:
        obs = observe(r, prev_H, state)
        ctrl = {"wfs": WFS_CMD, "ts": TS_CMD, "r_z": r["r_z"], "dwell": dwell}
        estimates.append(est.update(obs, ctrl))
        prev_H = r["H_out"]
    return rows, estimates


def rmse(a, b):
    a = np.asarray(a); b = np.asarray(b)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def score(rows, estimates):
    H_true = [r["H_out"] for r in rows]
    T_true = [r["T_out"] for r in rows]
    s_true = [r["standoff"] for r in rows]
    H_est = [e["H"] for e in estimates]
    T_est = [e["T"] for e in estimates]
    s_est = [e["standoff"] for e in estimates]
    return {
        "H":        rmse(H_est, H_true),
        "T":        rmse(T_est, T_true),
        "standoff": rmse(s_est, s_true),
    }


def plot_all(rows, by_name):
    layers = np.array([r["layer"] for r in rows])
    truth = {
        "H":        np.array([r["H_out"] for r in rows]),
        "T":        np.array([r["T_out"] for r in rows]),
        "standoff": np.array([r["standoff"] for r in rows]),
    }
    labels = {"H": "wall top (mm)", "T": "T (C)", "standoff": "standoff (mm)"}
    colors = {"naive": "C3", "EKF": "C0", "learned": "C2"}

    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    for i, k in enumerate(["H", "T", "standoff"]):
        ax[i].plot(layers, truth[k], label="truth", color="k", lw=2)
        for name, est in by_name.items():
            arr = np.array([e[k] for e in est])
            ax[i].plot(layers, arr, label=name, color=colors[name],
                       lw=1.3, alpha=0.9)
        ax[i].set_xlabel("layer"); ax[i].set_ylabel(labels[k])
        ax[i].set_title(f"{k}: truth vs estimators")
        ax[i].legend(); ax[i].grid(alpha=0.3)
    fig.tight_layout()
    out = OUT / "all_estimators.png"
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    out.write_bytes(buf.getvalue())
    return out


if __name__ == "__main__":
    print('Training models on independent builds...')
    models = train_models()

    # held-out test case
    n_layers, dwell, seed = 31, 60, 1
    rows, naive_est = run_one(n_layers, dwell, seed, est_builder=Naive)
    _,    kf_est    = run_one(n_layers, dwell, seed, est_builder=EKF)
    _,    lrn_est   = run_one(n_layers, dwell, seed,
                              est_builder=lambda: Learned(models))

    by_name = {"naive": naive_est, "EKF": kf_est, "learned": lrn_est}
    rmse_by = {name: score(rows, est) for name, est in by_name.items()}

    print(f"\n{'state':>10} {'naive':>10} {'EKF':>10} {'learned':>10}")
    for k in ["H", "T", "standoff"]:
        print(f"{k:>10} "
              f"{rmse_by['naive'][k]:>10.3f} "
              f"{rmse_by['EKF'][k]:>10.3f} "
              f"{rmse_by['learned'][k]:>10.3f}")

    p = plot_all(rows, by_name)
    print(f"\nfigure: {p}")
