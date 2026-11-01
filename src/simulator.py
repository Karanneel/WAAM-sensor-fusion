"""Layerwise wall growth and cooling, with an optional fixed-speed build."""

import math
import numpy as np
from process import deposit, sample_build_parameters

T_AMB = 25.0
DT_LAYER = 100.0
H_MASS = 15.0
TAU_BASE = 30.0
TAU_GROWTH = 5.0
WFS_CMD = 70.0
TS_CMD = 10.0
R_Z_CMD = 1.5
START_Z = 15.0
WALL_LENGTH = 150.0


def thermal_update(T, H, dwell, ts, wall_length=WALL_LENGTH, beta=None, params=None):
    p = params or sample_build_parameters(0, varied=False)
    exponent = p.cooling_exponent if beta is None else beta
    tau = p.tau_base + p.tau_growth*H
    heat = p.heat_increment / (1 + H/H_MASS)
    # One elapsed-time interval avoids restarting stretched cooling at the dwell.
    elapsed = wall_length/ts + dwell
    return T_AMB + (T + heat - T_AMB)*math.exp(-(elapsed/tau)**exponent)


def run_build(n_layers, dwell, seed=0, wfs=WFS_CMD, ts=TS_CMD,
              r_z=R_Z_CMD, spatter_p=0.02, varied=True):
    if n_layers <= 0 or dwell < 0 or wfs <= 0 or ts <= 0:
        raise ValueError('Use positive layers and speeds, and nonnegative dwell.')
    rng = np.random.default_rng(seed)
    params = sample_build_parameters(seed, varied=varied)
    H, Z, T = 0.0, START_Z, T_AMB
    rows = []
    for layer in range(1, n_layers+1):
        lift = 0.0 if layer == 1 else r_z
        Z += lift
        area, width, height, state = deposit(wfs, ts, Z-H, T, params=params)
        H_out = H+height
        T_out = thermal_update(T, H_out, dwell, ts, params=params)
        rows.append(dict(layer=layer, H_in=H, H_out=H_out, Z=Z,
                         standoff_in=Z-H, standoff=Z-H_out, T_in=T, T_out=T_out,
                         area=area, width=width, height=height, regime=state,
                         spatter=bool(rng.random()<spatter_p), ts=ts, r_z=lift))
        H, T = H_out, T_out
    return rows
