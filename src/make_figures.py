"""Draw the wall schematic, one simulated build, and a result overview."""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from matplotlib.animation import FuncAnimation, PillowWriter
from harness import run_closed_loop
from ekf import EKF

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'figures'
TEAL='#285f68'
ORANGE='#bd613c'
GRAY='#56616c'


def schematic():
    fig,axis=plt.subplots(figsize=(11,4.7),layout='constrained')
    axis.set(xlim=(-30,205),ylim=(-10,92));axis.axis('off')
    axis.add_patch(Rectangle((-12,-4),180,4,color='#d4d8d8'))
    for layer in range(12):
        axis.add_patch(Rectangle((0,layer*3.2),150,3.2,facecolor='#c5d4d4',edgecolor='white',lw=.7))
    H=38.4;Z=57
    axis.add_patch(Polygon([(68,Z+18),(82,Z+18),(79,Z),(71,Z)],facecolor=GRAY))
    axis.plot([75,75],[Z,Z+35],color=GRAY,lw=2)
    axis.annotate('',(75,H),(75,Z),arrowprops=dict(arrowstyle='<->',color=ORANGE,lw=1.5))
    axis.text(81,47,'Standoff S = Z - H',fontsize=10,color=ORANGE)
    for x,height,label in [(158,H,'H'),(178,Z,'Z')]:
        axis.annotate('',(x,0),(x,height),arrowprops=dict(arrowstyle='<->',color=TEAL))
        axis.text(x+3,height/2,label,fontsize=12,color=TEAL)
    axis.annotate('Delayed height scan',xy=(20,H-3.2),xytext=(-24,70),
                  arrowprops=dict(arrowstyle='->',color=TEAL),color=TEAL,fontsize=10)
    axis.annotate('Pyrometer: temperature',xy=(125,H),xytext=(108,80),
                  arrowprops=dict(arrowstyle='->',color=ORANGE),color=ORANGE,fontsize=10)
    axis.text(-12,-8,'Base plate',fontsize=10,color=GRAY)
    axis.text(-25,88,'A wall built one layer at a time',fontsize=17,weight='bold',color=TEAL)
    axis.text(0,10,'Deposited layers',fontsize=11,color=TEAL)
    fig.savefig(OUT/'wall_schematic.png',dpi=160);plt.close(fig)


def build_animation():
    rows,estimates,controls,metrics,observations=run_closed_loop(31,60,0,EKF)
    table=pd.DataFrame(rows)
    for state in ['H','standoff','T']:table[f'estimated_{state}']=[e[state] for e in estimates]
    table['scanner_missing']=[o['scanner'] is None for o in observations]
    table['next_ts']=[c['ts'] for c in controls]
    table['next_lift']=[c['r_z'] for c in controls]
    table.to_csv(OUT/'example_build.csv',index=False)
    fig=plt.figure(figsize=(10,5.7),layout='constrained')
    grid=fig.add_gridspec(2,2,width_ratios=[1.1,1])
    wall=fig.add_subplot(grid[:,0]);height=fig.add_subplot(grid[0,1]);speed=fig.add_subplot(grid[1,1])
    fig.suptitle('One simulated wall | 60 s dwell | EKF feedback',fontsize=14,color=TEAL)
    levels=np.arange(1,32)
    def update(index):
        count=index+1;row=rows[index]
        for axis in [wall,height,speed]:axis.clear()
        wall.set(xlim=(-10,180),ylim=(-5,85),xlabel='Nominal wall length (mm)',ylabel='Height (mm)')
        wall.add_patch(Rectangle((-5,-3),165,3,color='#d4d8d8'))
        for r in rows[:count]:
            wall.add_patch(Rectangle((0,r['H_in']),150,r['height'],facecolor='#c5d4d4',edgecolor='white',lw=.5))
        wall.add_patch(Polygon([(69,row['Z']+10),(81,row['Z']+10),(78,row['Z']),(72,row['Z'])],facecolor=GRAY))
        wall.plot([0,150],[count*1.8]*2,'--',color=ORANGE,lw=1)
        wall.set_title(f'Layer {count}/31 | T = {row["T_out"]:.0f} C',fontsize=11)
        wall.text(0,76,'Schematic side view\nNo spatial thermal field',fontsize=9,color=GRAY)
        height.plot(levels[:count],[r['H_out'] for r in rows[:count]],label='True H',color=TEAL,lw=2)
        height.plot(levels[:count],[e['H'] for e in estimates[:count]],'--',label='Estimated H',color=ORANGE)
        height.plot(levels,levels*1.8,':',color=GRAY,label='Target')
        height.set(xlim=(1,31),ylim=(0,60),ylabel='Wall height (mm)');height.legend(fontsize=8);height.grid(alpha=.15)
        speed.plot(levels[:count],[r['ts'] for r in rows[:count]],color=TEAL)
        speed.set(xlim=(1,31),ylim=(5,20),xlabel='Layer',ylabel='Applied speed (mm/s)');speed.grid(alpha=.15)
    update(30);fig.savefig(OUT/'example_build.png',dpi=150)
    animation=FuncAnimation(fig,update,frames=31,interval=180)
    animation.save(OUT/'wall_build.gif',writer=PillowWriter(fps=6),dpi=90)
    plt.close(fig)


def results_overview():
    nominal=pd.read_csv(ROOT/'reports'/'experiments'/'model_error.csv')
    blocked=pd.read_csv(ROOT/'reports'/'experiments'/'dropout.csv')
    names=['naive','EKF','learned','reference','schedule_only']
    labels=['Baseline','EKF','Learned','Reference EKF','No sensors']
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
    for axis,metric,title in zip(axes,['wall_err','rmse_H'],['Final wall-height error','Height-estimation error']):
        for offset,frame,label,color in [(-.17,nominal,'2% dropout',TEAL),(.17,blocked,'20% dropout',ORANGE)]:
            base=frame[(frame.error_type=='width_temperature')&(frame.level==0)&(frame.gain==1)]
            values=base.groupby('estimator')[metric].mean().reindex(names)
            axis.barh(np.arange(5)+offset,values,height=.30,label=label,color=color)
        axis.set_yticks(range(5),labels);axis.invert_yaxis()
        axis.set(title=title,xlabel='Mean error over 30 builds (mm)');axis.grid(alpha=.15,axis='x');axis.set_axisbelow(True)
    axes[0].legend(fontsize=9)
    fig.suptitle('Nominal model | 60 s dwell | same training for both dropout conditions',fontsize=12)
    fig.savefig(OUT/'estimator_comparison.png',dpi=160);plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    schematic();build_animation();results_overview()
    print(f'Figures written to {OUT}')


if __name__=='__main__':main()
