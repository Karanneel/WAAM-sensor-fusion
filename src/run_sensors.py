"""
sensor smoke test. one build at mid dwell, overlay truth vs sensor readings
for height, temperature, standoff.
"""

import io
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from simulator import run_build
from sensors import SensorState, observe


OUT = Path(__file__).resolve().parents[1] / "reports" / "stopA_sim"
OUT.mkdir(parents=True, exist_ok=True)


def run_with_sensors(n_layers=31, dwell=60, seed=1):
    rows = run_build(n_layers, dwell=dwell, seed=seed)
    # independent sensor seed so changing sim seed doesn't change sensor noise
    rng = np.random.default_rng(seed + 1000)
    state = SensorState(rng)
    obs = []
    prev_H = 0.0
    for r in rows:
        obs.append(observe(r, prev_H, state))
        prev_H = r["H_out"]
    return rows, obs


def plot_build(rows, obs):
    layers = np.array([r["layer"] for r in rows])
    # scanner sits behind the torch so at layer k it reads H_in[k] (= H_out[k-1])
    H_in = np.array([r["H_in"] for r in rows])
    H_out = np.array([r["H_out"] for r in rows])
    T_true = np.array([r["T_out"] for r in rows])
    s_true = np.array([r["standoff"] for r in rows])

    scan = np.array([o["scanner"] if o["scanner"] is not None else np.nan
                     for o in obs])
    pyro = np.array([o["pyro"] for o in obs])
    ctwd = np.array([o["ctwd"] for o in obs])

    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))

    ax[0].plot(layers, H_out, label="H end-of-layer", color="k", lw=2)
    ax[0].plot(layers, H_in, label="H the scanner sees", color="gray",
               lw=1, ls="--")
    ax[0].scatter(layers, scan, label="scanner reading", s=25, alpha=0.8)
    ax[0].set_xlabel("layer"); ax[0].set_ylabel("wall top (mm)")
    ax[0].set_title("height: truth vs scanner")
    ax[0].legend(); ax[0].grid(alpha=0.3)

    ax[1].plot(layers, T_true, label="truth", color="k", lw=2)
    ax[1].scatter(layers, pyro, label="pyrometer", s=25, alpha=0.8, color="C1")
    ax[1].set_xlabel("layer"); ax[1].set_ylabel("T (°C)")
    ax[1].set_title("temperature: truth vs pyrometer")
    ax[1].legend(); ax[1].grid(alpha=0.3)

    ax[2].plot(layers, s_true, label="truth", color="k", lw=2)
    ax[2].scatter(layers, ctwd, label="CTWD channel", s=25, alpha=0.8, color="C2")
    ax[2].set_xlabel("layer"); ax[2].set_ylabel("standoff (mm)")
    ax[2].set_title("standoff: truth vs CTWD channel")
    ax[2].legend(); ax[2].grid(alpha=0.3)

    fig.tight_layout()
    out = OUT / "sensor_sweep.png"
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    out.write_bytes(buf.getvalue())
    return out


def summary(rows, obs):
    dropouts = sum(1 for o in obs if o["scanner"] is None)
    print(f"layers: {len(rows)}, scanner dropouts: {dropouts}")
    # residuals, scanner against H_in (what it actually sees)
    H_in = np.array([r["H_in"] for r in rows])
    T_true = np.array([r["T_out"] for r in rows])
    s_true = np.array([r["standoff"] for r in rows])
    scan = np.array([o["scanner"] if o["scanner"] is not None else np.nan
                     for o in obs])
    pyro = np.array([o["pyro"] for o in obs])
    ctwd = np.array([o["ctwd"] for o in obs])
    print(f"scanner MAE:  {np.nanmean(np.abs(scan - H_in)):.3f} mm (vs H the scanner sees)")
    print(f"pyro MAE:     {np.mean(np.abs(pyro - T_true)):.1f} °C")
    print(f"CTWD MAE:     {np.mean(np.abs(ctwd - s_true)):.3f} mm "
          f"(standoff range {s_true.min():.1f}-{s_true.max():.1f} mm)")


if __name__ == "__main__":
    rows, obs = run_with_sensors()
    summary(rows, obs)
    p = plot_build(rows, obs)
    print(f"figure: {p}")
