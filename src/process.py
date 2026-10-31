"""
waam process module. one-segment deposition from (wfs, ts, standoff, T).

physics:
  area from mass conservation, A = eta * A_wire * WFS / TS
  width scales with travel speed and part temperature (hot layers run wider)
  height = area / (shape_factor * width)
"""

import math


WIRE_D = 1.2             # mm, ER70S6 wire typical
ETA_DEP = 0.98
A_WIRE = math.pi * (WIRE_D / 2) ** 2

# reference op point for the width scaling. T_REF is room temp so cold builds
# are at the reference width, and width only grows above it
TS_REF = 5.0             # mm/s
WIDTH_REF = 8.0          # mm
T_REF = 25.0             # C

SHAPE = 2 / 3            # parabolic cap
FW_SLOPE = 0.0023        # fractional width gain per deg C above T_REF

# standoff is a state. the arc stays stable within +/- S_UNSTABLE/2 of nominal
S_NOM = 15.0             # mm
S_UNSTABLE = 10.0


def bead_area(wfs, ts):
    return ETA_DEP * A_WIRE * wfs / ts


def bead_width(ts, T):
    # hot layers spread. width scaling with ts follows laser-cladding form,
    # see Bax et al / RPI power law. clamp at T_REF so cold builds don't go
    # narrower than reference
    base = WIDTH_REF * (ts / TS_REF) ** -0.5
    T_eff = max(T, T_REF)
    return base * (1.0 + FW_SLOPE * (T_eff - T_REF))


def bead_height(area, width):
    return area / (SHAPE * width)


def regime(standoff):
    err = abs(standoff - S_NOM)
    if err < S_UNSTABLE * 0.5:
        return "stable"
    if err < S_UNSTABLE:
        return "unstable"
    return "fault"


def deposit(wfs, ts, standoff, T, shape=None):
    """one bead segment. returns area, width, height, regime.
    shape overrides the module default (used by the sealed-generator check)"""
    a = bead_area(wfs, ts)
    w = bead_width(ts, T)
    s = SHAPE if shape is None else shape
    h = a / (s * w)
    return a, w, h, regime(standoff)
