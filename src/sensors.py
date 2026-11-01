"""One delayed height scan and two layer-end measurements per layer.

CTWD is a synthetic quadratic standoff channel, not an arc-signal model.
Noise and drift magnitudes are assumptions; sigma is not the same as MAE.
"""

import numpy as np


# scanner, Keyence LJ-X8000 class, one profile per layer at layer-end
SCANNER_SIGMA = 0.03             # mm per-point noise
SCANNER_DROPOUT_P = 0.02         # fraction of layers blocked by spatter

# pyrometer, emissivity bias as a slow random walk, plus noise
PYRO_BIAS_WALK = 0.005           # per-layer std of multiplicative bias drift
PYRO_NOISE_SIGMA = 5.0           # degC gaussian noise

# Assumed CTWD noise, in mm; no fit to arc-waveform data is claimed.
CTWD_NOISE_SIGMA = 0.2           # mm
CTWD_BIAS_WALK = 0.003           # mm per-layer additive bias drift
CTWD_NOMINAL = 15.0              # mm, matches process.S_NOM


class SensorState:
    """carries slow-drifting sensor states across layers"""
    def __init__(self, rng, ctwd_quad=0.005, ctwd_bias0=0.0):
        self.rng = rng
        seeds = rng.integers(0, 2**32, size=3)
        self.scan_rng, self.pyro_rng, self.ctwd_rng = [np.random.default_rng(int(s)) for s in seeds]
        self.pyro_bias = 1.0            # multiplicative, 1.0 = no bias
        self.ctwd_bias = ctwd_bias0     # additive bias in mm
        self.mode = "steady"            # welding mode affects CTWD mapping
        self.ctwd_quad = ctwd_quad      # quadratic coef in CTWD mapping


def scanner_read(H_prev, spatter, rng):
    """direct height from the layer under the nozzle; None on spatter block.
    returns None at layer 1 too, since there's nothing deposited yet to scan"""
    if spatter or H_prev <= 0.0:
        return None
    return H_prev + rng.normal(0.0, SCANNER_SIGMA)


def pyrometer_read(T_true, state):
    state.pyro_bias += state.pyro_rng.normal(0.0, PYRO_BIAS_WALK)
    noise = state.pyro_rng.normal(0.0, PYRO_NOISE_SIGMA)
    return state.pyro_bias * T_true + noise


def ctwd_read(standoff, state):
    err = standoff - CTWD_NOMINAL
    # steady mode is nearly linear with a mild quadratic. a dip mode would
    # saturate; left as a mode-switch hook for the robustness tests
    if state.mode == "steady":
        signal = err + state.ctwd_quad * err ** 2
    else:
        signal = np.tanh(err / 5.0) * 5.0
    state.ctwd_bias += state.ctwd_rng.normal(0.0, CTWD_BIAS_WALK)
    noise = state.ctwd_rng.normal(0.0, CTWD_NOISE_SIGMA)
    return CTWD_NOMINAL + signal + state.ctwd_bias + noise


def observe(row, prev_H, state):
    """three sensor observations for one layer step"""
    scan = scanner_read(prev_H, row["spatter"], state.scan_rng)
    pyro = pyrometer_read(row["T_out"], state)
    ctwd = ctwd_read(row["standoff"], state)
    return {"scanner": scan, "pyro": pyro, "ctwd": ctwd}
