"""Sensor-subset comparisons with separate EKF and learned-model results."""

import itertools
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from learned import train_models, Learned, TRAIN_DWELLS
from harness import run_closed_loop
from sweep import ekf_builder, score_build

ALL_SENSORS = ['scanner','pyro','ctwd']
SENSOR_COST = dict(scanner=5.0, pyro=2.0, ctwd=1.0)
STATE_NAMES = ['H','standoff','T']
OUT = Path(__file__).resolve().parents[1]/'reports'/'sensor_selection'


def sensor_subsets():
    return [set(c) for size in range(4) for c in itertools.combinations(ALL_SENSORS,size)]


def subset_label(subset):
    return '+'.join(s for s in ALL_SENSORS if s in subset) or 'none'


def composite_rmse(values):
    return float(np.sqrt(values['rmse_H']**2 + values['rmse_s']**2 + (values['rmse_T']/10)**2))


def train_subset_learned(subset):
    builds=[(d,s) for d in TRAIN_DWELLS for s in range(100,120)]
    return train_models(builds=builds, subset=subset)


def compute_subsets(n_seeds=30):
    records=[]
    for subset in sensor_subsets():
        label=subset_label(subset)
        print(f'Training subset: {label}',flush=True)
        models=train_subset_learned(subset)
        for error_type in ['width_temperature','cooling_time','ctwd_curve']:
            curve=.0065 if error_type=='ctwd_curve' else .005
            for seed in range(n_seeds):
                builders={'EKF':ekf_builder(error_type,.30,subset),
                          'learned':lambda:Learned(models,subset=subset)}
                for name,builder in builders.items():
                    rows,est,_,metrics,obs=run_closed_loop(31,60,seed,builder,ctwd_quad=curve)
                    score=score_build(rows,est,obs,metrics)
                    records.append(dict(subset=label,estimator=name,error_type=error_type,seed=seed,
                                        cost=sum(SENSOR_COST[s] for s in subset),
                                        composite=composite_rmse(score),**score))
    return pd.DataFrame(records)


def exact_shapley(utility):
    """Attribute negative mean composite error to the three sensor channels."""
    result={}
    for sensor in ALL_SENSORS:
        others=[s for s in ALL_SENSORS if s!=sensor]
        value=0.0
        for size in range(3):
            for combination in itertools.combinations(others,size):
                subset=set(combination)
                weight=math.factorial(size)*math.factorial(2-size)/math.factorial(3)
                value+=weight*(utility[subset_label(subset|{sensor})]-utility[subset_label(subset)])
        result[sensor]=value
    return result


def is_pareto(costs,errors):
    costs=np.asarray(costs);errors=np.asarray(errors)
    return np.array([not np.any((costs<=c)&(errors<=e)&((costs<c)|(errors<e)))
                     for c,e in zip(costs,errors)])


def summarize(frame):
    return frame.groupby(['estimator','subset','cost'])[['rmse_H','rmse_s','rmse_T','composite']].mean().reset_index()


def plot_pareto(frame):
    summary=summarize(frame)
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    for axis,(name,group) in zip(axes,summary.groupby('estimator')):
        good=is_pareto(group.cost,group.composite)
        axis.scatter(group.cost,group.composite,color='#326b82')
        front=group.loc[good].sort_values('cost')
        axis.plot(front.cost,front.composite,'o-',color='#b45f36',label='Pareto front')
        for row in group.itertuples():
            axis.annotate(row.subset,(row.cost,row.composite),xytext=(3,5),textcoords='offset points',fontsize=7)
        axis.set(title=name,xlabel='Assumed relative sensor cost',ylabel='Mean normalized error')
        axis.grid(alpha=.2);axis.legend()
    fig.savefig(OUT/'pareto_front.png',dpi=150);plt.close(fig)


def write_report(frame):
    summary=summarize(frame)
    lines=['# Sensor selection','','Each estimator is evaluated separately on 30 test builds per sensor subset and error type.',
           'Learned models, including the no-sensor model, use the same 100 training builds (seeds 100-119 at five dwell settings).',
           'No test errors are used to choose an estimator. Costs and error normalization are assumptions.',
           'Training uses mixed fixed-speed and EKF-piloted trajectories. Evaluation uses each estimator in its own control loop; this is a policy distribution shift.',
           '', '| Estimator | Sensors | Cost | H RMSE (mm) | S RMSE (mm) | T RMSE (C) | Composite |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in summary.itertuples():
        lines.append(f'| {r.estimator} | {r.subset} | {r.cost:g} | {r.rmse_H:.3f} | {r.rmse_s:.3f} | {r.rmse_T:.2f} | {r.composite:.3f} |')
    lines+=['','Composite error = sqrt((H/1 mm)^2 + (S/1 mm)^2 + (T/10 C)^2), calculated per build and then averaged.',
            'The no-sensor learned baseline still receives layer number, dwell and applied travel speed. These are known controls, not sensor channels.',
            'Costs: scanner 5, pyrometer 2, CTWD 1 relative units. Shapley utility is negative error and does not include cost.', '', '## Rankings and tradeoffs','']
    shapley_rows=[]
    for name,group in frame.groupby('estimator'):
        avg=summary[summary.estimator==name]
        front=avg.loc[is_pareto(avg.cost,avg.composite),'subset'].tolist()
        lines.append(f'- {name} Pareto subsets: '+', '.join(front)+'.')
        for error_type,config in group.groupby('error_type'):
            utility=(-config.groupby('subset').composite.mean()).to_dict()
            attribution=exact_shapley(utility)
            ordering=sorted(attribution,key=attribution.get,reverse=True)
            lines.append(f'- {name}, {error_type}: '+' > '.join(ordering)+'.')
            for sensor,value in attribution.items():
                shapley_rows.append(dict(estimator=name,error_type=error_type,sensor=sensor,shapley=value))
    lines+=['','These rankings apply to the tested generator, controls and scaling assumptions. They are not model-independent sensor recommendations.',
            'Uncertainty for close subset rankings has not been estimated; the Pareto plot shows point estimates.']
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pd.DataFrame(shapley_rows).to_csv(OUT/'shapley.csv',index=False)
    summary.to_csv(OUT/'subset_means.csv',index=False)


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    data=compute_subsets();data.to_csv(OUT/'subset_results.csv',index=False)
    plot_pareto(data);write_report(data)
