# Docs

The engineering record behind Simulation Field: what was decided, why, and what was tried and dropped.

## Reading order

1. **[decisions/pre-registration.md](decisions/pre-registration.md)**: predictions and gates, written before code. Frozen 2026-10-26.
2. **[design/process-and-sensor-model.md](design/process-and-sensor-model.md)**: equations, parameters, sensor models and the calibration checklist.
3. **[learning-path.md](learning-path.md)**: what to study, in order, mapped to the stops.
4. **[future-work.md](future-work.md)**: wire-laser DED, powder DED, parked method items, ROS 2.
5. **[decisions/](decisions/)**: supporting records.
   - [decisions-log.md](decisions/decisions-log.md): dated decisions.
   - [source-corrections.md](decisions/source-corrections.md): what v0.1 cited wrongly and the fixes.
6. **[design/](design/)**: design history.
   - [original-plan-v0.1.md](design/original-plan-v0.1.md): the first plan, kept as written.
   - [process-and-sensor-model.md](design/process-and-sensor-model.md): equations and sources.

## Superseded by later decisions

The v0.1 plan predates the process decision. Main changes since:

- Process is **WAAM first**, then wire-laser DED, then powder DED, behind one process-module interface.
- The **core question is Q8**: does estimator accuracy ranking predict final wall error under a fixed controller and planted model error?
- **Microphone dropped**; coaxial camera parked for the DED modules; **placeholder CTWD channel** from arc signals added.
- **Q6 cut**; Q4 and Q7 merged into the core; Q2 and Q3 moved to stop B; most of Q5 parked.
- The real-data stage moves to the start (stop 0, PIONEER probe). Zenodo 12604782 is no longer the check.
- Camera rate in the cited paper is **10 Hz**, not 30 Hz.
