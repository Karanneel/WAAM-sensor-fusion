"""
smoke test for the waam generator. sweeps dwell and plots wall height and
interlayer temperature. qualitative check: does hot build shorter than cold?
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from simulator import run_build


OUT = Path(__file__).resolve().parents[1] / "reports" / "stopA_sim"
OUT.mkdir(parents=True, exist_ok=True)


def plot_sweep(dwells=(0, 30, 60, 120, 240), n_layers=31):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for d in dwells:
        rows = run_build(n_layers, dwell=d)
        layers = [r["layer"] for r in rows]
        tops = np.cumsum([r["height"] for r in rows])
        T = [r["T_out"] for r in rows]
        ax[0].plot(layers, tops, marker=".", label=f"{d} s")
        ax[1].plot(layers, T, marker=".", label=f"{d} s")
    ax[0].set_xlabel("layer")
    ax[0].set_ylabel("wall top above base (mm)")
    ax[0].set_title("simulated wall height, by dwell")
    ax[0].legend(title="dwell"); ax[0].grid(alpha=0.3)
    ax[1].set_xlabel("layer")
    ax[1].set_ylabel("interlayer T (°C)")
    ax[1].set_title("simulated interlayer temperature, by dwell")
    ax[1].legend(title="dwell"); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    out = OUT / "build_sweep.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def summary(dwells=(0, 30, 60, 120, 240), n_layers=31):
    print(f"{'dwell':>6} {'top (mm)':>10} {'peak T':>8} {'end T':>8}")
    for d in dwells:
        rows = run_build(n_layers, dwell=d)
        top = sum(r["height"] for r in rows)
        T = [r["T_out"] for r in rows]
        print(f"{d:>6} {top:>10.1f} {max(T):>8.0f} {T[-1]:>8.0f}")


if __name__ == "__main__":
    summary()
    p = plot_sweep()
    print(f"\nfigure: {p}")
