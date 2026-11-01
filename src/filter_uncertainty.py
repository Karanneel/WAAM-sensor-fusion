"""Compare EKF predicted uncertainty with empirical replay errors.

This is a covariance diagnostic, not an observability Gramian or a
Cramer-Rao bound. No claim of steady state is made.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from simulator import run_build
from sensors import SensorState, observe
from ekf import EKF
from sensor_value import sensor_subsets,subset_label

OUT=Path(__file__).resolve().parents[1]/'reports'/'sensor_selection'


def compute_uncertainty(n_seeds=30):
    records=[]
    for subset in sensor_subsets():
        for seed in range(n_seeds):
            model=EKF();state=SensorState(np.random.default_rng(seed+1000))
            rows=run_build(31,60,seed)
            for row in rows:
                obs=observe(row,row['H_in'],state)
                estimate=model.update(obs,dict(wfs=70,ts=row['ts'],r_z=row['r_z'],dwell=60),active_sensors=subset)
                if row['layer']<=21:continue
                for index,(key,truth) in enumerate([('H','H_out'),('standoff','standoff'),('T','T_out')]):
                    records.append(dict(subset=subset_label(subset),seed=seed,layer=row['layer'],state=key,
                                        variance=model.P[index,index],squared_error=(estimate[key]-row[truth])**2))
    raw=pd.DataFrame(records)
    table=raw.groupby(['subset','state'])[['variance','squared_error']].mean().pow(.5).reset_index()
    table=table.rename(columns={'variance':'predicted_std','squared_error':'empirical_rmse'})
    return table


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    table=compute_uncertainty();table.to_csv(OUT/'filter_uncertainty.csv',index=False)
    labels=[subset_label(s) for s in sensor_subsets()]
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for axis,metric,title in zip(axes,['predicted_std','empirical_rmse'],['EKF predicted standard deviation','Observed replay RMSE']):
        values=table.pivot(index='subset',columns='state',values=metric).reindex(index=labels,columns=['H','standoff','T']).to_numpy()
        im=axis.imshow(np.log10(np.maximum(values,1e-8)),aspect='auto',cmap='YlOrBr')
        axis.set_yticks(range(8),labels);axis.set_xticks(range(3),['H (mm)','S (mm)','T (C)']);axis.set_title(title)
        for i in range(8):
            for j in range(3):axis.text(j,i,f'{values[i,j]:.2f}',ha='center',va='center',fontsize=8)
        fig.colorbar(im,ax=axis,label='log10 value')
    fig.savefig(OUT/'filter_uncertainty.png',dpi=150);plt.close(fig)
    return table


if __name__=='__main__':main()
