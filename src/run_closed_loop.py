"""Plot a controlled build, its estimates and applied controls."""

import io
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from harness import run_closed_loop
from estimators import Naive
from ekf import EKF
from learned import Learned, train_models


OUT = Path(__file__).resolve().parents[1] / "reports" / "experiments"
OUT.mkdir(parents=True, exist_ok=True)


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


def plot_run(name, rows, estimates, controls, metrics):
    layers = np.array([r["layer"] for r in rows])
    H_true = np.array([r["H_out"] for r in rows])
    s_true = np.array([r["standoff"] for r in rows])
    T_true = np.array([r["T_out"] for r in rows])

    H_est = np.array([e["H"] for e in estimates])
    s_est = np.array([e["standoff"] for e in estimates])
    T_est = np.array([e["T"] for e in estimates])

    # Plot controls applied to the current layer, not the next command.
    ts_cmd = np.array([r["ts"] for r in rows])
    r_z = np.array([r["r_z"] for r in rows])

    fig, ax = plt.subplots(1, 5, figsize=(20, 4))
    for a, truth, pred, ylab, title in [
        (ax[0], H_true, H_est, "wall top (mm)", f"{name}: H"),
        (ax[1], s_true, s_est, "standoff (mm)", f"{name}: standoff"),
        (ax[2], T_true, T_est, "T (C)",         f"{name}: T"),
    ]:
        a.plot(layers, truth, label="truth",    color="k",  lw=2)
        a.plot(layers, pred,  label="estimate", color="C0", lw=1.4)
        a.set_xlabel("layer"); a.set_ylabel(ylab); a.set_title(title)
        a.legend(); a.grid(alpha=0.3)

    ax[3].plot(layers, ts_cmd, label="ts (controller)", color="C1", lw=1.4)
    ax[3].axhline(10.0, color="k", lw=0.8, ls="--", label="nominal 10")
    ax[3].set_xlabel("layer"); ax[3].set_ylabel("ts (mm/s)")
    ax[3].set_title(f"{name}: travel speed")
    ax[3].legend(); ax[3].grid(alpha=0.3)

    ax[4].plot(layers, r_z, label="r_z (Z advance)", color="C2", lw=1.4)
    ax[4].axhline(1.8, color="k", lw=0.8, ls="--", label="nominal 1.8")
    ax[4].set_xlabel("layer"); ax[4].set_ylabel("r_z (mm)")
    ax[4].set_title(f"{name}: Z advancement")
    ax[4].legend(); ax[4].grid(alpha=0.3)
    fig.tight_layout()

    out = OUT / f"cl_{name}.png"
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    out.write_bytes(buf.getvalue())
    return out


if __name__ == "__main__":
    print("training learned model...")
    models = train_models()

    n_layers, dwell, seed = 31, 60, 1

    results = {}
    for name, builder in [
        ("naive",   lambda: Naive()),
        ("EKF",     lambda: EKF()),
        ("learned", lambda: Learned(models)),
    ]:
        rows, est, ctrl, metrics, _ = run_closed_loop(
            n_layers, dwell, seed, estimator_builder=builder,
            controller_gain=1.0,
        )
        results[name] = (rows, est, ctrl, metrics, score(rows, est))

    print(f"\n{'estimator':>10} {'final H':>10} {'wall err':>10} "
          f"{'last S':>10} {'mean ts':>10} {'RMSE H':>10} {'RMSE T':>10} {'RMSE s':>10}")
    for name, (rows, est, ctrl, m, s) in results.items():
        print(f"{name:>10} {m['final_H']:>10.2f} {m['wall_err']:>10.2f} "
              f"{m['last_standoff']:>10.2f} {m['mean_ts']:>10.2f} "
              f"{s['H']:>10.3f} {s['T']:>10.2f} {s['standoff']:>10.3f}")

    for name, (rows, est, ctrl, m, s) in results.items():
        p = plot_run(name, rows, est, ctrl, m)
        print(f"figure {name}: {p}")
