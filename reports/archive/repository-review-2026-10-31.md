# Repository review, 2026-10-31

Reviewed repository: https://github.com/Karanneel/waam-sensor-fusion

Reviewed commit: `815c946096dc30fa2c6ed159ff4ad9eaa87d7fec`. GitHub's main-branch commit, retrieved through the GitHub connector, matches local HEAD. The working tree was clean before this report. Both commits reachable in local history were inspected. No source files, existing reports, figures, Git history, or remote content were changed.

## Assessment

The implementation produces reproducible numerical outputs, but several central scientific interpretations are unsupported. The most serious problem is that the controller cannot affect the scored wall-height outcome through the implemented physics. The advertised invariance is therefore built into the experiment. The sensor-value analysis also confounds sensing with memorisation of a deterministic build schedule and uses overlapping training/test builds.

Treat the repository as a prototype requiring corrections before presenting its headline conclusions as established findings. Removing generic wording alone would not resolve these problems.

Severity: P1 means a result or advertised workflow needs correction; P2 means a material methodological or documentation problem. These priorities concern the research claims, not production-service availability.

## Findings

### 1. P1: The controller has no causal path to final wall height

Locations: `src/process.py:57-64`, `src/harness.py:66-93`, `README.md:15`.

The controller changes only the nozzle Z increment. Area, width, bead height, and temperature depend on fixed wire feed, travel speed, thermal state, and generator parameters. Standoff only changes a regime label. That label does not change deposition, heating, or the random dropout probability. Therefore neither estimator choice nor controller gain can change H or T within a fixed generator/dwell setting.

Reproduction: three deliberately artificial estimators returned constant standoff estimates of 0, 15, and 100 mm. Their controller commands were respectively fixed at 3.5, 1.8, and 0.5 mm. Last-layer true standoffs were 64.941, 13.941, and -25.059 mm. All three produced final H = 56.814955040301 mm and wall error = 1.014955040301 mm.

The README explanation that the controller "absorbs estimator differences" is not established. Even impossible negative standoff does not affect the scored height. This is an experiment-design defect, not evidence that estimator quality generally does not matter for control.

Correction: retain this run as a diagnostic. For a revised experiment, use a physically justified actuator that affects height, such as travel speed, already present in the mass-conservation equations. Alternatively evaluate standoff regulation under the existing controller and narrow the research question accordingly. Freeze revised hypotheses before rerunning; do not tune a coupling to manufacture a crossover.

### 2. P1: Training/test builds overlap in both stages

Locations: `src/run_sweep.py:30-37`, `src/run_dropout_sweep.py:25-32`, `src/sweep.py:94`, `src/sensor_value.py:84,141,191`.

Stop A trains at dwell 60 with seeds 10-13, among other settings, and tests dwell 60 with seeds 0-29. Four test seeds overlap training. Stop B trains dwell 60 with seeds 0-7 and evaluates seeds 0-9: eight of ten overlap. This violates the stated split-by-build policy. The overlap exists at zero planted error, including exact pilot trajectories where the pilot and evaluated controller use the same EKF. Nonzero planted-error trajectories may differ, but reusing seeds/build settings still fails the stated independent validation design.

Correction: assign disjoint build IDs/seeds before data generation. Add held-out process conditions or generator parameters; new noise seeds alone do not establish physical generalisation.

### 3. P1: The learned model can recover height and temperature without sensors

Locations: `src/learned.py:26-36`, `src/simulator.py:60-80`, `src/sensor_value.py:80-112,239-243`.

Height and temperature are deterministic functions of dwell and layer index at fixed controls. Seeds change scanner dropout and measurement noise, not physical H/T trajectories. Dwell and layer index are learned-model features. Stop B trains every build at dwell 60, with identical H/T labels at each layer.

Reproduction using the existing subset-training functions, with an empty sensor set:

| Learned model inputs | H RMSE (mm) | T RMSE (C) | Standoff RMSE (mm) |
|---|---:|---:|---:|
| No sensor channels; build schedule remains | 0.00076155 | 0.00078320 | 0.235535 |
| CTWD only, existing Stop B result | 0.00076155 | 0.00078320 | 0.165755 |

The near-perfect H/T reconstruction is not evidence that CTWD supplies those quantities. The existing analysis omits a learned model for the empty subset, using only the perturbed EKF there, while allowing a learned model for every nonempty subset. Sensor utility therefore includes a change of estimator/model access.

Correction: include the same schedule-only learned baseline for the empty set. Introduce justified variation in physical builds, split those builds independently, and report performance on unseen conditions. Layer index is a legitimate feature, but its predictive contribution must be separated from sensor information.

### 4. P1: Sensor subset scores combine different estimators after inspecting test errors

Location: `src/sensor_value.py:245-250`.

Each state's score is the minimum test RMSE of EKF and learned. The resulting vector can combine H/T from one estimator with standoff from another, selected using ground-truth test errors. It is not necessarily the performance of any implemented estimator or preselected hybrid.

Correction: evaluate separate estimator-specific Pareto fronts, or select an estimator/hybrid using independent validation data and freeze that selection before testing. Label an after-the-fact componentwise minimum as an optimistic reference only.

### 5. P1: The current real-data probe returns NO-GO

Locations: `src/probe_pioneer.py:60-78,178-185`, `docs/decisions/pre-registration.md:22-31`.

Re-ran the current probe against the local PIONEER files with figure-writing replaced by no-op functions so existing evidence stayed unchanged. Only dwell 30 and 60 loaded a Robot_Layer series. Dwell 0, 90, 120, and 240 were skipped. G1 PASS, G2 FAIL, G3 PASS; return code 1, verdict NO-GO.

The current source requires hot/cold series at 0 and 240 for G2. The recorded GO instead cites three dwell series and a loosened 31 C peak-spread rule. The source has regressed relative to the later probe discussed earlier in this chat, which included a welding-current fallback and a different G2 rule.

Correction: identify the version that produced the claimed evidence. Record changed rules explicitly and retain the original-rule outcome. Do not silently label a revised gate an original pass.

### 6. P1: The sealed-check entry point crashes and does not reproduce the saved run set

Locations: `src/run_sealed_check.py:38,48,87`, `src/sweep.py:52-57`.

`run_sweep` now returns oracle rows as well as naive/EKF/learned. The overlay function has colors only for the original three, and `colors[name]` raises `KeyError: 'oracle'`. Reproduced by calling the overlay on the committed CSVs; no figure was saved.

The saved sealed CSV contains 2,160 rows and three estimators. The current generator would create 2,880 rows and four estimators, overwrite the CSV, and then fail while plotting. Thus the advertised end-to-end workflow is broken and the saved sealed result belongs to an earlier configuration.

Correction: define the intended sealed estimator set explicitly, fix plotting, and preserve the old result rather than overwriting it. Any corrected final evaluation needs a dated methodological addendum; the already inspected variant is no longer unseen.

### 7. P1: Prediction verdicts change the preregistered outcome metric

Location: `docs/decisions/pre-registration.md:14-17,73-76`.

P1 asks which estimator wins on final wall error; its verdict awards partial credit for H/standoff state RMSE instead. P2 asks about a wall-error crossover; its verdict awards partial credit for state-RMSE crossovers instead. P4 asks whether naive is within 10% on wall error; the verdict answers with standoff/T errors.

The saved wall errors tie exactly, so P1's strict KF win is not observed, P2's wall-error crossover is not observed, and naive is within 10% of the best in every tested cell. These answers are additionally limited by Finding 1. Ties do not demonstrate a reversed ordering.

Correction: score each prediction on its original metric. Put additional state-level observations in a separate analysis. The wording "all conditions" should distinguish main-generator error (1.014955 mm) from sealed-generator error (4.013109 mm).

### 8. P1: The recorded core-gate pass is not backed by its specified calculation

Locations: `docs/decisions/pre-registration.md:33-41,67`, `src/sweep.py:68-83`, `src/plot_crossover.py:18-29`.

The gate requires unmeasured-state/dropout-specific RMSE, means over builds, and a 95% interval excluding zero improvement. The saved CSV stores whole-build RMSE only. The plotting code bootstraps each estimator's median separately; it does not compute the paired improvement statistic or scanner-dropout-only errors. There is also no within-layer resolution for the promised "between scans" behaviour.

Even on the aggregate proxy, the claim that both EKF and learned beat naive on two eligible categories at low error is unsupported. At fw=0.15, gain=1, ratios of mean build RMSE give EKF improvements of H +56.46%, standoff +30.85%, T -12.80%. Whole-build H is explicitly excluded as the gate's substitute for dropout-specific scoring. Learned improves standoff +30.93% and T +41.48%, but its aggregate H error is much worse.

This does not prove the overall gate fails: one non-naive estimator might meet it. It means the specified pass has not been demonstrated, and "both" is too strong.

Correction: export per-layer observations, dropout flags and errors; implement the original masks and a paired build-level bootstrap for improvement. Report the pass/fail result without changing thresholds.

### 9. P2: The oracle is a model-informed EKF reference, not a proven achievable floor

Locations: `src/oracle.py:3-8,23-40`, `README.md:17`.

Correct model parameters do not make a nonlinear EKF statistically optimal. It shares the EKF's approximate Jacobian and assumed Q. It does not estimate the CTWD bias random walk. In a sealed run it still uses default process parameters, so its shape and thermal equations would not match sealed truth.

Saved zero-error medians: EKF standoff RMSE = 0.131706 mm, oracle = 0.153582 mm. They match closely on H (0.027927 vs 0.027920 mm), but not on standoff, and the ordinary EKF is better on that metric. This contradicts the README's combined H-and-standoff floor assertion.

Correction: rename it a reference EKF with the known CTWD map. Remove "achievable limit" and conclusions that a hybrid has nothing left to gain unless supported by a valid bound or stronger benchmark.

### 10. P2: EKF covariance is incorrectly labelled a Gramian, Fisher information, and CRB

Locations: `src/observability.py:44-71`, `reports/stopB/stopB_report.md:5`, `src/run_stopB.py:29-42`.

The code averages EKF P diagonals over the last ten layers and takes square roots. It does not compute the advertised noise-weighted empirical observability Gramian or a nonlinear posterior Cramer-Rao information recursion. A finite, changing wall-growth trajectory also does not establish steady state merely by selecting its last ten layers.

For nonlinear, mismatched filtering with arbitrary process covariance, P is the filter's uncertainty approximation, not automatically a rigorous error lower bound. See the original nonlinear filtering bound treatment: https://www.ese.wustl.edu/~nehorai/paper/ieeetsp98-1.pdf

Correction: label the current figure "EKF predicted standard deviation by sensor subset" and test consistency against empirical errors, or implement the actual information/observability calculation. Do not equate "structural" with "model-independent" based on these runs.

### 11. P2: Standoff measurements, state prediction, and control use different time indices

Locations: `src/harness.py:66-92`, `src/sensors.py:75`, `src/ekf.py:99,132-135`.

The row's standoff and CTWD observation are pre-deposition Z-H. The EKF first advances standoff using `s + r_z - h`, then assimilates that older CTWD value as a direct observation of the predicted standoff. The truth advances Z with the newly computed command, whereas the control dictionary given to the estimator contains the previous command. There is no single consistent pre/post-deposition state convention across these operations.

The harness also returns `final_standoff = H - prev_H`, always zero because both variables have just been assigned H_out. `last_standoff` refers to the beginning of the last layer, not the final post-update geometry.

Correction: document the state/measurement timeline, align each measurement with that state, and pass the command actually applied during the corresponding transition. Compute final standoff from the final Z and H under that convention.

### 12. P2: Planted-error axes have different meanings and README labels are wrong

Locations: `src/sweep.py:27-50`, `README.md:27`.

`fw` changes the EKF's width-temperature slope, not wire-feed slope. `tau` changes only the EKF's base cooling time, not the generator or its height-dependent term. `ctwd` changes the true sensor's quadratic coefficient, not the documented map bias. The first two primarily handicap the EKF; the third changes observations for everyone. Equal percentage levels are not equivalent model-error severities.

Correction: document the exact quantity, side of the experiment, and units for each perturbation. Separate estimator-model mismatch from sensor-domain shift. Interpret learned-model wins in the context of that asymmetry.

### 13. P2: The calibration claim has no auditable calibration record

Locations: `README.md:9,34`, `docs/design/process-and-sensor-model.md:3,55,98-104`, process/simulator constants.

The README says calibrated against PIONEER. The process document still calls parameters starting values to be calibrated and leaves the calibration checklist unchecked. The tracked source contains fixed constants and a probe, but no calibration fit, fitted-parameter output, calibration loss, residual comparison, or independent validation record. Manual calibration may have occurred; this repository does not substantiate it.

The probe calculates per-layer peak thermocouple readings, not temperatures immediately before the next deposition. Those cannot silently be used as the same thermal target.

Correction: supply the actual calibration procedure, chosen walls/channels, fitted parameters, measured-versus-predicted curves, and scope of the fit. Until then use "parameters informed by published trends and exploratory PIONEER analysis" only if that accurately describes what was done.

### 14. P2: Stop 0 height extraction and gates do not establish the claimed quantity

Locations: `src/probe_pioneer.py:92-110,190-226`, preregistration Stop 0.

The extractor subtracts the minimum of the top-edge profile, not an independently established substrate datum. Its derived height can depend on wall ends, substrate inclusion, and scan cropping. It uses two walls while the recorded original rule requires at least three. A final top-edge profile does not recover each deposited layer's measured height.

Correction: establish scan orientation and substrate datum, inspect the selected region, evaluate the required wall count, and distinguish final-wall geometry from layer-by-layer height truth.

### 15. P2: Sealed winner agreement is based on arbitrary tie-breaking

Location: `src/run_sealed_check.py:67-74`.

The main and sealed wall-error values are exactly tied across estimators in every cell. `idxmin` nevertheless assigns one estimator as the winner. Matching this arbitrary winner in 24/24 cells is not evidence of a stable ranking. The genuine numerical observation is tied wall errors within each generator, for the reason in Finding 1.

Correction: detect ties with a preregistered tolerance and compare tied sets or paired differences. Keep tied outcomes distinct from rank reversals.

### 16. P2: Generated Stop B prose contradicts the tables and figure

Locations: `src/run_stopB.py:39-42,91-108`, `reports/stopB/stopB_report.md:19,57`.

Several conclusions are literal strings rather than derived from the numerical result. "Scanner dominates H ... 0.03 -> 0.18 mm without it" disagrees with the table: all sensors give 0.134 mm predicted H uncertainty; removing the scanner gives 1.484 mm for pyro+ctwd. The averaged Pareto front recomputed from the stored method is {none, ctwd}. Both scan+ctwd and the full set are dominated by ctwd alone; full set has lower averaged error than scan+ctwd, so scan+ctwd does not dominate it as the prose says. The plotted front itself correctly marks none and ctwd.

Shapley values are calculated from error utility without costs. The prose attributing their ranking to "this cost model" confuses the Shapley analysis with the separate cost/Pareto calculation.

Correction: derive comparisons and dominance statements from the arrays, or write a clearly reviewed static discussion after generating tables. Use Markdown tables or fenced text; current space-aligned tables are ordinary prose on GitHub and lose their intended layout.

## Git, public presentation, and writing

- Two commits are visible, both authored/committed on October 31. They do not independently establish that the October 26 prediction freeze preceded estimator tuning. This is a provenance limitation, not evidence that the stated date is false. Preserve any genuine earlier dated record; do not manufacture earlier history.
- The latest commit edits prediction wording above a freeze rule that says it cannot change. The punctuation change is minor, but a dated editorial note would respect that rule better than silently editing frozen text.
- No explicit Claude/ChatGPT/OpenAI/Anthropic names or Co-authored-by trailers were found in the text files of either reachable commit. A limited signature scan found no matching GitHub/OpenAI-style tokens or private-key headers. This is not an exhaustive credential/security audit.
- Ignored council transcripts and research notes are not in the two inspected commits. However, tracked prose still says "council finding" in the process model. The public Git ignore file names the excluded internal records; filenames alone do not establish AI authorship.
- The second commit explicitly discusses fixing em-dashes and public-release cleanup. This is editorial history, not proof of AI authorship. Punctuation, lowercase comments, lists, and tidy formatting are not reliable authorship tests.
- Phrases most worth revising are "the famous ... headline", "Three honest-check findings", "anti-circularity defense", "linear strawman", "apples to apples", and broad "structural"/"achievable floor" verdicts. They are distracting or overconfident relative to the evidence, regardless of who wrote them.
- "There is no open testbed" and "No prior work was found applying this method to WAAM" need a dated, scoped search record. Two methodology references were checked directly: MultiCorrupt https://arxiv.org/abs/2402.11677 and KalmanNet https://arxiv.org/abs/2107.10043 are genuine and relevant as inspirations, but do not establish WAAM novelty.
- The main generic wording problem is causal confidence without supporting checks: the controller allegedly "absorbs" differences, the EKF allegedly reaches an "achievable limit", and the learned model allegedly "extrapolates into divergence". The dropout error gap is real in the sampled reproduction; its mechanism needs an ablation. The implemented learned model uses current/previous observations rather than recursively feeding back its predicted H. A physical controller-driven H divergence is impossible in this generator.
- Suitable independent writing samples were not returned by two writing-style searches. Chat messages establish a preference for direct explanations, but are insufficient to authenticate an academic/repository voice. No claim that this review has established a precise personal style match is made.
- Broken public links: `docs/learning-path.md` links to excluded `design/research-report.md`; `docs/decisions/decisions-log.md` links to the same excluded report. Directory links in docs/README are valid and were not counted as broken files.
- There is no tracked license, automated regression test suite, or pinned dependency/environment record. The smoke scripts generate plots but do not provide an assertion-based check for the central invariants. The dependency list includes unused pykalman and python-control; these are unnecessary installation requirements for the inspected source. The ignored raw data needs download/extraction instructions to make Stop 0 reproducible on another machine.

For public writing, prefer short descriptions of what was measured, the exact condition, and what remains untested. Keep genuine assistance disclosures where appropriate; do not replace them with unsupported claims of unaided work. Technical evidence matters more than disguising stylistic cues.

## Verification performed and limits

- Inspected all tracked Python modules, documentation and report text; parsed every Python module successfully using AST.
- Retrieved GitHub main commit and verified its SHA matches local HEAD. A separate shell git network check failed; remote verification came from the GitHub connector, not that shell command.
- Audited all 7,920 stored sweep rows: 2,880 main, 2,880 dropout, 2,160 sealed. No missing values or exact duplicate rows were found. Main and dropout each contain exactly one wall-error value; sealed contains exactly one different wall-error value.
- Retrained the main learned models and reproduced 24 sampled zero-error build/estimator/dropout cases (seeds 0, 10, 29; four estimators; nominal and 20% dropout). H and T RMSE matched stored values to six decimal places. This supports the numerical provenance of those cases, not every scientific claim.
- Reproduced the fixed-estimator control disconnection, the sealed plotting KeyError, the current probe NO-GO, and the no-sensor learned baseline without replacing existing artifacts.
- Recomputed all eight Stop B covariance rows and both sensor-value configurations, including Shapley values. Values match the reported method. Shapley efficiency held: sum = 0.8375188429384661 versus utility difference 0.8375188429384662.
- Visually inspected the Pareto/Shapley figure. The plot's marked Pareto points are consistent with its calculation; the accompanying prose is not.
- Did not rerun or retune the sealed generator, overwrite original experiment outputs, install dependencies, publish changes, or rewrite Git history. Did not reverify every historical literature claim or perform an exhaustive new novelty search. All scientific conclusions remain simulation-specific.

## Recommended order of correction

1. Correct the headline interpretation and prediction scorecard; preserve the existing artifacts as the original prototype result.
2. Define a consistent state/measurement/control timeline and an actuator-to-outcome path that answers the chosen research question.
3. Separate physical builds and training/test partitions, and include the schedule-only learned baseline.
4. Rebuild sensor-value comparisons without test-selected componentwise minima, and label uncertainty estimates accurately.
5. Implement the exact preregistered gate or transparently document a new prospective protocol. Record the already inspected sealed variant as inspected, with any subsequent validation clearly dated.
6. Repair the probe and plotting entry points, document calibration evidence, regenerate reports from the corrected experiment, and then revise public prose to match the evidence.
