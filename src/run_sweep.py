"""
main planted-error sweep. trains learned model, runs sweep, saves CSV plus
four bootstrap-CI crossover figures. ~15s compute
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from learned import train_models
from sweep import run_sweep
from plot_crossover import plot_crossover


OUT = Path(__file__).resolve().parents[1] / "reports" / "stopA_sim"
OUT.mkdir(parents=True, exist_ok=True)


METRICS = [
    ("rmse_s",   "standoff RMSE (mm)",    "crossover_rmse_s.png"),
    ("rmse_H",   "H RMSE (mm)",           "crossover_rmse_H.png"),
    ("rmse_T",   "T RMSE (°C)",           "crossover_rmse_T.png"),
    ("wall_err", "final wall error (mm)", "crossover_wall_err.png"),
]


if __name__ == "__main__":
    print("training learned model...")
    train_builds = [(d, s) for d in (0, 30, 60, 120, 240) for s in range(10, 14)]
    t0 = time.time()
    models = train_models(train_builds)
    print(f"  took {time.time() - t0:.1f} s")

    print("running sweep...")
    t0 = time.time()
    df = run_sweep(models, n_seeds=30)
    print(f"  took {time.time() - t0:.1f} s, {len(df)} runs")

    csv = OUT / "sweep_results.csv"
    df.to_csv(csv, index=False)
    print(f"wrote {csv}")

    for metric, ylabel, name in METRICS:
        p = plot_crossover(df, metric, ylabel, OUT / name)
        print(f"figure: {p}")
