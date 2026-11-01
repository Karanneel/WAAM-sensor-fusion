# Source corrections to the v0.1 plan

Every source cited in v0.1 exists and is relevant. The errors are in specific numbers and scope. Items marked **checked** were confirmed directly against the original source on 2026-10-17.

| v0.1 claim | Verdict | Correction | Source |
|---|---|---|---|
| Coaxial camera at 30 Hz "matches a published robotic-DED monitoring setup" | **Wrong number (checked)** | The paper used a CCD camera at **10 Hz** and a microphone at 44.1 kHz. The 30 Hz figure comes from the group's Zenodo demo dataset, not the paper | [arXiv 2305.13596](https://arxiv.org/pdf/2305.13596), [Zenodo 12604782](https://zenodo.org/records/12604782) |
| The same paper as a fusion reference | **Partly** | It uses a stratified **random** 8:2 split, the leakage the plan's own validation rule forbids, so its 98.5% fused accuracy is likely optimistic. Cite it as an example of the pitfall | arXiv 2305.13596 (checked) |
| "Published robotic WAAM work uses exactly this form" (power law, cold/hot fits) | **Overstated** | One lab (RPI, Wen group), aluminium WAAM. Height was measured with an IR camera on a second robot, not a laser scanner. The paper has no temperature state; blending the two fits by temperature is the plan's own assumption | [arXiv 2412.04536](https://arxiv.org/html/2412.04536v1) |
| Cold fit a = −0.4619, b = 1.647; hot fit a = −0.3700, b = 1.215 | Verified | Values as stated (ln-space). No units given and no R² reported | arXiv 2412.04536 |
| Zenodo 12604782 as the real-data check | **Scope wrong** | One wall, no height or temperature ground truth, so it supports only camera-vs-microphone defect classification, and a single build makes a grouped split impossible | Zenodo record |
| Zenodo 15050300 is "the full dataset, access on request" | **Partly** | Access on request is correct. "Full" is an inference; the record does not say so. About 448 GB | Zenodo record |
| ORNL standoff estimation paper | Verified | Herberger et al., Additive Manufacturing 97 (2025) 104598. Camera + microphone, NN predicts standoff in LP-DED. No public data found | ORNL |
| Laser line scanner ~2 Hz | **No source** | Hardware runs 1-16 kHz profiles. "2 Hz" only makes sense as one scan per layer. The real flaw is the offset behind the nozzle (delay ≈ 3-6 s) | Keyence LJ-X8000, Micro-Epsilon specs |
| Pyrometer ~100 Hz | **No source** | Real range is 2.5 Hz (imaging two-colour) to 1 ms response (spot) | Smoqi et al.; Optris CTratio |
| Sensor cost ranking | **No source** | Keep as an explicit ASSUMPTION in the report | |
| "Krause and Guestrin's work on near-optimal sensor placement" | **Incomplete** | Krause, **Singh**, Guestrin, "Near-Optimal Sensor Placements in Gaussian Processes", JMLR 9 (2008) 235-284 | [JMLR](https://jmlr.org/papers/v9/krause08a.html) |
| JDL model as the vocabulary for early/feature/late fusion | **Wrong reference** | JDL levels describe what fusion does, not where signals combine. Use Dasarathy 1997 for data/feature/decision levels (volume and pages unverified) | Steinberg et al., ISIF 2023 |
| Labbe, *Kalman and Bayesian Filters in Python* | Verified | Free, CC BY 4.0 text, MIT code. Its companion library filterpy has had no release since 2018 | GitHub |
| Settles, *Active Learning Literature Survey* | Verified | CS Tech Report 1648, UW-Madison, 2009 | [PDF](https://research.cs.wisc.edu/techreports/2009/TR1648.pdf) |
| "Camera alone confuses too hot with too high" (Q2 example) | **Reframe** | The real camera-alone ambiguity is temperature vs **standoff**. Preheat lengthens the pool far more than it widens it | Halder et al. 2024 |
