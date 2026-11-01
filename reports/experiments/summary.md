# Estimator comparison

Generated with the revised 2026-11-01 protocol. Errors below are means across 30 independent test builds.
These are simulation results. They do not validate a WAAM cell or establish an optimal estimator.

| Condition | Estimator | Final height error (mm) | H RMSE (mm) | S RMSE (mm) | T RMSE (C) |
|---|---|---:|---:|---:|---:|
| model_error | EKF | 0.2507 | 0.0561 | 0.1421 | 7.6833 |
| model_error | learned | 0.2331 | 0.1828 | 0.1423 | 2.9280 |
| model_error | naive | 0.2301 | 0.0820 | 0.1965 | 5.0917 |
| model_error | reference | 0.2506 | 0.0560 | 0.1607 | 7.6889 |
| model_error | schedule_only | 1.2944 | 0.7942 | 0.8138 | 2.0967 |
| dropout | EKF | 0.2564 | 0.0643 | 0.1422 | 7.6435 |
| dropout | learned | 0.4140 | 0.6465 | 0.2650 | 2.9362 |
| dropout | naive | 0.2346 | 0.1001 | 0.1965 | 5.0917 |
| dropout | reference | 0.2563 | 0.0642 | 0.1608 | 7.6493 |
| dropout | schedule_only | 1.2944 | 0.7942 | 0.8138 | 2.0967 |
| generator_variant | EKF | 0.9788 | 0.1939 | 0.4676 | 32.6283 |
| generator_variant | learned | 0.8700 | 0.3116 | 0.3159 | 4.3635 |
| generator_variant | naive | 0.9085 | 0.0550 | 0.5453 | 5.0320 |
| generator_variant | reference | 0.8937 | 0.0575 | 0.1608 | 6.9600 |
| generator_variant | schedule_only | 5.4254 | 3.3267 | 3.3846 | 10.7488 |
| unseen_dwell | EKF | 0.3988 | 0.0613 | 0.1428 | 6.6956 |
| unseen_dwell | learned | 0.4027 | 0.1721 | 0.1476 | 4.7658 |
| unseen_dwell | naive | 0.3649 | 0.0859 | 0.1965 | 5.0036 |
| unseen_dwell | reference | 0.3988 | 0.0612 | 0.1609 | 6.7014 |
| unseen_dwell | schedule_only | 2.1996 | 1.2834 | 1.2585 | 20.3716 |

## Paired improvement check

The three categories are layer-end standoff, drifted temperature, and dropout-only joint height/standoff error.
For each error type, gain and zero/low error level, a category passes with at least 10% lower mean build RMSE and a paired-bootstrap 95% interval for improvement above zero.
Each category requires 30 valid paired builds. The first layer is excluded from dropout scoring.

- EKF: at least two categories pass in 12/12 conditions.
- learned: at least two categories pass in 12/12 conditions.

This check replaces the earlier, unsupported pass statement; it does not retroactively validate the original protocol.

## Generator sensitivity

The variant was inspected before this revision and is not an unseen validation set. Near-equal point estimates are treated as ties within 1e-6; no significance is inferred from a winner label.

- wall_err: matching minimum-mean estimator sets in 0/24 conditions.
- rmse_H: matching minimum-mean estimator sets in 12/24 conditions.
- rmse_s: matching minimum-mean estimator sets in 0/24 conditions.
- rmse_T: matching minimum-mean estimator sets in 0/24 conditions.
