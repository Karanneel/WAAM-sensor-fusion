# Simulation Field

**At this operating point, under a fixed WAAM layer-to-layer height controller, estimator choice does not reach the final wall.**

A simulated robotic wire-arc additive manufacturing (WAAM) wall testbed where every sensor fusion choice is scored against known truth. Four estimators (naive baseline, extended Kalman filter, gradient-boosted learned model, oracle) are compared across planted process-model errors, generator variations, and scanner dropouts, using a pre-registered gate from the start.

## Status

| Stop | Content | Status |
|---|---|---|
| 0 | PIONEER probe (real WAAM data) | GO |
| A | Simulator, sensors, 3 estimators + oracle, controller, 3 sweeps (planted error, dropout, sealed) | Complete |
| B | Observability (Gramian / Fisher information) + sensor-value Pareto front | Complete |
| Later | Wire-laser DED module, powder DED module, parked items | See [docs/future-work.md](docs/future-work.md) |

## Results & honest limits

Three structural findings that survive the pre-registered sealed-variant check, the oracle floor comparison, and 20% scanner dropout.

### 1. Final wall-height error is estimator-invariant

Oracle, EKF, learned and naive all produce **1.015 mm final wall error** across every planted-error cell. The fixed layer-to-layer controller absorbs estimator noise before it reaches the outcome. This is the strongest Q8 statement the project supports: at this operating point, estimator sophistication does not change the part.

### 2. EKF matches oracle at zero error

On H and standoff RMSE, the extended Kalman filter sits on the oracle line (correct physics, correct nonlinear CTWD inversion) at zero planted error. Fusion with correct physics is already at the achievable floor. A hybrid KF+NN (KalmanNet-style) has nothing left to gain in the quiet regime.

### 3. Learned model fails under scanner dropouts

At 20% dropout, learned H RMSE is **6.8 mm against EKF's 0.028 mm — a factor of 240×**. Model-based physics propagation carries the KF through blocked scans. The learned model, having never seen 5-6 consecutive dropouts in training, extrapolates onto chaos. Pre-registered claim validated: fusion wins when direct sensors are unreliable.

### Pre-registration verdict

| # | Prediction | Verdict |
|---|---|---|
| P1 | KF wins at zero error | **Half**. EKF wins H and standoff; learned wins T |
| P2 | Learned overtakes KF at mid error | **Half**. Learned beats EKF on T at any fw error |
| P3 | State RMSE ranking ≠ wall-error ranking | **Confirmed strongly** |
| P4 | Naive within 10% of best sometimes | **Wrong**. Naive never within 10% on standoff/T |
| P5 | Standoff benefits most from fusion | **Wrong**. H benefits most |

Three of five predictions were wrong or half-right. That is the pre-reg doing its job.

### What is model-dependent (fails sealed check)

Specific "which estimator wins on which state" claims. On the sealed generator, naive wins H and T, learned wins standoff. The famous "EKF collapses on T under fw error" result is a feature of the main generator, not a universal truth.

### Honest limits

- Thermal model does not include spatial gradient along the wall. Teixeira 2023 shows ~200 °C variation along a WAAM layer; we use a single-node lumped balance.
- Learned trained on 20 builds without proper GroupKFold within training. Hyperparameters were not tuned.
- CTWD placeholder is a scalar nonlinearity, not the Bratzel 2022 LSTM. Real arc-signal-to-CTWD regression would be more complex.
- Hardware never run. Numbers are simulated, calibrated against PIONEER WAAM data (Zenodo 17608626) but not validated against a HiWi cell.
- EKF Jacobian ignores the ∂τ/∂H coupling (small per-step effect, absorbed by Q).

## Methodology inspiration

Not borrowed from WAAM. The workflow (simulated testbed + multiple estimators + planted-error sweep + crossover + sealed check) is standard in these fields:

- **MultiCorrupt** ([arXiv 2402.11677](https://arxiv.org/abs/2402.11677)): AV sensor-fusion robustness benchmark with corruption types × severity levels. Our planted-error sweep structure.
- **KalmanNet** (Revach et al., IEEE TSP 2022, [arXiv 2107.10043](https://arxiv.org/abs/2107.10043)): KF vs learned vs hybrid on nonlinear tracking. Our EKF-vs-learned comparison mirrors theirs.
- **Tennessee Eastman Process** (Downs & Vogel 1993): classic chemical-process benchmark with planted faults. 30+ years of pre-registered-style discipline.
- **EuRoC MAV** / TUM-RGBD SLAM benchmarks: state RMSE (trajectory) vs outcome error (mapping) distinction, same shape as our state RMSE vs wall_err finding.

No targeted-search result found that applies this method to WAAM. The simulation-based scoring is the contribution.

## How to run

```bash
pip install -r requirements.txt

# physics + estimator smoke tests
python src/run_waam.py            # simulator sweep over dwell
python src/run_sensors.py         # sensor truth-vs-obs plot
python src/run_estimators.py      # open-loop estimator comparison
python src/run_closed_loop.py     # closed-loop estimator comparison

# the main results
python src/run_sweep.py           # 2880-run planted-error sweep + 4 figures
python src/run_dropout_sweep.py   # scanner-dropout stress test
python src/run_sealed_check.py    # pre-registered sealed-variant check

# stop B: observability + sensor value
python src/run_stopB.py           # CRB floors + Shapley + Pareto front

# the stop-0 real-data probe
python src/probe_pioneer.py       # PIONEER WAAM GO/NO-GO (already run)
```

Total end-to-end runtime on a laptop: about 90 seconds.

## Layout

```
simulation-field/
  src/
    process.py            waam bead physics (mass conservation, width/height split)
    simulator.py          layer-by-layer open-loop simulator
    sensors.py            scanner, pyrometer, CTWD placeholder
    harness.py            closed-loop sim + estimator + controller
    estimators.py         naive baseline
    ekf.py                extended kalman filter + KFParams dataclass
    learned.py            gradient-boosted regressor estimator
    oracle.py             EKF with true params + correct nonlinear CTWD
    sweep.py              planted-error sweep over estimators
    plot_crossover.py     bootstrap-CI crossover plots
    run_*.py              entry points
    probe_pioneer.py      stop 0 PIONEER probe
  docs/
    decisions/
      pre-registration.md       frozen 2026-10-26
      decisions-log.md          dated decisions
      source-corrections.md     v0.1 citation fixes
    design/
      original-plan-v0.1.md     first plan, kept as written
      process-and-sensor-model.md  equations and sources
    learning-path.md
    future-work.md
    README.md
  data/
    pioneer_17608626/     downloaded PIONEER walls (git-ignored)
    README.md             dataset manifest
  reports/
    stop0/                PIONEER probe figures
    stopA_sim/            all crossover + dropout + sealed figures + CSVs
    stopB/                observability heatmap + Pareto front
```

## Key figures

In `reports/stopA_sim/`:

| File | Shows |
|---|---|
| `dropout_rmse_H.png` | Learned collapses at 6.8 mm, EKF holds at 0.028 mm. The 240× gap |
| `crossover_rmse_T.png` | EKF matches oracle at zero fw error, diverges to 13.3 °C at fw=0.60 |
| `crossover_wall_err.png` | All four estimators overlap at 1.015 mm. Q8 answer |
| `sealed_vs_main_T.png` | Rankings do not survive the sealed check on T |
| `sweep_results.csv` | All 2880 planted-error runs |
| `sweep_dropout.csv` | All 2880 dropout runs |
| `sweep_sealed.csv` | All 2160 sealed-generator runs |

## Links

- [docs/decisions/pre-registration.md](docs/decisions/pre-registration.md) — frozen 2026-10-26. Predictions P1-P5, sealed variant, core gate.
- [docs/design/process-and-sensor-model.md](docs/design/process-and-sensor-model.md) — equations, sensor models, calibration targets.
- [docs/decisions/source-corrections.md](docs/decisions/source-corrections.md) — citation fixes from the v0.1 plan.
- [docs/future-work.md](docs/future-work.md) — wire-laser DED module, powder DED module, parked method items.
