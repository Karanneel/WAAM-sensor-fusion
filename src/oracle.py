"""
oracle estimator for the stop-A sweep.

the oracle is an EKF given the TRUE process params and a measurement model
that matches the truth sensor exactly. so it sees the same noisy obs as the
other estimators but with no planted error and the correct CTWD nonlinearity

this sets the achievable floor. compare EKF with planted error to oracle to
see how much is left on the table at each error level
"""

import math
import numpy as np

from ekf import EKF, KFParams, _bead_height, _thermal_predict, _dh_dT
from sensors import SCANNER_SIGMA, PYRO_NOISE_SIGMA, CTWD_NOISE_SIGMA, CTWD_NOMINAL


class Oracle(EKF):
    """EKF with correct physics params AND the correct nonlinear CTWD map.
    everything else matches EKF so the comparison is apples to apples"""

    def __init__(self, H0=0.0, standoff0=CTWD_NOMINAL, T0=25.0, bias0=1.0,
                 ctwd_quad=0.005):
        # start from truth KFParams, nothing perturbed
        super().__init__(H0=H0, standoff0=standoff0, T0=T0, bias0=bias0,
                         params=KFParams())
        self.ctwd_quad = ctwd_quad
        # match the sensor model exactly: no inflation
        self.R_ctwd = CTWD_NOISE_SIGMA ** 2

    def _update_ctwd(self, z):
        # invert the true nonlinear map rather than using a linear strawman.
        # z = s_nom + (s - s_nom) + quad*(s - s_nom)^2 + bias + noise
        # solve the quadratic for standoff given z and the current ctwd estimate
        s_est = self.x[1]
        err = s_est - CTWD_NOMINAL
        pred = CTWD_NOMINAL + err + self.ctwd_quad * err ** 2
        # linearize around s_est for the measurement Jacobian
        dz_ds = 1.0 + 2.0 * self.ctwd_quad * err
        H_row = [0, dz_ds, 0, 0, 0]
        self._update_scalar(z - pred, H_row, self.R_ctwd)
