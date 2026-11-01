"""Inspect local PIONEER logs and final wall scans without claiming calibration."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pyvista as pv
import trimesh

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'pioneer_17608626'/'extracted'
OUT=ROOT/'reports'/'data_probe'
TC_COLS=[f'Thermocouple{i}' for i in range(1,9)]


def load_logs(dwell):
    name='combined_file.vtk' if dwell==0 else f'05_CombinedFile_{dwell}.vtk'
    path=DATA/'vtk'/name
    if not path.exists():return None,'file missing'
    mesh=pv.read(path)
    fields={}
    for store in [mesh.point_data,mesh.cell_data,mesh.field_data]:
        for key in ['Robot_Layer']+TC_COLS:
            if key in store:fields[key]=np.asarray(store[key])
    if 'Robot_Layer' not in fields:return None,'no directly logged layer labels'
    if any(key not in fields for key in TC_COLS):return None,'thermocouple channels missing'
    if len({len(v) for v in fields.values()})!=1:return None,'channel lengths differ; alignment not established'
    labels = fields['Robot_Layer']
    if not np.allclose(labels, np.rint(labels), atol=1e-3, rtol=0):
        return None,'layer labels are not near integers; phase interpretation required'
    fields['Robot_Layer'] = np.rint(labels).astype(int)
    return pd.DataFrame(fields),None


def top_profile(path,n_bins=50):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        raise ValueError('STL contains no directly readable wall mesh')
    points = mesh.vertices
    if len(points) < 3:
        raise ValueError('STL has fewer than three vertices')
    span=np.ptp(points,axis=0)
    axis=int(np.argmax(span[:2]))
    edges=np.linspace(points[:,axis].min(),points[:,axis].max(),n_bins+1)
    profile=[]
    for index,(left,right) in enumerate(zip(edges[:-1],edges[1:])):
        mask=(points[:,axis]>=left)&((points[:,axis]<=right) if index==n_bins-1 else (points[:,axis]<right))
        profile.append(float(points[mask,2].max()) if mask.any() else np.nan)
    return (edges[:-1]+edges[1:])/2,np.asarray(profile)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(thermal_series={},wall_profiles={},errors={},
                calibration_status='not fitted',
                original_requirements_satisfied=False,
                conclusion='Exploratory data only; no measured per-layer height or three-dwell interlayer-temperature validation established.')
    fig,axis=plt.subplots(figsize=(7,4),layout='constrained')
    for dwell in [0,30,60,90,120,240]:
        try:
            frame,error=load_logs(dwell)
            if error:
                report['errors'][str(dwell)]=error;continue
            frame=frame[frame.Robot_Layer>0]
            peaks=frame.groupby('Robot_Layer')[TC_COLS].max().mean(axis=1)
            report['thermal_series'][str(dwell)]=dict(logged_layer_labels=len(peaks),peak_C=float(peaks.max()))
            axis.plot(peaks.index,peaks.values,label=f'{dwell} s dwell')
        except Exception as error:report['errors'][str(dwell)]=str(error)
    axis.set(xlabel='Logged layer',ylabel='Mean of channel peaks (C)',title='Thermocouple peaks, not interlayer temperature')
    if report['thermal_series']:axis.legend()
    axis.grid(alpha=.2);fig.savefig(OUT/'temperature_peaks.png',dpi=150);plt.close(fig)
    fig,axis=plt.subplots(figsize=(7,4),layout='constrained')
    for dwell in [0,30,60,120,240]:
        path=DATA/'stl'/f'M1_{dwell}_Free.stl'
        if not path.exists():continue
        try:
            x,z=top_profile(path)
            axis.plot(x-x.min(),z,label=f'{dwell} s dwell')
            report['wall_profiles'][str(dwell)]=dict(z_min=float(np.nanmin(z)),z_max=float(np.nanmax(z)))
        except Exception as error:report['errors'][f'scan_{dwell}']=str(error)
    axis.set(xlabel='Position along scan (mm)',ylabel='Top edge in scan Z coordinates (mm)',title='Final scan profiles; substrate datum unverified')
    if report['wall_profiles']:axis.legend()
    axis.grid(alpha=.2);fig.savefig(OUT/'wall_profiles.png',dpi=150);plt.close(fig)
    (OUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(report['conclusion'])
    print(f'Loaded {len(report["thermal_series"])} labelled thermal series and {len(report["wall_profiles"])} final scans.')
    return 0 if report['thermal_series'] or report['wall_profiles'] else 1


if __name__=='__main__':raise SystemExit(main())
