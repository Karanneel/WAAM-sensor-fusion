"""
closed-loop experiment harness. ties the sim, sensors, estimator and
controller together into one function so the planted-error sweep can call it
many times.

per layer:
  deposit physically, update truth state
  observe (noisy obs from sensors)
  estimator consumes obs, returns state estimate
  controller consumes estimate, returns r_z for the next layer

final outcome: wall-height error against a reference target. that is the
Q8 scoring metric
"""

import math
import numpy as np

from process import deposit, S_NOM
from simulator import (T_AMB, R_Z_CMD, START_Z, WFS_CMD, TS_CMD,
                       thermal_update)
from sensors import SensorState, observe


# controller tries to keep standoff at this value
NOMINAL_STANDOFF = S_NOM

# nominal per-layer wall growth at calibrated params. the actual growth
# depends on temperature; this is the baseline the controller plans against
NOMINAL_GROWTH = 1.8                 # mm per layer at dwell=60 reference

# clamp on the commanded Z increment to avoid wild excursions
R_Z_MIN, R_Z_MAX = 0.5, 3.5


def run_closed_loop(n_layers, dwell, seed, estimator_builder,
                    controller_gain=1.0, target_wall_height=None,
                    wfs=WFS_CMD, ts=TS_CMD, start_z=START_Z,
                    ctwd_quad=0.005, sealed=False, spatter_p=0.02):
    """sealed=True enables the pre-registered sealed-generator check:
    cooling exponent 0.85, shape factor 3/4, +0.5mm CTWD bias.
    spatter_p controls the per-layer probability of a scanner dropout"""
    """returns (rows, estimates, controls, metrics)"""
    # sealed-variant knobs
    shape = 3.0 / 4.0 if sealed else None   # None lets process.deposit use SHAPE
    beta = 0.85 if sealed else 1.0
    ctwd_bias0 = 0.5 if sealed else 0.0

    rng = np.random.default_rng(seed)
    sens_rng = np.random.default_rng(seed + 1000)
    sens_state = SensorState(sens_rng, ctwd_quad=ctwd_quad,
                             ctwd_bias0=ctwd_bias0)
    est = estimator_builder()

    H = 0.0
    Z = start_z
    T = T_AMB
    prev_H = 0.0

    rows, estimates, controls, obs_list = [], [], [], []

    # first layer uses nominal r_z; controller sets r_z for layer 2 onward
    r_z_next = NOMINAL_GROWTH

    for k in range(1, n_layers + 1):
        standoff = Z - H
        area, width, height, regime = deposit(wfs, ts, standoff, T, shape=shape)
        spatter = rng.random() < spatter_p
        H_out = H + height
        T_out = thermal_update(T, H_out, dwell, ts, beta=beta)

        row = {"layer": k, "H_in": H, "Z": Z, "standoff": standoff,
               "T_in": T, "T_out": T_out, "area": area, "width": width,
               "height": height, "regime": regime, "spatter": spatter,
               "H_out": H_out}
        rows.append(row)

        obs = observe(row, prev_H, sens_state)
        obs_list.append(obs)
        ctrl = {"wfs": wfs, "ts": ts, "r_z": r_z_next, "dwell": dwell}
        est_out = est.update(obs, ctrl)
        estimates.append(est_out)

        # controller: P on standoff error
        s_err = NOMINAL_STANDOFF - est_out["standoff"]
        r_z_next = NOMINAL_GROWTH + controller_gain * s_err
        r_z_next = max(R_Z_MIN, min(R_Z_MAX, r_z_next))
        controls.append(r_z_next)

        # advance truth
        H = H_out
        Z = Z + r_z_next
        T = T_out
        prev_H = H_out

    if target_wall_height is None:
        target_wall_height = n_layers * NOMINAL_GROWTH
    metrics = {
        "final_H":        H,
        "target_H":       target_wall_height,
        "wall_err":       abs(H - target_wall_height),
        "final_standoff": H - prev_H,     # not meaningful; see standoff below
        "last_standoff":  rows[-1]["standoff"],
    }
    return rows, estimates, controls, metrics, obs_list


# obs_list is collected inside the loop; keep the per-layer obs for callers that
# need to replay them (e.g. training a learned estimator on closed-loop data)
