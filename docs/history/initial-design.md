# Sensor fusion and data prioritisation testbed: project plan

Oct 16, 2026 · @Karan Dutt Neelakantrao

A small simulated robot-DED process with known physics, used to answer method questions with evidence: which sensors to use, how to fuse them, what data to collect first, and how to choose a model under real constraints.

## The idea

The goal is to show method, not a trained model: how an engineer decides what to measure, how to combine signals, and what to prioritise when time, money and compute are limited.

Real datasets cannot answer these questions, because the true state of the process is never known. A simulation can: you choose the physics, so every design choice is scored against the truth.

- **Process:** a single-bead wall built layer by layer by a robot-held DED nozzle. Layer height depends on travel speed, and heat accumulates as the wall grows.
- **Sensors:** four simulated sensors, each with a realistic rate, delay, noise, failure mode and cost.
- **Method:** eight questions, each answered by a controlled experiment and recorded as a design decision with its evidence.
- **Transfer:** the framework is process-independent. The same steps apply to WAAM, LPBF monitoring, a welding cell, or sensor fusion in autonomous driving.

The deliverable is a short design report plus Python code. No hardware or downloads are needed. ROS 2 and a real-data check are optional final stages.

## At a glance

&#91;embedded content: sensing-to-decision loop · 6 stages, 8 questions\]

Read it left to right, then back along the bottom: each box is one stage of the loop, and its Q numbers say which questions test it.

## The simulated process and sensors

The hidden true state has two variables: the height of each layer, and the temperature of the part. Every sensor sees only part of that state, late or with error.

**Process model (kept simple on purpose):**

- Layer height per pass follows a power law in travel speed, with separate "cold" and "hot" fits. Published robotic WAAM work uses exactly this form.
- Part temperature rises with each layer and decays with interlayer time (a lumped heat balance).
- Faults to inject: standoff drift, heat build-up, a speed error, and random spatter events.

| Sensor | What it observes | Rate | Delay | Flaw | Relative cost |
| --- | --- | --- | --- | --- | --- |
| Laser line scanner | Layer height, directly | \~2 Hz | Measures behind the nozzle | Late; blocked by spatter | High |
| Coaxial camera | Melt-pool width (indirect) | 30 Hz | Low | Noisy; reading shifts with temperature | Medium |
| Pyrometer | Surface temperature | \~100 Hz | Low | Drifts over time; emissivity error | Medium |
| Microphone | Process stability (very indirect) | 44.1 kHz | Low | Weak link to the state; background noise | Low |

Rates follow common practice: the 30 Hz camera and 44.1 kHz microphone match a published robotic-DED monitoring setup. All numbers are parameters you can change, and changing them is part of the study.

## The eight methodology questions

Each question is answered in order, because each answer constrains the next. Requirements come before sensors, sensors before fusion, fusion before model choice.

| # | Question | Experiment | What is measured | What it shows |
| --- | --- | --- | --- | --- |
| 1 | What must the system know, how precisely, how fast? | Derive a time budget from scan speed and melt-pool size; set the height and temperature error the controller can tolerate | Decision deadline (ms); allowed estimation error | The hard constraint every later choice is judged against |
| 2 | Can these sensors recover the state at all? | Observability check for every sensor combination | Which states each combination can and cannot separate | e.g. camera alone confuses "too hot" with "too high"; camera plus pyrometer does not. First filter, before any ML |
| 3 | What is each sensor worth? | Ablation of all sensor subsets, plus a Shapley-style split of the gain | Error per subset vs its cost | The cheapest set that meets question 1, and where extra sensors stop paying |
| 4 | How should the signals be combined? | Same conditions, five fusion designs: Kalman filter, early, feature-level, late, cascade | Error, latency and compute per design, with mismatched rates and delays | When physics-based filtering beats ML and when it loses (usually: small data favours the filter; a wrong physics model favours ML) |
| 5 | What happens when a sensor fails? | Inject dropout, pyrometer drift and spatter-blinded camera frames | Error under each fault; whether the system knows it is degraded | Which designs degrade gracefully. This often decides the design more than accuracy does |
| 6 | Which experiments should be run first? | Random runs vs design of experiments vs active learning, each with the same run budget | Runs needed to reach the target error | How much real experimentation a good data strategy saves |
| 7 | Which model, and why? | Physics only, physics plus an ML correction (grey box), classical ML, small neural net; with learning curves | Accuracy, inference time, data needed, interpretability | A decision matrix that justifies the choice instead of defaulting to the largest model |
| 8 | Does better estimation give a better part? | Each estimator drives the same simple height controller | Final wall height error and its spread | Accuracy and outcome are different things; a slower or fragile estimator can build a worse part |

The validation rule across all eight: split train and test by build or layer, never by random time steps, because neighbouring samples are near-duplicates.

## Concepts to study first

Study them in this order; each one is used by a specific question above. The first four carry most of the project.

| Order | Concept | What it is | Used in question | Good starting resource |
| --- | --- | --- | --- | --- |
| 1 | State and observability | The hidden variables you care about, and whether a set of measurements can recover them | 1, 2 | Any control-engineering text, chapter on state-space models and observability |
| 2 | Kalman filter | A recursive estimator that fuses a physics model with noisy, delayed measurements at different rates | 4, 5 | R. Labbe, *Kalman and Bayesian Filters in Python* (free online book with notebooks) |
| 3 | Fusion levels | Where signals are combined: raw data (early), features (mid), decisions (late), or a state estimate | 4 | Survey papers on multisensor data fusion; the JDL fusion model as a vocabulary |
| 4 | Grouped validation and leakage | Why random splits inflate scores on time series and repeated builds | All | scikit-learn documentation on GroupKFold and time-series splits |
| 5 | Feature value and Shapley values | Fair credit for each input's contribution to performance | 3 | Introductory material on Shapley values and permutation importance |
| 6 | Sensor selection under a budget | Choosing the subset of sensors with the best information per cost | 3 | Krause and Guestrin's work on near-optimal sensor placement |
| 7 | Design of experiments and active learning | Choosing which experiments to run so each one teaches the most | 6 | B. Settles, *Active Learning Literature Survey*; an introduction to Bayesian optimisation |
| 8 | Grey-box modelling | A physics model with an ML term that learns only what the physics misses | 7 | Papers on physics-informed or hybrid models for process monitoring |
| 9 | Uncertainty estimation | Knowing how confident a prediction is, so the system can flag degradation | 5, 8 | Introductory material on prediction intervals and ensembles |
| 10 | Closed-loop evaluation | Scoring an estimator by the result it produces in control, not by its accuracy alone | 8 | Your control-engineering course material on feedback loops |

You already have a head start on 4 (the race-grouped validation in Off the Pace) and the autonomous-driving context helps with 2 and 3, since vehicle sensor fusion faces the same questions.

## Build plan

About 25-40 hours in total. Each stage ends in something usable, so the project can stop after any stage and still show a complete piece.

1. **Simulator and sensors (5-7 h).** Process model, fault injection, four sensor models with rate, delay, noise and cost. Output: a plot of true state against every sensor's view of it.
2. **Requirements and observability (3-4 h).** Questions 1 and 2. Output: the time budget, the error tolerance, and a table of which sensor combinations can see which states.
3. **Sensor value and fusion (6-8 h).** Questions 3 and 4. Output: error against cost for every sensor subset, and the five fusion designs compared. This stage alone is a solid portfolio piece.
4. **Robustness (3-4 h).** Question 5. Output: how each design behaves under dropout, drift and spatter.
5. **Data prioritisation and model choice (5-7 h).** Questions 6 and 7. Output: runs needed per data strategy, and the model decision matrix with learning curves.
6. **Closed-loop evaluation (3-4 h).** Question 8. Output: final wall height error per estimator.
7. **Optional: real-data check (4-6 h).** Repeat questions 3 and 4 on a public robotic-DED recording (coaxial camera plus microphone) to test whether the simulated conclusions hold on real signals.
8. **Optional: ROS 2 wrapper (8-10 h).** Each block becomes a node; replay the data through it and measure end-to-end latency against the question 1 budget.

The written output is a design report: one page per question, each with the decision, the evidence and the conditions under which it would change.

## Limits and open questions

The main limit: simulated conclusions are only as good as the simulated physics. The report therefore labels each finding as structural (holds for any process with these sensor properties) or model-dependent (could change with real physics).

- The process model is simplified. It reproduces trends such as heat build-up, not exact DED behaviour.
- Sensor flaws are modelled, not measured. The optional real-data stage tests the most important ones.
- Open: which fault matters most for your eventual thesis process, DED or WAAM? That sets which faults to model in most detail.
- Open: whether a TU Clausthal lab (ISAF or IMW) has a robotic deposition or welding cell whose data could replace the simulation later.

## Sources

- [Robotic wire arc additive manufacturing with variable height layers (arXiv 2412.04536)](https://arxiv.org/html/2412.04536v1): power-law bead height model with cold and hot fits, layer-height correction between layers.
- [Multimodal sensor fusion for real-time location-dependent defect detection in laser DED (arXiv 2305.13596)](https://www.arxiv.org/pdf/2305.13596): camera and microphone rates, feature-level fusion, per-sensor strengths.
- [Robotic laser DED with acoustic and coaxial camera monitoring, demo data (Zenodo 12604782)](https://zenodo.org/records/12604782): candidate dataset for the optional real-data check.
- [LDED-FusionNet multisensor dataset (Zenodo 15050300)](https://zenodo.org/records/15050300): the full dataset, access on request.
- [Multimodal sensor fusion for real-time standoff estimation in DED (ORNL)](https://impact.ornl.gov/en/publications/multimodal-sensor-fusion-for-real-time-standoff-estimation-in-dir/): camera plus microphone to estimate standoff height.
