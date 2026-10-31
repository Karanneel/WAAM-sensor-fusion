# Data manifest

Raw data is not redistributed. Download from the source, keep it in this folder (git-ignored), and log what was pulled in `pull_log.csv`.

No open dataset has per-layer measured height plus multiple in-process sensors for a wall. Real data checks the simulator's physics; it does not score fusion.

| Priority | Dataset | Use | Contents | Size / licence | Status |
|---|---|---|---|---|---|
| 1 | [PIONEER WAAM Open Repository, Zenodo 17608626](https://zenodo.org/records/17608626) | Stop 0 probe; thermal calibration vs dwell | WAAM walls, ER70S6 and ER110SG, dwell 30/60/90/120/240 s. IR + active-illumination video (H.265 MKV); voltage, current, wire speed, robot speed/position, thermocouples (VTK); post-build STL point clouds with and without clamps; FEM predictions (VMAP) | ~9.1 GB in 7 ZIPs, CC BY 4.0 | Record checked 2026-10-17. Per-layer height **not confirmed** |
| 2 | [Cranfield 24311296](https://dspace.lib.cranfield.ac.uk/handle/1826/22028), "Automated interlayer wall height compensation for wire based DED" | Possible WAAM height ground truth | Unknown | CC BY 4.0 | **Contents unverified**; open manually |
| 3 | [ORNL WAAM co-registered](https://www.nature.com/articles/s41597-025-04638-0) (DOI 10.13139/ORNLNCCS/2439935) | Multi-rate replay; ROS 2 stage | Robot position ~16.7 Hz; current/voltage/wire feed 100 S/s; mic 50 kHz; captured as ROS bags, released as HDF5; XCT surface registered to STL | Globus; size not stated | No per-layer height |
| Later (DED) | [NSF/TAMU DED Data Challenge, Zenodo 21285367](https://zenodo.org/records/21285367) | Height estimator check for the DED modules | Thermal camera 50 fps; profilometer height maps; single tracks | ~668 MB, CC BY 4.0 | Single tracks, not walls |
| Later (DED) | [Chen LDED audio-visual, Zenodo 12604782](https://zenodo.org/records/12604782) | Camera vs mic classification only | Mic 44.1 kHz; coaxial CCD 30 Hz; one wall | 671 MB, CC BY 4.0 | No height or temperature truth; one build |

## Tools for reading

- STL: `trimesh` or `numpy-stl`. VTK: `pyvista` or `vtk`. MKV: `opencv-python` (optional for stop 0).
- PIONEER's recommended viewers: FreeCAD 1.0.2 (STEP, STL), ParaView 5.12.1 with the VMAP plugin (VMAP, VTK), VLC (MKV).
