"""Compare estimators under explicit model and measurement perturbations."""

import numpy as np
import pandas as pd
from harness import run_closed_loop
from estimators import Naive
from ekf import EKF, KFParams
from learned import Learned
from reference_filter import ReferenceEKF

ERROR_TYPES = ('width_temperature', 'cooling_time', 'ctwd_curve')
LEVELS = (0.0, 0.15, 0.30, 0.60)
GAINS = (0.5, 1.0)
EVALUATION_SEEDS = range(30)


def ekf_builder(error_type, level, subset=None):
    p = KFParams()
    if error_type == 'width_temperature':
        p.fw_slope *= 1+level
    elif error_type == 'cooling_time':
        p.tau_base *= 1+level
    elif error_type != 'ctwd_curve':
        raise ValueError(f'Unknown error type: {error_type}')
    class SubsetEKF(EKF):
        def update(self, obs, control):
            return super().update(obs, control, active_sensors=subset)
    return lambda: SubsetEKF(params=p)


def score_build(rows, estimates, observations, metrics):
    def rmse(state, truth, mask=None):
        errors = np.array([e[state]-r[truth] for e, r in zip(estimates, rows)])
        if mask is not None:
            errors = errors[mask]
        return float(np.sqrt(np.mean(errors**2))) if len(errors) else np.nan
    # Layer one has no previous wall to scan; it is not a spatter dropout.
    missing = np.array([o['scanner'] is None and r['layer']>1 for o, r in zip(observations, rows)])
    H_missing = rmse('H', 'H_out', missing)
    s_missing = rmse('standoff', 'standoff', missing)
    return dict(wall_err=metrics['wall_err'], last_S=metrics['last_standoff'],
                mean_ts=metrics['mean_ts'], rmse_H=rmse('H', 'H_out'),
                rmse_T=rmse('T', 'T_out'), rmse_s=rmse('standoff', 'standoff'),
                dropout_count=int(missing.sum()), rmse_dropout_H=H_missing,
                rmse_dropout_s=s_missing,
                dropout_joint=float(np.hypot(H_missing, s_missing)))


def run_sweep(models, schedule_models=None, error_types=ERROR_TYPES, levels=LEVELS,
              gains=GAINS, n_seeds=30, dwell=60, variant=False, dropout_p=0.02):
    records = []
    for error_type in error_types:
        for level in levels:
            curve = 0.005*(1+level) if error_type == 'ctwd_curve' else 0.005
            for gain in gains:
                for seed in range(n_seeds):
                    builders = dict(naive=Naive, EKF=ekf_builder(error_type, level),
                                    learned=lambda: Learned(models),
                                    reference=lambda: ReferenceEKF(ctwd_quad=curve, variant=variant))
                    if schedule_models is not None:
                        builders['schedule_only'] = lambda: Learned(schedule_models, subset=set())
                    for name, builder in builders.items():
                        rows, estimates, _, metrics, obs = run_closed_loop(
                            31, dwell, seed, builder, controller_gain=gain,
                            variant=variant, spatter_p=dropout_p, ctwd_quad=curve)
                        records.append(dict(error_type=error_type, level=level, gain=gain,
                                            seed=seed, estimator=name,
                                            **score_build(rows, estimates, obs, metrics)))
    return pd.DataFrame(records)
