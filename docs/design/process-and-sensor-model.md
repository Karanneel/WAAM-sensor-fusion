# Wall, sensors and controller

This is a layerwise model of a single-bead WAAM wall. It has one height and one
temperature per layer. It does not resolve a melt pool, a robot trajectory,
residual stress, or a temperature field along the wall.

The parameters are assumptions informed by the earlier literature review.
They have not been fitted to PIONEER thermocouples or validated against a cell.

## Deposition

For wire feed speed WFS and travel speed TS, both in mm/s:

- Wire area: A_wire = pi * (1.2 mm / 2)^2.
- Deposited area: A = eta * A_wire * WFS / TS, with eta = 0.98.
- Width: w = w_ref * (TS / 5 mm/s)^(-1/2) * [1 + a * max(T - 25 C, 0)].
- Layer increment: h = A / (c * w).

Nominal width w_ref is 8 mm, a = 0.0023 per C, and c = 2/3. The area relation
comes from mass conservation. The width law, cap shape and coefficients are
modelling assumptions. Standoff labels an arc regime but does not change
deposited mass or heat in this implementation.

## Cooling

After depositing a layer, H is the new wall height in mm:

- tau(H) = 30 s + (5 s/mm) * H.
- Temperature increment = 100 C / [1 + H / (15 mm)].
- Elapsed time = 150 mm / TS + dwell.
- T_next = 25 C + (T + increment - 25 C) * exp[-(elapsed / tau)^beta].

Beta is 1 for the main model. The variant uses 0.85. Cooling is applied over
one elapsed interval rather than restarting the stretched exponential at dwell.
These are lumped empirical equations, not a heat-transfer solution.

## Differences between builds

Each physical build draws independent uniform multipliers between 0.95 and 1.05
for width, width-temperature slope, base cooling time, height-dependent cooling
coefficient and heat increment. The draw stays fixed during that build.
The 5% ranges are sensitivity assumptions, not measured tolerances. An independent
random stream separates these draws from sensor noise and scanner dropout.

This variation prevents layer number and dwell from specifying a unique H/T
trajectory across all test builds. A learned model without sensor inputs is
still evaluated to measure how much the schedule and applied controls explain.

## One layer's timing

The EKF state is [H, S, T, b, H_previous], after deposition and before the next lift.
S = Z - H is nozzle-to-wall distance in mm; b is multiplicative pyrometer bias.

1. Apply the lift chosen after the previous layer. The first lift is zero.
2. Deposit at the applied travel speed; update H and cool over deposition plus dwell.
3. Read delayed scanner height H_previous, layer-end temperature and layer-end S.
4. Predict with the lift and speed actually applied, then update the filter.
5. Choose the next travel speed and lift from the new estimate.

The scanner delay is represented as one full layer, not a continuously modelled
3-6 s sensor offset. No between-scan trajectory is claimed. Applied and commanded
next-layer controls are stored separately in exported example trajectories.

## Sensors

| Channel | Measurement | Assumed errors |
|---|---|---|
| Scanner | Previous layer's H | sigma 0.03 mm; independent per-layer dropout |
| Pyrometer | b * T at layer end | sigma 5 C; b random walk sigma 0.005/layer |
| CTWD placeholder | 15 + (S-15) + q*(S-15)^2 | q=0.005/mm; sigma 0.2 mm; bias random walk sigma 0.003 mm/layer |

These magnitudes are assumptions. A Gaussian sigma of 0.2 mm is not a claim of
0.2 mm mean absolute error. CTWD denotes a synthetic standoff measurement; the
repository does not infer it from raw current/voltage waveforms. Each sensor has
its own random stream, so blocking a scan does not change pyrometer noise.

## Control and estimators

The target is a linear wall-growth trajectory, nominally 1.8 mm per layer.
After layer k, speed_next = clip(10 + gain * 2 * [H_est - H_target(k)], 5, 20)
in mm/s. A taller estimate raises travel speed and reduces deposited area.
Nozzle lift follows estimated layer growth, clipped to 0.5-3.5 mm.

The baseline adds 1.8 mm to the previous scan or estimate, and uses the latest
pyrometer and CTWD readings. The EKF uses nominal process parameters and a
linear CTWD measurement. It includes the thermal derivatives with respect to
both height and temperature, and uses a Joseph covariance update.

The reference EKF knows the nominal nonlinear CTWD curve and selected variant
settings. It does not know sampled build parameters or sensor drift, and is
not an optimal estimator or an error lower bound.

The learned estimator fits three gradient-boosted regressors to current and
previous sensor readings, a missing-scan indicator, layer number, dwell and
applied travel speed. The schedule-only version masks every sensor channel.
Both are trained on fixed-speed and EKF-piloted builds; evaluation under their
own controllers can introduce a policy distribution shift.
