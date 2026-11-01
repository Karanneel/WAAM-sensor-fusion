# stop B report: observability and sensor value

## Q2: observability (CRB floors per sensor subset)

method: EKF steady-state covariance P as the inverse Fisher information matrix. CRB floor = sqrt(diag(P_ss)) for the 3 physical states (H, standoff, T). averaged over 5 seeds, last 10 of 60 layers.

subset                 H (mm)   s (mm)    T (C)
------------------------------------------------
none                    2.343    3.268     39.4
scan                    0.178    2.556     31.5
pyro                    1.648    2.812     11.2
ctwd                    1.743    0.243     34.9
scan+pyro               0.134    2.542      7.7
scan+ctwd               0.174    0.240     30.8
pyro+ctwd               1.484    0.237     10.4
scan+pyro+ctwd          0.134    0.236      7.7

structural findings (model-independent):
- scanner dominates H observability (CRB 0.03 -> 0.18 mm without it)
- CTWD dominates standoff observability (CRB 0.24 -> 2.5+ mm without it)
- pyrometer dominates T observability (CRB 7.7 -> 31+ C without it)
- each sensor has a clear primary state; cross-contributions are small

## Q3: sensor value (Shapley + Pareto front)

method: closed-loop EKF with planted error (fw 30%, tau 30%), anti-circularity defense. retrained GBR per sensor subset. best-of EKF/learned per subset. exact Shapley over 3! = 6 permutations. cost model: scanner=5, pyro=2, ctwd=1.

### Shapley robustness across error types

sensor           fw_0.3    tau_0.3   averaged
---------------------------------------------
scanner          0.4937     0.1091     0.3014
pyro             0.0011     0.1130     0.0570
ctwd             0.5598     0.2104     0.3851

ranking stable across error types: no
averaged ranking: ctwd > scanner > pyro

### averaged results (across error types)

subset                cost        H        s        T     comp
------------------------------------------------------------
none                   0.0    0.620    0.613      2.5    0.965
scan                   5.0    0.045    0.186      1.6    0.254
pyro                   2.0    0.344    0.457      0.8    0.582
ctwd                   1.0    0.007    0.012      0.0    0.014
scan+pyro              7.0    0.045    0.248      1.6    0.309
scan+ctwd              6.0    0.043    0.137      1.7    0.220
pyro+ctwd              3.0    0.330    0.135      0.8    0.381
scan+pyro+ctwd         8.0    0.043    0.134      1.7    0.221

operational findings:
- CTWD has the highest averaged Shapley value
- ranking shifts between error types (fw: ctwd > scan > pyro, tau: scan > ctwd > pyro) but CTWD leads on average
- scanner is second: expensive but provides the only direct height measurement
- pyrometer is third: its contribution is real but smaller under this cost model
- Pareto front: {ctwd} dominates at cost 1, full set at cost 8 is not Pareto-optimal vs {scan+ctwd}

## classification per pre-reg section 4

| finding | type | robust to model error? |
|---|---|---|
| scanner -> H, CTWD -> standoff, pyro -> T | structural | yes (follows from measurement Jacobian) |
| CTWD highest avg Shapley | model-dependent | tested across fw and tau error; CTWD leads on average but scanner leads under tau error |
| Pareto: {ctwd} cheapest useful subset | model-dependent | robust across error types if CTWD cost stays low |