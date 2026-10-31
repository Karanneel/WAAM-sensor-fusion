# Learning path

Study in this order. Each block lists what it is for, the stop that needs it, and free resources first. Items marked **(unverified)** were recalled during research and not opened; check them before citing.

---

## Before stop A (the core)

**1. State-space models and the Kalman filter.** Used for the multi-rate KF with a planted model error.
- R. Labbe, *Kalman and Bayesian Filters in Python*, chapters 1-8. Free, CC BY 4.0, notebooks on GitHub/Binder. Use filterpy only inside these notebooks; write your own filter for the project.
- Särkkä and Svensson, *Bayesian Filtering and Smoothing*, 2nd ed. 2023, EKF/UKF chapters. [Free personal-use PDF](https://users.aalto.fi/~ssarkka/pub/bfs_book_2023_online.pdf).

**2. Delayed and multi-rate measurements.** The scanner reports a layer late, offset behind the torch.
- Larsen et al., "Incorporation of time delayed measurements in a discrete-time Kalman filter", CDC 1998 ([DTU Orbit](https://orbit.dtu.dk/en/publications/incorporation-of-time-delayed-measurements-in-a-discrete-time-kal/)).
- Gopalakrishnan, Kaisare, Narasimhan, delayed and infrequent measurements in an EKF ([IITM](https://publications.iitm.ac.in/publication/incorporating-delayed-and-infrequent-measurements-in-extended)). Journal name **(unverified)**.

**3. Grouped validation and leakage.** You already have this from Off the Pace.
- scikit-learn docs: GroupKFold, LeaveOneGroupOut.
- Roberts et al., structured cross-validation, Ecography 2017 ([PDF](https://www.biometrie.uni-freiburg.de/mitarbeiter/dormann/roberts-et-al-2017-ecography.pdf)).

**4. Closed-loop evaluation.** Why accuracy and outcome differ; the core result's framing.
- Gevers, "Identification for Control", European Journal of Control 2005 ([PDF](https://perso.uclouvain.be/michel.gevers/PublisMig/P78.pdf)).
- Lambert et al., "Objective Mismatch in Model-based RL", L4DC 2020 ([PMLR](https://proceedings.mlr.press/v120/lambert20a.html)).
- Sammons, Gegel, Bristow, Landers, repetitive process control of AM, IEEE TCST 2019 ([link](https://scholarsmine.mst.edu/mec_aereng_facwork/4153)).

**5. The WAAM process you are simulating.**
- Bratzel et al. 2022, ML for CTWD from arc signals, TU Clausthal ([ThinkMind PDF](https://www.thinkmind.org/articles/adaptive_2022_2_30_50014.pdf)). Read first; it is the local anchor.
- Halder et al. 2024, interlayer temperature vs dwell ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11243745)).
- Teixeira et al. 2023 and Kozamernik et al. 2020, hot layers lower and wider (links in the research report).
- Marcotte, Mishra, Wen 2024, between-layer height correction ([arXiv 2412.04536](https://arxiv.org/html/2412.04536v1)).

## Before stop B

**6. Observability as a number, not yes/no.**
- Hermann and Krener 1977, nonlinear observability ([PDF](https://www.fs.isy.liu.se/Edu/Courses/ObserversPhD/CourseMaterial/Hermann_Krener_1977.pdf)).
- Himpe, emgr empirical Gramian framework ([arXiv 2209.03833](https://arxiv.org/abs/2209.03833)).
- Kazma and Taha, variational Gramian for sensor selection ([arXiv 2402.14711](https://www.arxiv.org/abs/2402.14711v4)).
- Krener and Ide, "Measures of unobservability", CDC 2009 **(venue unverified)**.

**7. Sensor value and Shapley.**
- Fryer, Strümke, Nguyen 2021, why Shapley is a poor selection rule ([arXiv 2102.10936](https://export.arxiv.org/abs/2102.10936)).
- Krause, Singh, Guestrin, JMLR 9 (2008) ([link](https://jmlr.org/papers/v9/krause08a.html)).
- Joshi and Boyd, sensor selection via convex optimisation, IEEE TSP 2009 ([link](https://stanford.edu/~boyd/papers/sensor_selection.html)).

## Later (parked items)

- Consistency tests (NEES/NIS): Bar-Shalom, Li, Kirubarajan, *Estimation with Applications to Tracking and Navigation*, Wiley 2001 (paid).
- Uncertainty for time series: Gibbs and Candès, adaptive conformal inference, NeurIPS 2021 ([arXiv](https://arxiv.org/abs/2106.00170)).
- Robustness benchmarks from driving: MultiCorrupt ([arXiv 2402.11677](https://arxiv.org/pdf/2402.11677v3)).
- Hybrid estimators: Revach et al., KalmanNet ([arXiv 2107.10043](https://arxiv.org/abs/2107.10043)).
- DoE and active learning: Loeppky, Sacks, Welch 2009; Settles 2009 ([PDF](https://research.cs.wisc.edu/techreports/2009/TR1648.pdf)).

The full resource list, grouped by question, is in [design/research-report.md](design/research-report.md), section "Add these resources".
