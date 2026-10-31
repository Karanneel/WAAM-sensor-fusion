"""
scanner-dropout stress test. pre-registered as a core gate state.

reruns the sweep with spatter_p = 0.20 (10x nominal). shows how each
estimator holds up when the direct height sensor is blocked 1 layer in 5
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from learned import train_models
from sweep import run_sweep
from plot_crossover import plot_crossover
from run_sweep import METRICS


OUT = Path(__file__).resolve().parents[1] / "reports" / "stopA_sim"
OUT.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print("training learned model...")
    train_builds = [(d, s) for d in (0, 30, 60, 120, 240) for s in range(10, 14)]
    t0 = time.time()
    models = train_models(train_builds)
    print(f"  took {time.time() - t0:.1f} s")

    print("running dropout sweep (spatter_p=0.20)...")
    t0 = time.time()
    df = run_sweep(models, n_seeds=30, dropout_p=0.20)
    print(f"  took {time.time() - t0:.1f} s, {len(df)} runs")

    csv = OUT / "sweep_dropout.csv"
    df.to_csv(csv, index=False)
    print(f"wrote {csv}")

    for metric, ylabel, name in METRICS:
        out_path = OUT / name.replace("crossover_", "dropout_")
        p = plot_crossover(df, metric, ylabel, out_path)
        print(f"figure: {p}")

    # quick summary of dropout effect
    import pandas as pd
    print("\n=== dropout stress at level=0 (zero planted error) ===")
    base = df[(df["level"] == 0.0) & (df["gain"] == 1.0)
              & (df["error_type"] == "fw")]
    for name, grp in base.groupby("estimator"):
        print(f"  {name:>10}: H RMSE {grp['rmse_H'].median():.3f} mm, "
              f"standoff RMSE {grp['rmse_s'].median():.3f} mm")
