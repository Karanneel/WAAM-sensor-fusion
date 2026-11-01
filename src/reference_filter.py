"""EKF reference with the nominal nonlinear CTWD curve.

It knows the chosen variant settings, but not sampled build parameters or
sensor drift. It is a comparison model, not a statistical error bound.
"""

from ekf import EKF, KFParams
from sensors import CTWD_NOMINAL, CTWD_NOISE_SIGMA


class ReferenceEKF(EKF):
    def __init__(self, ctwd_quad=0.005, variant=False):
        p = KFParams(shape=0.75 if variant else 2/3,
                     cooling_exponent=0.85 if variant else 1.0)
        super().__init__(params=p)
        self.ctwd_quad = ctwd_quad
        self.ctwd_offset = 0.5 if variant else 0.0
        self.R_ctwd = CTWD_NOISE_SIGMA**2

    def _update_ctwd(self, z):
        error = self.x[1]-CTWD_NOMINAL
        predicted = CTWD_NOMINAL+error+self.ctwd_quad*error**2+self.ctwd_offset
        slope = 1+2*self.ctwd_quad*error
        self._update_scalar(z-predicted, [0, slope, 0, 0, 0], self.R_ctwd)
