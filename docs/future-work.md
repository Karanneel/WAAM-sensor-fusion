# Future work

Everything deliberately left out of the WAAM core, with the reason and what it would take. Order matters: the process extensions come first.

---

## 1. Wire-laser DED module (next, after the WAAM version is complete)

Same wire mass conservation, laser heat source. Swap the process module; estimators, controller and validation stay unchanged.

| Change | Effect on the simulator |
|---|---|
| Heat and wire feed become independent controls | Laser power is a real fast actuator for a melt-pool loop; travel speed or wire feed drives height. The two-loop structure becomes natural |
| Arc current/voltage disappears | Replace with wire-to-workpiece electrical resistance (Chalmers: Hagqvist, Heralić, [resistance measurements for control of LMwD](https://research.chalmers.se/en/publication/192753); [resistance-based ILC](https://research.chalmers.se/en/publication/236108)). Needs a measurement circuit, so not free |
| Standoff becomes regimes | Wire tip must enter the pool: stable / dripping (too far) / stubbing (too close). Height error also defocuses the laser spot |
| Width set mainly by spot size | Temperature-driven height/width split matters less |
| Laser absorptivity uncertain | Add as a swept parameter |
| Spatter mostly gone | Replace the spatter fault with dripping events |
| Wire feed direction | Front vs back feeding flips each layer on a back-and-forth wall; possible alternating-layer bias (size unverified) |
| Coaxial camera returns | Melt-pool width and length features (preheat lengthens the pool far more than it widens it) |

- **Data:** no open wire-laser wall dataset was found.
- **Groups:** TUM iwb (Bernauer et al. 2024, RCIM 86 102683, layer-height control in wire-laser DED), Chalmers/University West, Fraunhofer ILT.

## 2. Powder DED module (after wire-laser)

- **Catchment efficiency vs standoff** must be swept as an uncertain curve from day one. No measured curve for a specific nozzle was found. Its slope decides whether height self-corrects (Donadello et al. 2018, 2021), and therefore how much a height sensor is worth.
- Height self-stabilises only near the operating point: error decays when 0 < ∂h/∂S < 2 (inference from Donadello's condition).
- Laser DED geometry laws differ from wire: height ∝ F/V, width ∝ P/V^0.5 (Bax); P·F^0.7/V for height in Inconel 718 (Bian 2024).
- Microphone and coaxial camera become natural sensors again. Real data: Chen LDED audio-visual (Zenodo 12604782) for classification only; NSF/TAMU DED challenge (Zenodo 21285367) has measured height maps for single tracks.

## 3. Parked method items

| Item | Why parked | Revisit when |
|---|---|---|
| Fast in-layer loop (melt-pool / temperature on power) | Out of scope for the core study | The wire-laser module adds laser power as an actuator (decision D4) |
| Q5 robustness extras: NIS chi-square gating, dropout training, one unseen fault type | Core gate only needs the drift state | After stop B |
| Q6 random vs DoE vs active learning | In a self-written simulator it measures only the smoothness of an invented surface | Real data with a run budget exists (ISAF cell). Known gap: no AM study compares active learning to a proper space-filling DoE at equal budget |
| KalmanNet-style hybrid estimator | Optional in stop A | Stop A finishes under budget |
| Real-data arc vs IR study, leave-one-dwell-out on PIONEER | Depends on stop 0 | Stop 0 returns GO (decision D3) |

## 4. ROS 2 wrapper

- Each block becomes a node; replay data through it and measure end-to-end latency against the Q1 deadline.
- ORNL WAAM data was captured as ROS bags (released as HDF5); `rosbags` reads and writes bags without ROS.
- `robot_localization` is a multi-rate EKF reference, not a direct fit for a height state.

## 5. ISAF data replacing the placeholder

- Logged Fronius CMT current/voltage plus laser-triangulation height from an ISAF cell would replace the placeholder CTWD channel and give a real "you are here" point on every crossover plot.
- Depends on the ISAF contact (decision D2).
