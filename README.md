# waam-sensor-fusion

A simulation testbed for comparing sensor fusion strategies in wire-arc additive manufacturing (WAAM). Four estimators (naive baseline, extended Kalman filter, gradient-boosted learned model, oracle) are scored against known ground truth across planted process-model errors, generator variations, and scanner dropout, with all predictions registered before code was written.

## Why this exists

Sensor fusion papers in additive manufacturing typically report accuracy on one dataset with one model. There is no open testbed that holds the process physics, the estimators, and the controller in one loop and asks: does a better state estimate actually produce a better part?

This project answers that question for a simulated WAAM single-bead wall. The simulator is calibrated against real WAAM data (PIONEER, Zenodo 17608626), and every finding is classified as structural or model-dependent using a sealed generator variant the estimators never saw during tuning.

## What it found

Three findings survive the sealed-variant check, the oracle floor, and 20% scanner dropout.

**1. Final wall error is estimator-invariant.** Oracle, EKF, learned and naive all produce 1.015 mm wall error. The fixed layer-to-layer controller absorbs estimator differences before they reach the part. At this operating point, estimator sophistication does not change the outcome.

**2. EKF matches oracle at zero planted error.** On height and standoff RMSE, the EKF sits on the oracle floor (correct physics, correct nonlinear CTWD inversion). Physics-based fusion with correct parameters is already at the achievable limit.

**3. Learned model fails under scanner dropout.** At 20% dropout, learned height RMSE is 6.8 mm versus EKF at 0.028 mm, a factor of 240x. The EKF propagates physics through blocked scans. The learned model, trained without consecutive dropout sequences, extrapolates into divergence.

Specific state-level rankings (which estimator wins on which state) are model-dependent: they change on the sealed generator. Only the wall-error invariance finding transfers.

## Architecture

Five-state EKF: layer height, standoff, part temperature, pyrometer bias, previous height. Three sensor channels: laser line scanner, pyrometer, CTWD (arc-signal placeholder). Eight sensor subsets (2^3) evaluated for observability via the noise-weighted Gramian and exact Shapley values.

The process model uses mass conservation for bead area, a height/width split governed by a shape factor, and a lumped thermal balance with a wall-height-dependent time constant. Planted errors (wire-feed slope, thermal time constant, CTWD map bias) are swept independently to map where each estimator breaks.

## Limitations

- Single-node lumped thermal model, no spatial gradient along the wall. Real WAAM layers show ~200 C variation along the bead (Teixeira 2023).
- CTWD channel is a scalar nonlinearity, not the Bratzel 2022 LSTM. Real arc-signal regression would be more complex.
- Learned estimator trained on 20 builds without GroupKFold within training. Hyperparameters not tuned.
- Hardware never run. All numbers are simulated, calibrated against PIONEER data but not validated on a live cell.
- EKF Jacobian ignores the d(tau)/dH coupling (small per-step, absorbed by Q tuning).

## How to run

```bash
pip install -r requirements.txt

# process and estimator verification
python src/run_waam.py
python src/run_sensors.py
python src/run_estimators.py
python src/run_closed_loop.py

# main results
python src/run_sweep.py             # planted-error sweep, 2880 runs
python src/run_dropout_sweep.py     # scanner dropout stress test
python src/run_sealed_check.py      # sealed-variant check

# stop B: observability and sensor value
python src/run_stopB.py             # CRB floors, Shapley, Pareto front

# real-data probe
python src/probe_pioneer.py         # PIONEER WAAM data check
```

End-to-end runtime: about 90 seconds on a laptop.

## Layout

```
src/
  process.py            bead physics (mass conservation, width/height split)
  simulator.py          layer-by-layer simulator
  sensors.py            scanner, pyrometer, CTWD placeholder
  ekf.py                extended Kalman filter
  learned.py            gradient-boosted regressor estimator
  oracle.py             EKF with true parameters
  estimators.py         naive baseline
  harness.py            closed-loop controller + estimator harness
  sweep.py              planted-error sweep engine
  observability.py      Gramian, Fisher information, CRB
  sensor_value.py       Shapley values, cost-weighted Pareto
  plot_crossover.py     bootstrap-CI crossover figures
  run_*.py              entry points
  probe_pioneer.py      PIONEER real-data probe
docs/
  decisions/
    pre-registration.md       predictions and gates, frozen 2026-10-26
    decisions-log.md          dated scope and method decisions
    source-corrections.md     citation fixes from the original plan
  design/
    process-and-sensor-model.md   equations, sensor models, calibration
    original-plan-v0.1.md         first plan, kept as written
  learning-path.md
reports/
  stop0/          PIONEER probe figures
  stopA_sim/      crossover, dropout, sealed figures and CSVs
  stopB/          observability heatmap, Pareto front
data/
  README.md       dataset manifest
```

## Key figures

| File | Shows |
|---|---|
| `reports/stopA_sim/crossover_wall_err.png` | All four estimators overlap at 1.015 mm wall error |
| `reports/stopA_sim/dropout_rmse_H.png` | Learned collapses at 6.8 mm, EKF holds at 0.028 mm |
| `reports/stopA_sim/crossover_rmse_T.png` | EKF tracks oracle at zero error, diverges under planted fw error |
| `reports/stopA_sim/sealed_vs_main_T.png` | State rankings do not survive the sealed check |
| `reports/stopB/gramian_heatmap.png` | Observability Gramian across sensor subsets |
| `reports/stopB/pareto_front.png` | Cost vs composite RMSE Pareto front |

## Methodology

The workflow (simulated testbed, multiple estimators, planted-error sweep, crossover analysis, sealed-variant check) draws from established practice outside AM:

- **MultiCorrupt** (arXiv 2402.11677): AV sensor-fusion robustness benchmark with corruption types and severity levels.
- **KalmanNet** (Revach et al., IEEE TSP 2022): KF vs learned vs hybrid on nonlinear state estimation.
- **Tennessee Eastman Process** (Downs and Vogel 1993): chemical-process benchmark with planted faults, 30+ years of use.

No prior work was found applying this method to WAAM.

## References

- [Pre-registration](docs/decisions/pre-registration.md): predictions P1-P5, gates, sealed variant definition.
- [Process and sensor model](docs/design/process-and-sensor-model.md): equations, parameters, calibration.
- [Source corrections](docs/decisions/source-corrections.md): citation fixes from the original plan.
