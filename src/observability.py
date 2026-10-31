"""
stop B / Q2: CRB floors per sensor subset from EKF steady-state covariance.
output: reports/stopB/gramian_heatmap.png
"""

import io
import itertools
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from simulator import run_build
from sensors import SensorState, observe
from ekf import EKF

ALL_SENSORS = ["scanner", "pyro", "ctwd"]
STATE_NAMES = ["H", "standoff", "T"]
STATE_IDX = [0, 1, 2]
STATE_UNITS = ["mm", "mm", "°C"]

OUT = Path(__file__).resolve().parents[1] / "reports" / "stopB"


def sensor_subsets():
    subs = []
    for r in range(len(ALL_SENSORS) + 1):
        for combo in itertools.combinations(ALL_SENSORS, r):
            subs.append(set(combo))
    return subs


def subset_label(s):
    if not s:
        return "none"
    short = {"scanner": "scan", "pyro": "pyro", "ctwd": "ctwd"}
    return "+".join(short[k] for k in ALL_SENSORS if k in s)


def run_ekf_subset(subset, n_layers=60, n_seeds=5, dwell=60):
    """avg steady-state P diagonal over last 10 layers, 3 physical states"""
    P_diag_accum = np.zeros(3)
    count = 0
    for seed in range(n_seeds):
        rows = run_build(n_layers, dwell=dwell, seed=seed)
        rng = np.random.default_rng(seed + 1000)
        state = SensorState(rng)
        ekf = EKF()
        prev_H = 0.0
        for i, r in enumerate(rows):
            obs_raw = observe(r, prev_H, state)
            ekf.update(obs_raw, {"wfs": 70, "ts": 10, "r_z": 1.5, "dwell": dwell},
                       active_sensors=subset if subset else set())
            prev_H = r["H_out"]
            if i >= n_layers - 10:
                P_diag_accum += np.array([ekf.P[j, j] for j in STATE_IDX])
                count += 1
    return P_diag_accum / count


def compute_crb_table():
    subsets = sensor_subsets()
    labels = [subset_label(s) for s in subsets]
    crb = np.zeros((len(subsets), 3))
    for i, s in enumerate(subsets):
        p_diag = run_ekf_subset(s)
        crb[i] = np.sqrt(p_diag)
    return labels, crb, subsets


def plot_gramian_heatmap(labels, crb, save_path=None):
    fig, ax = plt.subplots(figsize=(7, 5))

    crb_log = np.log10(crb + 1e-6)
    im = ax.imshow(crb_log, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{n} ({u})" for n, u in zip(STATE_NAMES, STATE_UNITS)])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("state")
    ax.set_ylabel("sensor subset")
    ax.set_title("CRB floor per sensor subset (log₁₀ scale)")

    for i in range(crb.shape[0]):
        for j in range(crb.shape[1]):
            val = crb[i, j]
            txt = f"{val:.2f}" if val < 100 else f"{val:.0f}"
            color = "white" if crb_log[i, j] > np.median(crb_log) else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=color)

    fig.colorbar(im, ax=ax, label="log₁₀(CRB floor)")
    fig.tight_layout()

    if save_path is None:
        OUT.mkdir(parents=True, exist_ok=True)
        save_path = OUT / "gramian_heatmap.png"

    buf = io.BytesIO()
    fig.savefig(buf, dpi=160, format="png")
    plt.close(fig)
    Path(save_path).write_bytes(buf.getvalue())
    return save_path


def gramian_summary(labels, crb):
    print(f"{'subset':<20} {'H (mm)':>8} {'s (mm)':>8} {'T (°C)':>8}")
    print("-" * 48)
    for i, lab in enumerate(labels):
        print(f"{lab:<20} {crb[i,0]:8.3f} {crb[i,1]:8.3f} {crb[i,2]:8.1f}")


if __name__ == "__main__":
    labels, crb, subsets = compute_crb_table()
    gramian_summary(labels, crb)
    p = plot_gramian_heatmap(labels, crb)
    print(f"\nfigure: {p}")
