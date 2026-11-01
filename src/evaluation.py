"""Paired build-level comparisons for the revised evaluation protocol."""

import numpy as np
import pandas as pd


def paired_improvement(frame, estimator, metric, n_boot=2000):
    pairs = frame.pivot(index='seed', columns='estimator', values=metric)[['naive', estimator]].dropna()
    if len(pairs) < 2:
        return dict(n=len(pairs), improvement_pct=np.nan, ci_low=np.nan, ci_high=np.nan, passed=False)
    baseline = pairs['naive'].to_numpy()
    candidate = pairs[estimator].to_numpy()
    delta = baseline-candidate
    rng = np.random.default_rng(907)
    means = delta[rng.integers(0, len(delta), (n_boot, len(delta)))].mean(axis=1)
    low, high = np.quantile(means, [.025, .975])
    improvement = 100*(1-candidate.mean()/baseline.mean()) if baseline.mean()>0 else np.nan
    return dict(n=len(pairs), improvement_pct=improvement, ci_low=float(low), ci_high=float(high),
                passed=bool(len(pairs)>=30 and improvement>=10 and low>0))


def evaluate_gate(main, dropout):
    """Layer-end standoff, drifted temperature, and dropout-only joint H/S error.

    This is a dated replacement protocol. The layerwise simulator cannot
    resolve the old plan's between-scan trajectories.
    """
    rows = []
    for (error_type, level, gain), cell in main[main.level.isin([0, .15])].groupby(['error_type','level','gain']):
        stressed = dropout[(dropout.error_type==error_type)&(dropout.level==level)&(dropout.gain==gain)]
        for estimator in ['EKF', 'learned']:
            for category, data, metric in [('standoff', cell, 'rmse_s'),
                                           ('temperature', cell, 'rmse_T'),
                                           ('dropout', stressed, 'dropout_joint')]:
                rows.append(dict(error_type=error_type, level=level, gain=gain,
                                 estimator=estimator, category=category,
                                 **paired_improvement(data, estimator, metric)))
    return pd.DataFrame(rows)


def tied_winners(frame, metric, atol=1e-6):
    result = {}
    summary = frame.groupby(['error_type','level','gain','estimator'])[metric].mean().reset_index()
    for cell, group in summary.groupby(['error_type','level','gain']):
        minimum = group[metric].min()
        result[cell] = sorted(group.loc[np.isclose(group[metric], minimum, rtol=0, atol=atol), 'estimator'])
    return result
