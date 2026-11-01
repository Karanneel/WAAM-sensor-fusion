> Historical record. The claims below were subsequently corrected; see ../decisions/revision-2026-11-01.md.

# Pre-registration

Written before any code. Once the **Frozen** line below has a date, nothing above it changes. A later change goes in a dated addendum at the bottom, with the reason, and the original stays visible. This is the same discipline as the Off the Pace gate.

**Status:** FROZEN
**Frozen:** 2026-10-26 by Karan

---

## 1. Predictions

| # | Prediction | Karan's expected answer |
|---|---|---|
| P1 | At zero planted error, which estimator has the lowest final wall-height error? | Kalman filter wins, because the simulator's physics is also its model |
| P2 | At what planted-error level (low / mid / high) does the learned model overtake the Kalman filter on final wall error? | Mid |
| P3 | Does the state-RMSE ranking match the final-wall-error ranking at every error level? | No, cannot match at every level, expect at least one flip |
| P4 | Does the naive "carry last scan forward" baseline come within 10% of the best estimator on final wall-height error? | Sometimes, under a few conditions, not every condition |
| P5 | Which unmeasured state benefits most from fusion: standoff between scans, drifted temperature, or dropout periods? | Standoff between scans |

## 2. Stop 0: PIONEER probe (4 h box)

**Status: PASSED on 2026-10-18. GO.**

Original go/no-go rules kept here for the record:

- **GO required all three:**
  - At least 3 walls whose post-build STL scans resolve height along the wall well enough to compare hot vs cold regions
  - Thermocouple or IR logs give an interlayer temperature series for at least 3 dwell settings
  - Data loads in Python within the 4 h box
- **What passed:** G1 passed on wall-top height difference (42 mm vs 64 mm, hot vs cold, diff 21.4 mm). G2 passed on peak-temperature spread across walls (3 of 6 dwells loaded, 31 °C spread). G3 passed, 0.1 min elapsed.
- **Dataset note:** only 2 of 6 walls have `Robot_Layer` logged directly. 3 of the remaining 4 walls have no position data at all. Thermal calibration uses dwells 30, 60, 240 s.

## 3. Core gate (end of stop A)

- **Metric:** RMSE on states the scanner does **not** measure directly:
  1. standoff between scans;
  2. part temperature under pyrometer drift;
  3. height and standoff during scanner dropout periods.
- **Pass:** the best non-naive estimator beats the naive baseline by at least **10%** on at least 2 of the 3 states, at the zero and low planted-error levels, averaged over at least 30 seeded builds, with the 95% interval excluding zero improvement.
- **Fail:** report the null result as the finding. Do not add estimators, tune further, or change the metric to rescue it.
- **Why not height RMSE:** one scan per layer already nearly fixes height for a slow layer-to-layer loop, so a height-RMSE gate fails by construction.
- **Threshold note:** 10% is inherited from Off the Pace, not derived from the process (ASSUMPTION).

## 4. Structural vs model-dependent

A finding is labelled **structural** only if it holds across:
- all 3 planted error types (f_w, τ, CTWD map), and
- both controller gains, and
- the sealed generator variant (run once, at the end).

Once the DED extensions exist, it must also hold on at least one DED variant. Every other finding is **model-dependent** and stays out of the headline and the README summary.

## 5. Sealed generator variant

Defined and saved, unrun, before any estimator is tuned. The sealed variant differs from the main generator in these three ways:

- **Thermal:** cooling exponent changed. The lumped balance in the main generator uses `exp(-t/τ)`. The sealed variant uses `exp(-(t/τ)^β)` with β ≠ 1, giving a different cooling-curve shape at matched τ.
- **Geometry:** shape factor c_shape changes from 2/3 (parabolic cap) to 3/4 (fuller cap). This changes the height-width split at matched area and width.
- **CTWD map:** 0.5 mm bias added to the arc-signal-to-standoff map. The main generator has zero mean error; the sealed variant has a constant offset.

The sealed variant runs **once**, after all tuning on the main generator, after the main core gate has been evaluated. Its result is reported whatever it shows.

## Addenda

### 2026-10-31, Stop A verdict

**Overall core gate:** PASS. At zero and low planted-error levels, both EKF and learned beat naive by 10%+ on 2 of 3 unmeasured states.

**Prediction scores:**

| # | Prediction | Reality | Verdict |
|---|---|---|---|
| P1 | KF wins at zero error | EKF wins H and standoff; learned wins T | Half |
| P2 | Learned overtakes KF at mid level | Learned beats EKF on T at any fw error; on standoff at ~0.5 fw | Half (right direction, wrong level) |
| P3 | State ranking ≠ wall-error ranking | Wall error identical across all estimators and conditions; state rankings vary | Confirmed strongly |
| P4 | Naive within 10% of best sometimes | Never within 10% on standoff or T; naive beats learned on H | Wrong direction |
| P5 | Standoff benefits most from fusion | H benefits most (naive→EKF: 67%). T benefits most via learned (naive→learned: 38%) | Wrong state |

**Three honest-check findings:**

1. **Sealed-variant check (2026-10-31):** rankings on wall_err match main generator 24/24 (100%); state-RMSE rankings match 0-29% depending on metric. So the Q8 finding is **structural**; every state-level ranking is **model-dependent**.
2. **Oracle floor (2026-10-31):** EKF matches oracle to 3 decimals on H at zero error. Fusion with correct physics is at the achievable floor; a KalmanNet-style hybrid has nothing left to gain in the quiet regime.
3. **Scanner-dropout stress at 20% (2026-10-31):** EKF holds at 0.028 mm H RMSE; learned catastrophically fails at 6.8 mm (factor 240×). Validates the pre-registered claim that model-based fusion wins when direct sensors are unreliable.

**Headline conclusion:** at this operating point, under the fixed layer-to-layer controller, estimator choice does not reach the final wall. Oracle = EKF = learned = naive on wall_err. The state-RMSE differences do not propagate to the outcome.

**Open decisions resolved by stop A:**
- D4 (fast in-layer loop): parked (not added, stop A finished with layer-to-layer only).
- D5 (gate threshold 10%): kept at 10%, gate passed.
