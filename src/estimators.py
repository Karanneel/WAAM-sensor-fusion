"""
estimator interface and the naive baseline.

every estimator exposes the same shape:
  est = Estimator(...)
  for each layer:
      state_est = est.update(obs, control)
  where state_est is a dict {H, standoff, T}

obs is one row from sensors.observe(). control is {wfs, ts, r_z} the planner
committed to for this layer. the controller and the harness talk only to this
interface, so swapping estimators is a one-line change

naive baseline: no model, just carry forward the latest sensor reading. this
is what everything else has to beat on the pre-registered core gate
"""

from sensors import CTWD_NOMINAL


# default growth to assume when the scanner is blocked for a layer
NOM_GROWTH = 1.8     # mm, matches the calibrated process at WFS/TS defaults


class Naive:
    """last-reading-forward baseline. no model, no fusion"""

    def __init__(self, H0=0.0, T0=25.0, standoff0=CTWD_NOMINAL):
        self.H = H0
        self.T = T0
        self.standoff = standoff0

    def update(self, obs, control):
        if obs["scanner"] is not None:
            # scanner tells us H the scanner sees (end of previous layer).
            # for an H estimate at end of CURRENT layer, add one nominal growth
            self.H = obs["scanner"] + NOM_GROWTH
        else:
            self.H = self.H + NOM_GROWTH
        self.T = obs["pyro"]
        self.standoff = obs["ctwd"]
        return {"H": self.H, "T": self.T, "standoff": self.standoff}
