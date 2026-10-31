"""
pre-registered sealed-variant check. runs the same sweep on a generator with
three locked-in changes:
  thermal:  cooling exponent 0.85 (stretched exponential)
  geometry: shape factor 2/3 -> 3/4
  CTWD:     +0.5mm bias from the start

the estimators (naive, EKF, learned) are UNCHANGED. learned was trained on
the main generator. this tests whether the stop-A rankings survive on a
different-but-similar generator. matching rankings = structural finding
"""

import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from learned import train_models
from sweep import run_sweep


OUT = Path(__file__).resolve().parents[1] / "reports" / "stopA_sim"
OUT.mkdir(parents=True, exist_ok=True)


def overlay_plot(df_main, df_sealed, metric, ylabel, out_name):
    """main generator solid, sealed dashed; one panel per error_type x gain"""
    error_types = sorted(df_main["error_type"].unique())
    gains = sorted(df_main["gain"].unique())
    fig, ax = plt.subplots(len(gains), len(error_types),
                           figsize=(4.5 * len(error_types), 3.5 * len(gains)),
                           sharex="col", sharey="row", squeeze=False)
    colors = {"naive": "C3", "EKF": "C0", "learned": "C2"}
    for i, g in enumerate(gains):
        for j, et in enumerate(error_types):
            a = ax[i][j]
            for df, ls, lbl in [(df_main, "-", "main"),
                                (df_sealed, "--", "sealed")]:
                sub = df[(df["gain"] == g) & (df["error_type"] == et)]
                for name, grp in sub.groupby("estimator"):
                    agg = grp.groupby("level")[metric].median().reset_index()
                    a.plot(agg["level"], agg[metric], marker="o",
                           color=colors[name], ls=ls, lw=1.4,
                           label=f"{name} ({lbl})" if (i == 0 and j == 0) else None)
            a.set_title(f"error={et}, gain={g}")
            if i == len(gains) - 1:
                a.set_xlabel("planted error level")
            if j == 0:
                a.set_ylabel(ylabel)
            a.grid(alpha=0.3)
            if i == 0 and j == 0:
                a.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    out = OUT / out_name
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    out.write_bytes(buf.getvalue())
    return out


def winners(df, metric):
    """for each (error_type, level, gain) cell, which estimator wins on metric"""
    agg = df.groupby(["error_type", "level", "gain", "estimator"])[metric] \
            .median().reset_index()
    out = {}
    for (et, lv, g), sub in agg.groupby(["error_type", "level", "gain"]):
        winner = sub.loc[sub[metric].idxmin(), "estimator"]
        out[(et, lv, g)] = winner
    return out


if __name__ == "__main__":
    print("training learned model on MAIN generator...")
    train_builds = [(d, s) for d in (0, 30, 60, 120, 240) for s in range(10, 14)]
    t0 = time.time()
    models = train_models(train_builds)
    print(f"  took {time.time() - t0:.1f} s")

    print("running sweep on SEALED generator...")
    t0 = time.time()
    df_sealed = run_sweep(models, n_seeds=30, sealed=True)
    print(f"  took {time.time() - t0:.1f} s, {len(df_sealed)} runs")

    csv_sealed = OUT / "sweep_sealed.csv"
    df_sealed.to_csv(csv_sealed, index=False)
    print(f"wrote {csv_sealed}")

    # load prior main-generator sweep
    csv_main = OUT / "sweep_results.csv"
    df_main = pd.read_csv(csv_main)
    print(f"loaded main sweep: {csv_main}")

    # overlay figure for the headline metric (T RMSE under fw)
    for metric, ylabel, name in [
        ("rmse_T",   "T RMSE (°C)",         "sealed_vs_main_T.png"),
        ("rmse_s",   "standoff RMSE (mm)",  "sealed_vs_main_s.png"),
        ("rmse_H",   "H RMSE (mm)",         "sealed_vs_main_H.png"),
        ("wall_err", "wall error (mm)",     "sealed_vs_main_wallerr.png"),
    ]:
        p = overlay_plot(df_main, df_sealed, metric, ylabel, name)
        print(f"figure: {p}")

    # structural vs model-dependent: compare winners cell by cell
    print("\n=== rankings: main vs sealed ===")
    for metric in ["rmse_H", "rmse_T", "rmse_s", "wall_err"]:
        wm = winners(df_main, metric)
        ws = winners(df_sealed, metric)
        matches = sum(1 for k in wm if wm[k] == ws[k])
        total = len(wm)
        print(f"\n  metric={metric}")
        print(f"    cells with matching winner: {matches}/{total} "
              f"({100*matches/total:.0f}%)")
        # flag cells where winner changed
        flips = [(k, wm[k], ws[k]) for k in wm if wm[k] != ws[k]]
        for (et, lv, g), w_main, w_sealed in flips:
            print(f"    FLIP: error={et}, level={lv:.2f}, gain={g}: "
                  f"main={w_main} -> sealed={w_sealed}")
