"""Build a wall using estimates to choose the next layer's travel speed.

At each layer: lift the nozzle, deposit, cool, read sensors, estimate, then
choose the next lift and speed. Standoff is measured after deposition and
before the next lift. The scanner returns the previous layer's height.
"""

from dataclasses import asdict
import numpy as np
from process import deposit, S_NOM, sample_build_parameters
from simulator import T_AMB, START_Z, WFS_CMD, TS_CMD, thermal_update
from sensors import SensorState, observe

NOMINAL_STANDOFF = S_NOM
NOMINAL_GROWTH = 1.8                 # Assumed target growth, mm/layer.
TS_MIN, TS_MAX = 5.0, 20.0
TS_GAIN_DEFAULT = 2.0                # mm/s per mm of cumulative height error.
R_Z_MIN, R_Z_MAX = 0.5, 3.5


def run_closed_loop(n_layers, dwell, seed, estimator_builder,
                    controller_gain=1.0, target_wall_height=None,
                    wfs=WFS_CMD, ts=TS_CMD, start_z=START_Z,
                    ctwd_quad=0.005, variant=False, spatter_p=0.02, varied=True):
    """Return truth rows, estimates, next-layer controls, metrics, observations."""
    if n_layers <= 0 or dwell < 0 or wfs <= 0 or ts <= 0:
        raise ValueError('Use positive layers and speeds, and nonnegative dwell.')
    if not 0 <= spatter_p <= 1:
        raise ValueError('Dropout probability must be between zero and one.')
    target = n_layers*NOMINAL_GROWTH if target_wall_height is None else target_wall_height
    if target <= 0:
        raise ValueError('Target wall height must be positive.')
    params = sample_build_parameters(seed, varied=varied, variant=variant)
    rng = np.random.default_rng(seed)
    sensor_state = SensorState(np.random.default_rng(seed+1000),
                               ctwd_quad=ctwd_quad, ctwd_bias0=0.5 if variant else 0)
    estimator = estimator_builder()
    H, Z, T = 0.0, start_z, T_AMB
    speed, lift, previous_est_H = ts, 0.0, 0.0
    rows, estimates, controls, observations = [], [], [], []
    for layer in range(1, n_layers+1):
        Z += lift
        area, width, height, state = deposit(wfs, speed, Z-H, T, params=params)
        H_out = H+height
        T_out = thermal_update(T, H_out, dwell, speed, params=params)
        row = dict(layer=layer, H_in=H, H_out=H_out, Z=Z,
                   standoff_in=Z-H, standoff=Z-H_out, T_in=T, T_out=T_out,
                   area=area, width=width, height=height, regime=state,
                   spatter=bool(rng.random()<spatter_p), ts=speed, r_z=lift)
        obs = observe(row, H, sensor_state)
        applied = dict(wfs=wfs, ts=speed, r_z=lift, dwell=dwell)
        estimate = estimator.update(obs, applied)
        error = estimate['H'] - layer*target/n_layers
        next_speed = float(np.clip(ts + controller_gain*TS_GAIN_DEFAULT*error, TS_MIN, TS_MAX))
        # Lift by estimated growth. Height feedback uses speed, not nozzle Z.
        next_lift = float(np.clip(estimate['H']-previous_est_H, R_Z_MIN, R_Z_MAX))
        rows.append(row); observations.append(obs); estimates.append(estimate)
        controls.append(dict(ts=next_speed, r_z=next_lift))
        previous_est_H = estimate['H']
        H, T, speed, lift = H_out, T_out, next_speed, next_lift
    metrics = dict(final_H=H, target_H=target, wall_err=abs(H-target),
                   last_standoff=rows[-1]['standoff'], final_standoff=Z-H,
                   mean_ts=float(np.mean([r['ts'] for r in rows])),
                   build_parameters=asdict(params))
    return rows, estimates, controls, metrics, observations
