"""Single-bead geometry. Lengths are in mm and speeds in mm/s."""

from dataclasses import dataclass
import math
import numpy as np

WIRE_D = 1.2
ETA_DEP = 0.98
A_WIRE = math.pi * (WIRE_D / 2) ** 2
TS_REF = 5.0
WIDTH_REF = 8.0
T_REF = 25.0
SHAPE = 2 / 3
FW_SLOPE = 0.0023
S_NOM = 15.0
S_UNSTABLE = 10.0


@dataclass(frozen=True)
class BuildParameters:
    """Truth parameters, sampled once per build; never passed to an estimator."""
    width_ref: float = WIDTH_REF
    fw_slope: float = FW_SLOPE
    eta_dep: float = ETA_DEP
    shape: float = SHAPE
    tau_base: float = 30.0
    tau_growth: float = 5.0
    heat_increment: float = 100.0
    cooling_exponent: float = 1.0


def sample_build_parameters(seed, varied=True, variant=False):
    # These ranges are sensitivity assumptions, not fitted manufacturing tolerances.
    rng = np.random.default_rng(np.random.SeedSequence([seed, 2000]))
    spread = 0.05 if varied else 0.0
    width, slope, tau, growth, heat = rng.uniform(1-spread, 1+spread, 5)
    return BuildParameters(width_ref=WIDTH_REF*width, fw_slope=FW_SLOPE*slope,
                           tau_base=30*tau, tau_growth=5*growth,
                           heat_increment=100*heat,
                           shape=0.75 if variant else SHAPE,
                           cooling_exponent=0.85 if variant else 1.0)


def bead_area(wfs, ts):
    return ETA_DEP * A_WIRE * wfs / ts


def bead_width(ts, T):
    return WIDTH_REF * (ts / TS_REF) ** -0.5 * (1 + FW_SLOPE * max(T-T_REF, 0))


def bead_height(area, width):
    return area / (SHAPE * width)


def regime(standoff):
    error = abs(standoff-S_NOM)
    return 'stable' if error < S_UNSTABLE/2 else 'unstable' if error < S_UNSTABLE else 'fault'


def deposit(wfs, ts, standoff, T, shape=None, params=None):
    p = params or BuildParameters()
    area = p.eta_dep * A_WIRE * wfs / ts
    width = p.width_ref * (ts / TS_REF) ** -0.5 * (1 + p.fw_slope * max(T-T_REF, 0))
    height = area / ((p.shape if shape is None else shape) * width)
    # The regime is diagnostic only. Arc faults do not alter deposited mass here.
    return area, width, height, regime(standoff)
