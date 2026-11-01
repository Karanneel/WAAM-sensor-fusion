"""Baseline: latest sensor readings plus an assumed 1.8 mm layer increment."""

from sensors import CTWD_NOMINAL
NOM_GROWTH = 1.8


class Naive:
    def __init__(self, H0=0.0, T0=25.0, standoff0=CTWD_NOMINAL):
        self.H, self.T, self.standoff = H0, T0, standoff0

    def update(self, obs, control):
        # The delayed scan sees the previous wall height.
        self.H = (obs['scanner'] if obs['scanner'] is not None else self.H)+NOM_GROWTH
        self.T, self.standoff = obs['pyro'], obs['ctwd']
        return dict(H=self.H, T=self.T, standoff=self.standoff)
