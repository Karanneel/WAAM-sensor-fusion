# Sensor selection

Each estimator is evaluated separately on 30 test builds per sensor subset and error type.
Learned models, including the no-sensor model, use the same 100 training builds (seeds 100-119 at five dwell settings).
No test errors are used to choose an estimator. Costs and error normalization are assumptions.
Training uses mixed fixed-speed and EKF-piloted trajectories. Evaluation uses each estimator in its own control loop; this is a policy distribution shift.

| Estimator | Sensors | Cost | H RMSE (mm) | S RMSE (mm) | T RMSE (C) | Composite |
|---|---|---:|---:|---:|---:|---:|
| EKF | ctwd | 1 | 0.734 | 0.156 | 4.21 | 0.908 |
| EKF | none | 0 | 0.953 | 0.953 | 3.17 | 1.433 |
| EKF | pyro | 2 | 0.947 | 0.947 | 4.88 | 1.465 |
| EKF | pyro+ctwd | 3 | 0.837 | 0.155 | 5.17 | 1.035 |
| EKF | scanner | 5 | 0.060 | 0.291 | 4.70 | 0.574 |
| EKF | scanner+ctwd | 6 | 0.057 | 0.145 | 5.20 | 0.548 |
| EKF | scanner+pyro | 7 | 0.064 | 0.466 | 8.07 | 0.945 |
| EKF | scanner+pyro+ctwd | 8 | 0.062 | 0.143 | 8.32 | 0.849 |
| learned | ctwd | 1 | 0.982 | 0.249 | 2.73 | 1.088 |
| learned | none | 0 | 0.856 | 1.495 | 2.16 | 1.763 |
| learned | pyro | 2 | 0.842 | 0.856 | 2.92 | 1.247 |
| learned | pyro+ctwd | 3 | 0.902 | 0.278 | 3.03 | 1.028 |
| learned | scanner | 5 | 0.292 | 0.494 | 2.27 | 0.665 |
| learned | scanner+ctwd | 6 | 0.325 | 0.163 | 2.22 | 0.464 |
| learned | scanner+pyro | 7 | 0.299 | 0.469 | 2.99 | 0.681 |
| learned | scanner+pyro+ctwd | 8 | 0.316 | 0.160 | 3.01 | 0.501 |

Composite error = sqrt((H/1 mm)^2 + (S/1 mm)^2 + (T/10 C)^2), calculated per build and then averaged.
The no-sensor learned baseline still receives layer number, dwell and applied travel speed. These are known controls, not sensor channels.
Costs: scanner 5, pyrometer 2, CTWD 1 relative units. Shapley utility is negative error and does not include cost.

## Rankings and tradeoffs

- EKF Pareto subsets: ctwd, none, scanner, scanner+ctwd.
- EKF, cooling_time: scanner > ctwd > pyro.
- EKF, ctwd_curve: scanner > ctwd > pyro.
- EKF, width_temperature: scanner > ctwd > pyro.
- learned Pareto subsets: ctwd, none, pyro+ctwd, scanner, scanner+ctwd.
- learned, cooling_time: scanner > ctwd > pyro.
- learned, ctwd_curve: scanner > ctwd > pyro.
- learned, width_temperature: scanner > ctwd > pyro.

These rankings apply to the tested generator, controls and scaling assumptions. They are not model-independent sensor recommendations.
Uncertainty for close subset rankings has not been estimated; the Pareto plot shows point estimates.
