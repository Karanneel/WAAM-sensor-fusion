# Process and sensor model (WAAM version)

The physics behind the generator, with sources. The parameters are starting values to be calibrated in stop A, not final numbers. Claims are labelled FACT (sourced), ESTIMATE (reasoned) or ASSUMPTION (taken as given).

---

## 1. Process-module interface

Every heat source (WAAM now, wire-laser DED and powder DED later) implements the same module.

| Direction | Quantity | Unit |
|---|---|---|
| In | Heat input (arc power or laser power) | W |
| In | Wire feed speed WFS | mm/s |
| In | Travel speed TS | mm/s |
| In | Standoff S (CTWD for WAAM) | mm |
| In | Part temperature at the deposit, T | °C |
| Out | Bead area A | mm² |
| Out | Bead width w and height h | mm |
| Out | Heat into the part Q_in | J per layer segment |
| Out | Regime flag | stable / unstable / fault |

Estimators, the controller and the experiment harness only see this interface and the sensor outputs.

## 2. Geometry: mass conservation first

- **Bead area (FACT, wire processes):** A_k = η · A_wire · WFS / TS, with η ≈ 0.95-1 for wire. Teixeira et al. 2023 check: about 26 mm² predicted against about 25.5 mm² measured.
- **Width:** w_k = w_0 · (TS/TS_0)^−0.5 · f_w(T_k). Hot layers come out wider (FACT: Teixeira 2023, Kozamernik et al. 2020). The form of f_w is an ESTIMATE, calibrated to those trends.
- **Height:** h_k = A_k / (c_shape · w_k), with c_shape ≈ 2/3 for a parabolic cap (ESTIMATE). Hot layers come out lower.
- **Consistency check:** area ∝ TS^−1 and width ∝ TS^−0.5 give height ∝ TS^−0.5. The RPI power-law exponents (−0.46 cold, −0.37 hot; Marcotte et al. 2024, arXiv 2412.04536) fall in that range. Use them as a check, not as the model. That paper is one lab, aluminium WAAM, and height was measured with an IR camera, not a scanner.

## 3. Standoff as a state

- H_{k+1} = H_k + h_k and Z_{k+1} = Z_k + r_z, where r_z is the commanded Z increment. Then S_k = Z_k − H_k.
- **Wire processes have no mass-based self-correction (FACT):** deposited volume is fixed by wire feed, so a mismatch between h_k and r_z integrates into standoff drift.
- **WAAM consequence (FACT):** larger CTWD lowers mean current and causes arc instability and spatter. Oueslati et al. 2024 saw instability at 33 mm CTWD against 20 mm nominal.
- **Model:** instability / spatter probability rising with |S − S_0| beyond a threshold, which feeds the regime flag and adds scanner dropouts. The threshold shape is an ASSUMPTION, swept.
- **Without a CTWD signal (ESTIMATE):** standoff error between scans grows roughly as √k · σ_h.

## 4. Thermal model

- **Lumped interlayer balance (ESTIMATE, not a published law):**
  T_{k+1} = T_amb + (T_k + ΔT_layer − T_amb) · exp(−t_dwell / τ_k), with τ_k growing with wall height (roughly H²/α).
- **Calibration targets (FACT, Halder et al. 2024, laser hot-wire Ti-6Al-4V, 15 layers):**

| Dwell | Interlayer temperature, layer 1 → 15 |
|---|---|
| none | 214.6 → 660.4 °C |
| 120 s | 225.6 → 314.4 °C |
| 300 s | 242.3 → 263.1 °C |

- **WAAM reference (FACT):** interlayer temperature passed 200 °C after about 6 layers at 36 s dwell (Kozamernik 2020).
- **Along-layer variation (FACT):** up to about 200 °C along one WAAM layer (Teixeira 2023); the middle runs hotter than the ends. Model at least 3 segments per layer. A single scalar temperature makes the pyrometer look better than it is.
- **Free edges:** wall ends run deeper melt pools and slump (Aggarangsi et al. 2003). Model as an end-segment multiplier.
- **On a stop-0 "go":** calibrate against PIONEER thermocouples at its five dwell times instead.

## 5. Faults, injected as causes

| Fault | Injection | What emerges |
|---|---|---|
| Z-increment mismatch | r_z ≠ mean h | Standoff drift, then instability |
| Travel speed error | TS bias or noise | Area and height error |
| Heat build-up | Short dwell | Lower, wider layers; drift in f_w |
| Pyrometer drift | Random-walk bias | Wrong temperature estimate if not modelled |
| Arc instability | Regime flag from |ΔS| | Spatter, scanner dropouts |

Standoff drift is never injected directly. It emerges from the causes.

## 6. Sensor models

| Sensor | Default | Flaws | Source |
|---|---|---|---|
| Laser line scanner | One profile per layer (hardware runs at 1-16 kHz; per-layer mode is a choice) | Mounted 20-50 mm behind the torch: delay = offset ÷ TS ≈ 3-6 s. σ 10-50 µm. Spatter dropouts | Keyence LJ-X8000, Micro-Epsilon scanCONTROL specs; RPI WAAM used about 100 Hz |
| Pyrometer | 50-1000 Hz | Multiplicative emissivity bias; random-walk drift; spot averaging over a 3-6 mm wall; upper mounting about 17% off at 120 °C | Jorge et al. 2022; Schwarzkopf et al. 2023; Optris CTratio |
| CTWD from arc current/voltage | About 10 Hz feature from 10-50 kHz raw | **Placeholder.** Noise matched to 0.18-0.29 mm MAE; mapping mode-dependent and biased, nonlinear | Bratzel et al. 2022 (LSTM, Fronius CMT, KUKA); Hölscher et al. 2022 (±1.2 mm from short-circuit resistance) |

**Why the CTWD map is biased and nonlinear (council finding):** a clean linear law I ≈ I0 − κ(S − S0) makes the cheap sensor rank first by construction. Bratzel's model generalised only within one welding mode, and ISAF's Fronius CMT encodes CTWD in waveform shape and timing, not a simple current level.

**Dropped:** microphone. **Parked for the wire-laser DED module:** coaxial camera (width and length features; preheat lengthens the pool far more than it widens it, Halder 2024: length 15.3 → 30.6 mm, width 10.2 → 11.7 mm).

## 7. Controller

- Fixed layer-to-layer controller, the same for all estimators.
- Actuator: travel speed for the next layer (or the next Z increment), bounded and rate-limited.
- Two gains are tested (low, high).
- The fast in-layer loop is parked (open decision D4).
- Reference: Sammons, Gegel, Bristow, Landers 2019 (repetitive process control); Marcotte et al. 2024 (between-layer speed re-planning).

## 8. Planted model error (the anti-circularity knob)

Three error types, each swept over 3-4 levels from zero to large:
1. Wrong width-temperature function f_w (the estimator's thermal coupling is off).
2. Wrong thermal time constant τ.
3. Wrong CTWD map (gain and bias off).

The generator always uses the true values. Estimators use the perturbed ones.

## 9. Calibration checklist (stop A)

- [ ] Area from mass conservation reproduces about 26 mm² at the Teixeira settings.
- [ ] Hot layers about 20% lower than cold at matched settings (the RPI fits give this at v = 10 in the paper's units).
- [ ] Interlayer temperature curves match the Halder table shape at three dwell times.
- [ ] Along-layer variation of about 100-200 °C.
- [ ] Instability onset near 1.65× nominal CTWD (Oueslati: 33 mm against 20 mm).
