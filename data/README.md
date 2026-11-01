# Optional PIONEER data

The simulated experiments run without external data. The exploratory probe
uses [PIONEER WAAM, Zenodo record 17608626](https://zenodo.org/records/17608626),
released under CC BY 4.0. Download the production-monitoring and metrology ZIPs
from the record; the downloaded data are not redistributed here.

Extract the relevant files into:

```text
data/pioneer_17608626/extracted/
  vtk/
    combined_file.vtk
    05_CombinedFile_30.vtk
    05_CombinedFile_60.vtk
    05_CombinedFile_90.vtk
    05_CombinedFile_120.vtk
    05_CombinedFile_240.vtk
  stl/
    M1_0_Free.stl
    M1_30_Free.stl
    M1_60_Free.stl
    M1_120_Free.stl
    M1_240_Free.stl
```

Install `requirements-data.txt`, then run `python src/probe_pioneer.py`.
The probe reads directly logged layer labels; it does not invent labels where
they are missing. It plots channel peaks per layer, not temperature immediately
before deposition. Final scan Z coordinates are displayed without assuming a
verified substrate datum or per-layer height truth.

The JSON report lists missing channels/files and the number of usable series.
A completed probe means data were inspected; it does not imply calibration or
that the original data requirements passed.

Layer labels in the VTK files have small floating-point rounding errors. The
probe rounds values within 0.001 of an integer; the resulting 32 positive labels
are reported as logged labels, without assuming that each is a deposited bead.
