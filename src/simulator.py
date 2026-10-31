"""
layer-by-layer simulation of a waam wall build.

state carried between layers:
  H  wall-top height above base plate (mm)
  Z  nozzle height above base plate (mm). standoff = Z - H
  T  part temperature (C), lumped single-node model

each layer:
  deposit one segment, update H
  cool during deposit time (wall_length / ts)
  cool during dwell time
  advance Z by the commanded increment r_z
"""

import math
import numpy as np

from process import deposit


T_AMB = 25.0
DT_LAYER = 100.0         # C added at H=0 per layer; shrinks as wall mass grows
H_MASS = 15.0            # mm. dt_eff = DT_LAYER / (1 + H/H_MASS)
TAU_BASE = 30.0          # s thermal time constant at H=0
TAU_GROWTH = 5.0         # s per mm of wall height

# default build command
WFS_CMD = 70.0           # mm/s wire feed
TS_CMD = 10.0            # mm/s travel speed
R_Z_CMD = 1.5            # mm nominal commanded Z increment per layer
START_Z = 15.0           # mm nozzle height above base at layer 1
WALL_LENGTH = 150.0      # mm


def thermal_update(T, H, dwell, ts, wall_length=WALL_LENGTH, beta=1.0):
    """lumped balance across the deposit time plus the dwell.

    beta=1 is the standard exponential decay. beta<1 is a stretched
    exponential, used only by the sealed-generator check
    """
    tau = TAU_BASE + TAU_GROWTH * H
    t_dep = wall_length / ts
    dt_eff = DT_LAYER / (1.0 + H / H_MASS)
    peak = T + dt_eff
    if beta == 1.0:
        decay_dep = math.exp(-t_dep / tau)
        decay_dwell = math.exp(-dwell / tau) if dwell > 0 else 1.0
    else:
        decay_dep = math.exp(-((t_dep / tau) ** beta))
        decay_dwell = math.exp(-((dwell / tau) ** beta)) if dwell > 0 else 1.0
    T_after_dep = T_AMB + (peak - T_AMB) * decay_dep
    T_end = T_AMB + (T_after_dep - T_AMB) * decay_dwell
    return T_end


def run_build(n_layers, dwell, seed=0,
              wfs=WFS_CMD, ts=TS_CMD, r_z=R_Z_CMD, spatter_p=0.02):
    """simulate a wall build. returns a list of per-layer dicts"""
    rng = np.random.default_rng(seed)
    H = 0.0
    Z = START_Z
    T = T_AMB
    rows = []
    for k in range(1, n_layers + 1):
        standoff = Z - H
        area, width, height, state = deposit(wfs, ts, standoff, T)
        # cheap spatter model; sensors use this to decide if scan is blocked
        spatter = rng.random() < spatter_p
        H_new = H + height
        T_new = thermal_update(T, H_new, dwell, ts)
        rows.append({
            "layer": k, "H_in": H, "Z": Z, "standoff": standoff,
            "T_in": T, "T_out": T_new,
            "area": area, "width": width, "height": height,
            "regime": state, "spatter": spatter, "H_out": H_new,
        })
        H = H_new
        Z = Z + r_z
        T = T_new
    return rows
