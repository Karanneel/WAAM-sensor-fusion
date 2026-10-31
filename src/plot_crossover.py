"""
crossover plot with bootstrap 95% confidence intervals around the median.

shared by run_sweep.py and run_dropout_sweep.py
"""

import io
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


COLORS = {"naive": "C3", "EKF": "C0", "learned": "C2", "oracle": "k"}
N_BOOT = 400


def _bootstrap_median_ci(x, n_boot=N_BOOT, alpha=0.05):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        m = float(np.median(x)) if len(x) else np.nan
        return m, m, m
    rng = np.random.default_rng(0)
    boots = np.median(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)
    med = float(np.median(x))
    lo = float(np.percentile(boots, 100 * alpha / 2))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return med, lo, hi


def plot_crossover(df, metric, ylabel, out_path):
    """4 or 6 panels: gain (rows) × error_type (cols). bootstrap 95% CI shaded"""
    error_types = sorted(df["error_type"].unique())
    gains = sorted(df["gain"].unique())
    fig, ax = plt.subplots(len(gains), len(error_types),
                           figsize=(4.5 * len(error_types), 3.5 * len(gains)),
                           sharex="col", sharey="row", squeeze=False)
    for i, g in enumerate(gains):
        for j, et in enumerate(error_types):
            a = ax[i][j]
            sub = df[(df["gain"] == g) & (df["error_type"] == et)]
            for name, grp in sub.groupby("estimator"):
                xs, meds, los, his = [], [], [], []
                for lv, cell in grp.groupby("level"):
                    m, lo, hi = _bootstrap_median_ci(cell[metric].values)
                    xs.append(lv); meds.append(m); los.append(lo); his.append(hi)
                color = COLORS.get(name, None)
                a.plot(xs, meds, marker="o", color=color, label=name, lw=1.6)
                a.fill_between(xs, los, his, color=color, alpha=0.18)
            a.set_title(f"error={et}, gain={g}")
            if i == len(gains) - 1:
                a.set_xlabel("planted error level")
            if j == 0:
                a.set_ylabel(ylabel)
            a.grid(alpha=0.3)
            if i == 0 and j == 0:
                a.legend(fontsize=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    Path(out_path).write_bytes(buf.getvalue())
    return out_path
