"""
stop 0: pioneer probe

three gates:
  G1  per-layer height recoverable from the STL scans
  G2  interlayer temperature series across dwell times
  G3  files load inside the 4h box

prints GO / NO-GO and saves two figures to reports/stop0/
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import trimesh
import pyvista as pv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "pioneer_17608626" / "extracted"
OUT  = ROOT / "reports" / "stop0"
OUT.mkdir(parents=True, exist_ok=True)

DWELLS = [0, 30, 60, 90, 120, 240]

# dwell=0 is the file named combined_file.vtk (no suffix); the rest follow 05_CombinedFile_{d}
VTK_PATHS = {
    0:   DATA / "vtk" / "combined_file.vtk",
    30:  DATA / "vtk" / "05_CombinedFile_30.vtk",
    60:  DATA / "vtk" / "05_CombinedFile_60.vtk",
    90:  DATA / "vtk" / "05_CombinedFile_90.vtk",
    120: DATA / "vtk" / "05_CombinedFile_120.vtk",
    240: DATA / "vtk" / "05_CombinedFile_240.vtk",
}

STL_FMT = DATA / "stl" / "M1_{d}_Free.stl"

TC_COLS = [f"Thermocouple{i}" for i in range(1, 9)]


def _grab(mesh, name):
    """find a named array in any of point/cell/field data"""
    for store in (mesh.point_data, mesh.cell_data, mesh.field_data):
        if name in store:
            return np.asarray(store[name])
    # case-insensitive fallback
    for store in (mesh.point_data, mesh.cell_data, mesh.field_data):
        for k in store.keys():
            if k.lower() == name.lower():
                return np.asarray(store[k])
    return None


def load_logs(dwell, verbose=False):
    """return a dataframe with Robot_Layer and thermocouples for one dwell"""
    p = VTK_PATHS[dwell]
    if not p.exists():
        return None
    mesh = pv.read(p)
    if verbose:
        pk = list(mesh.point_data.keys())
        layer_match = [k for k in pk if "layer" in k.lower()]
        print(f"    {p.name}: {len(pk)} point arrays, layer-like keys: {layer_match}")
    cols = {}
    for name in ["Robot_Layer"] + TC_COLS:
        arr = _grab(mesh, name)
        if arr is not None:
            cols[name] = arr
    if "Robot_Layer" not in cols:
        return None
    # arrays may have different lengths if they live in different stores,
    # trim to the shortest so pandas accepts them
    n = min(len(v) for v in cols.values())
    cols = {k: v[:n] for k, v in cols.items()}
    df = pd.DataFrame(cols)
    df["Robot_Layer"] = df["Robot_Layer"].astype(int)
    return df


def interlayer_temp(df):
    """peak thermocouple reading per layer, averaged across the 8 channels"""
    # skip layer 0 (pre-weld)
    df = df[df["Robot_Layer"] > 0]
    peaks = df.groupby("Robot_Layer")[TC_COLS].max()
    return peaks.mean(axis=1)


def layer_heights_from_stl(path, n_bins=50):
    """slice the wall mesh along its long axis, return top-edge height per bin"""
    m = trimesh.load(path, process=False)
    pts = m.vertices
    # longest horizontal axis is the wall direction
    span = pts.max(axis=0) - pts.min(axis=0)
    long_ax = int(np.argmax([span[0], span[1]]))
    z_ax = 2
    xs = pts[:, long_ax]
    zs = pts[:, z_ax]
    # bin along the wall, take the top point in each bin
    edges = np.linspace(xs.min(), xs.max(), n_bins + 1)
    tops = np.full(n_bins, np.nan)
    for i in range(n_bins):
        m = (xs >= edges[i]) & (xs < edges[i + 1])
        if m.any():
            tops[i] = zs[m].max()
    base = np.nanmin(tops)
    return (edges[:-1] + edges[1:]) / 2, tops - base


def gate2_plot(series_by_dwell):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for d, s in series_by_dwell.items():
        if s is None or len(s) < 3:
            continue
        ax.plot(s.index, s.values, marker="o", label=f"{d} s")
    ax.set_xlabel("layer")
    ax.set_ylabel("peak thermocouple (°C)")
    ax.set_title("interlayer temperature vs dwell (PIONEER M1)")
    ax.legend(title="dwell")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = OUT / "g2_interlayer_temperature.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def gate1_plot(profiles):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for d, (x, h) in profiles.items():
        if x is None:
            continue
        ax.plot(x - x.min(), h, label=f"{d} s")
    ax.set_xlabel("position along wall (mm)")
    ax.set_ylabel("height above base (mm)")
    ax.set_title("wall height profile, dwell=0 vs dwell=240 (PIONEER M1_Free)")
    ax.legend(title="dwell")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = OUT / "g1_wall_profiles.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def main():
    t0 = time.time()
    print(f"data root: {DATA}")

    # G3 as we go: if any load throws, we catch it and report
    g3_ok = True
    load_errors = []

    # ---- G2: temperatures ----
    series = {}
    for d in DWELLS:
        try:
            df = load_logs(d, verbose=True)
            if df is None:
                load_errors.append(f"dwell {d}: no Robot_Layer field found in VTK")
                series[d] = None
                continue
            series[d] = interlayer_temp(df)
            print(f"  dwell={d:>3}: {len(df):>7} rows, "
                  f"{series[d].index.max()} layers, "
                  f"peak {series[d].max():.0f}°C")
        except Exception as e:
            g3_ok = False
            load_errors.append(f"dwell {d} logs: {e}")
            series[d] = None

    g2_path = gate2_plot(series)

    # check hot vs cold trend
    valid = {d: s for d, s in series.items() if s is not None and len(s) > 2}
    g2_ok = False
    if 0 in valid and 240 in valid:
        hot_peak  = valid[0].max()
        cold_peak = valid[240].max()
        g2_ok = hot_peak > cold_peak
        print(f"  hot (0s) peak {hot_peak:.0f}°C  vs  "
              f"cold (240s) peak {cold_peak:.0f}°C  "
              f"=> {'PASS' if g2_ok else 'FAIL'}")

    # ---- G1: heights ----
    profiles = {}
    for d in [0, 240]:
        p = Path(str(STL_FMT).replace("{d}", str(d)))
        if not p.exists():
            load_errors.append(f"stl missing: {p.name}")
            profiles[d] = (None, None)
            continue
        try:
            profiles[d] = layer_heights_from_stl(p)
            x, h = profiles[d]
            print(f"  stl dwell={d}: {len(x)} bins, "
                  f"height {np.nanmin(h):.1f}–{np.nanmax(h):.1f} mm, "
                  f"variation {np.nanmax(h) - np.nanmin(h):.1f} mm")
        except Exception as e:
            g3_ok = False
            load_errors.append(f"stl dwell {d}: {e}")
            profiles[d] = (None, None)

    g1_path = gate1_plot(profiles)

    # G1 real test: hot (0s dwell) vs cold (240s) walls must differ in build height
    # by more than the per-wall ripple. if that signal is there, per-layer
    # height estimation is on the table
    g1_ok = False
    if profiles.get(0, (None, None))[1] is not None and \
       profiles.get(240, (None, None))[1] is not None:
        # top-of-wall = median of the plateau, ignoring the drop-offs at the ends
        h0   = np.nanmedian(np.sort(profiles[0][1])[-20:])
        h240 = np.nanmedian(np.sort(profiles[240][1])[-20:])
        diff = abs(h240 - h0)
        g1_ok = diff > 2.0
        print(f"  wall-top height: 0s={h0:.1f}mm, 240s={h240:.1f}mm, "
              f"diff={diff:.1f}mm  => {'PASS' if g1_ok else 'FAIL'}")

    # ---- summary ----
    dt = time.time() - t0
    print()
    print("=" * 48)
    print(f"  G1 height along wall       : {'PASS' if g1_ok else 'FAIL'}")
    print(f"  G2 temperature vs dwell    : {'PASS' if g2_ok else 'FAIL'}")
    print(f"  G3 files load              : {'PASS' if g3_ok else 'FAIL'}")
    print(f"  elapsed                    : {dt/60:.1f} min")
    print("=" * 48)
    if load_errors:
        print("notes:")
        for e in load_errors:
            print(f"  - {e}")

    verdict = "GO" if (g1_ok and g2_ok and g3_ok) else "NO-GO"
    print(f"\nverdict: {verdict}")
    print(f"figures: {g2_path.name}, {g1_path.name}  (in {OUT})")

    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
