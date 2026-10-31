# Decisions and discussion log

Dated, newest at the bottom. Each entry records the decision, why it was made, and what it replaced. Where this log and the master doc disagree, the master doc wins.

---

## 2026-10-16: v0.1 plan

- Simulated robotic laser DED single-bead wall; hidden state is layer height + part temperature.
- Four sensors: laser line scanner (~2 Hz), coaxial camera (30 Hz), pyrometer (~100 Hz), microphone (44.1 kHz).
- Eight method questions; design report + Python; optional real-data check and ROS 2 wrapper.
- Framing: method, not a trained model. Simulation chosen because real data never reveals the true state.
- Kept as written: [../design/original-plan-v0.1.md](../design/original-plan-v0.1.md).

## 2026-10-17: Deep research and source cross-check

- Five research streams. All five cited sources exist; errors are in numbers and scope. See [source-corrections.md](source-corrections.md).
- Main physics changes adopted:
  - mass conservation for bead area;
  - standoff modelled as a state;
  - thermal time constant that grows with wall height, plus along-layer variation;
  - sensor rates taken from hardware.
- Main method changes adopted:
  - Q1 and Q8 are split into two control loops.
  - Q2 uses a noise-weighted Gramian instead of a rank test.
  - Q3 selects from a Pareto front, with Shapley used only to explain.
  - Q7 gets a planted model error.
- Full synthesis: [../design/research-report.md](../design/research-report.md).

## 2026-10-17: Scope decision

- Adopted:
  - Make it a WAAM wall study with one core question: does state-accuracy ranking predict final wall error under a fixed controller and planted estimator error?
  - Drop the microphone and add a placeholder CTWD channel.
  - Q4 and Q7 merge into the Q8 core; Q2 and Q3 become stop B; Q6 is cut; NIS gating, dropout and ROS 2 are parked.
  - Pre-registered gates on unmeasured states.
- Replaced: the 10 Hz/30 Hz camera citation and the Zenodo 12604782 real-data stage.

## 2026-10-17: Process order and module interface

- **Decision:** build WAAM first. Wire-laser DED follows once WAAM is complete, then powder DED.
- **Why WAAM first:**
  - mass conservation pins bead area;
  - it fits CZM/ISAF and Bratzel 2022;
  - open WAAM data exists;
  - arc current/voltage is a near-free sensor.
- **Why wire-laser DED next:** it keeps wire mass conservation (no catchment curve to invent) and adds a laser heat source. TUM iwb works on it (Bernauer 2024).
- **Why powder DED last:** the catchment-vs-standoff curve must be swept as an uncertain parameter from day one, because its shape decides the scanner's value.
- **Design rule:** one process-module interface (inputs: heat input, wire feed, travel speed, standoff, temperature; outputs: area, width, height, heat in, regime flag). Estimators, controller and validation never change when the source is swapped.
- **Structural label extended:** a conclusion is structural only if it also holds on WAAM and at least one DED variant (once those exist).

## 2026-10-18: Stop 0 PIONEER probe passed

- G1 (per-layer height recoverable): PASS. 42 mm hot wall vs 64 mm cold wall from the same 31 layers.
- G2 (interlayer temperature across dwells): PASS on the loosened criterion. 3 of 6 walls loaded (30, 60, 240 s); 31 °C spread.
- G3 (files load in Python): PASS.
- Verdict: GO.
- Resolves D3 to "real data as primary truth, as a follow-on". Stop A still runs the simulator first.
- See `reports/stop0/` for the two probe figures.

## 2026-10-26: Pre-registration frozen

- P1-P5 predictions written down. Sealed-variant locked in (cooling exponent change + shape factor 3/4 + CTWD bias).
- Freeze line dated by Karan.
- See [pre-registration.md](pre-registration.md).

## 2026-10-31: Stop A complete

Verdict: PASS on the pre-registered core gate.

**Three structural findings (survive sealed check, oracle, dropout):**
1. Final wall error is estimator-invariant under the fixed controller at this operating point. Oracle = EKF = learned = naive at 1.015 mm.
2. EKF matches oracle at zero error on H and standoff. Physics-based fusion is at the achievable floor; a hybrid KF+NN has nothing left to gain in the quiet regime.
3. Learned model catastrophically fails under 20% scanner dropout (6.8 mm H RMSE vs EKF 0.028 mm, factor 240×). Model-based fusion wins when direct sensors are unreliable.

**Model-dependent findings (fail sealed check):**
- Specific state-RMSE rankings on the main generator (EKF wins H and standoff; learned wins T) do not transfer. On the sealed generator, naive wins H and T; learned wins standoff.
- The famous "EKF collapses on T under fw error" headline is a main-generator artefact and must be labelled model-dependent.

**Pre-reg prediction score:**
- P1: half (EKF wins 2 of 3 states, not all)
- P2: half (crossover exists on T under fw at any level, not just mid)
- P3: confirmed strongly (wall-err identical, state rankings vary)
- P4: wrong (naive never within 10% on standoff or T)
- P5: wrong (H benefits most from fusion, not standoff)

**Deliverables:**
- 15 Python files, 1758 lines total.
- 10 crossover figures (main + dropout + sealed overlays).
- 3 sweep CSVs totalling ~8000 rows.
- README written and in-place.

**Next action:** stop B (observability Gramian + sensor value Pareto) OR ISAF outreach. Decided outside this log.
