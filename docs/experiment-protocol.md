# Experiment protocol

Revision dated 2026-11-01. The earlier results were reviewed before this protocol
was written. This is a corrected exploratory analysis, not a newly unseen test.
Original predictions and verdicts remain in the historical record.

## Builds and splits

The main comparison uses 31 layers, 60 s dwell, two controller gains (0.5, 1),
and 30 evaluation seeds (0-29). Training uses seeds 100-149 at dwell settings
0, 30, 60, 120 and 240 s. The exact same fitted models are used for nominal,
20% scanner-dropout and generator-variant evaluations. A separate 90 s dwell
condition, absent from training, is also evaluated.

All estimators receive only sensor observations and known controls. Truth
parameters and state labels are used for supervised training and evaluation,
not passed to an evaluated estimator. Build variation and sensor errors are
specified in [the model notes](design/process-and-sensor-model.md).

## Perturbations

| Name | What changes | Who sees a changed observation stream? |
|---|---|---|
| width_temperature | EKF assumed width-temperature slope multiplied by 1+level | Truth stays fixed; each estimator still drives its own build |
| cooling_time | EKF assumed base cooling time multiplied by 1+level | Same interpretation as above |
| ctwd_curve | True CTWD quadratic coefficient multiplied by 1+level | Every estimator |

Levels are 0, 0.15, 0.30 and 0.60. Percentages describe parameter changes,
not equal physical severity. Width/thermal tests deliberately perturb the EKF;
CTWD is a measurement-domain shift. Their results should not be pooled as
interchangeable error axes.

The generator variant uses shape factor 3/4, cooling exponent 0.85 and a
+0.5 mm CTWD offset. It has already been inspected. It is now a sensitivity
condition, not a sealed validation set. No tuning is performed to obtain a
preferred ranking or crossover.

## Outcomes and uncertainty

Final wall error is abs(final H - target H). State errors are per-build RMSE
on layer-end height, standoff and temperature. The scanner reads previous-layer
height. Dropout-only H/S errors exclude the first layer, where no previous
wall exists to scan. If a build has no missing scans, its dropout RMSE is
undefined (blank in CSV), not zero.

Plots show medians and bootstrap intervals. Report tables use mean build RMSE.
For the improvement check, baseline and candidate are paired by build seed.
A bootstrap resamples complete paired builds, not individual time steps.

The replacement improvement check has three categories:

1. Layer-end standoff RMSE at nominal dropout.
2. Temperature RMSE with pyrometer drift at nominal dropout.
3. Joint dropout error sqrt(H_RMSE^2 + S_RMSE^2), in mm, at 20% dropout.

For each estimator, error type, gain, and zero/low error level, a category passes
with at least 30 valid pairs, at least 10% reduction in mean build RMSE, and a
95% interval for mean absolute improvement wholly above zero. At least two
categories must pass in every condition to satisfy the full replacement check.
A failed or incomplete check remains a reported result. No familywise
multiple-comparison adjustment is applied, so individual intervals are descriptive.

This check does not recover the original promise of within-layer standoff
accuracy, which a layerwise simulator cannot measure.

## Sensor subsets

All eight subsets are evaluated separately for EKF and learned estimators.
Each learned subset, including the empty set, uses 100 training builds: seeds
100-119 at the five training dwell settings. Test seeds remain 0-29. Three
30% perturbation conditions are evaluated. No test-selected combination of
individual state predictions is reported as an implemented estimator.

Composite error is sqrt((H/1 mm)^2 + (S/1 mm)^2 + (T/10 C)^2), calculated per
build and then averaged. Sensor costs are assumed relative units: scanner 5,
pyrometer 2, CTWD 1. Pareto fronts use cost and composite error. Exact Shapley
values attribute negative composite error within each estimator and condition;
they do not include sensor cost. Close subset ranks have no significance claim.

The uncertainty diagnostic compares EKF predicted standard deviation with
empirical RMSE over the last ten of 31 replayed layers. It is neither a
Cramer-Rao bound nor an observability Gramian, and no steady state is assumed.

## Reproduction

Run `python src/run_experiments.py` and `python src/run_sensor_analysis.py`.
The experiment manifest records training/evaluation settings, package versions,
and SHA-256 digests of the experiment source. Existing outputs are replaced;
copy them before changing the protocol. The pre-revision files are preserved
under `reports/archive/` and in local Git history.
