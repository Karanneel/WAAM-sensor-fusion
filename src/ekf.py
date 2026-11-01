"""Extended Kalman filter for end-of-deposition height, standoff and temperature.

The last two states track multiplicative pyrometer bias and the previous
height, needed for the scanner's one-layer delay. All speeds use mm/s.
"""

from dataclasses import dataclass
import math
import numpy as np

from sensors import (SCANNER_SIGMA, PYRO_NOISE_SIGMA, CTWD_NOISE_SIGMA,
                     CTWD_NOMINAL)


@dataclass
class KFParams:
    """Nominal process parameters assumed by the filter."""
    width_ref: float = 8.0
    ts_ref: float = 5.0
    fw_slope: float = 0.0023
    t_ref: float = 25.0
    shape: float = 2 / 3
    wire_area: float = math.pi * (1.2 / 2) ** 2
    eta_dep: float = 0.98
    tau_base: float = 30.0
    tau_growth: float = 5.0
    dt_layer: float = 100.0
    h_mass: float = 15.0
    t_amb: float = 25.0
    wall_length: float = 150.0
    cooling_exponent: float = 1.0


def _bead_width(ts, T, p):
    base = p.width_ref * (ts / p.ts_ref) ** -0.5
    T_eff = max(T, p.t_ref)
    return base * (1.0 + p.fw_slope * (T_eff - p.t_ref))


def _bead_height(wfs, ts, T, p):
    area = p.eta_dep * p.wire_area * wfs / ts
    w = _bead_width(ts, T, p)
    return area / (p.shape * w)


def _dh_dT(wfs, ts, T, p):
    """derivative of bead height wrt T at current T. zero below t_ref"""
    if T < p.t_ref:
        return 0.0
    area = p.eta_dep * p.wire_area * wfs / ts
    base = p.width_ref * (ts / p.ts_ref) ** -0.5
    w = base * (1.0 + p.fw_slope * (T - p.t_ref))
    dw_dT = base * p.fw_slope
    h = area / (p.shape * w)
    return -h * dw_dT / w


def _thermal_predict(T, H, dwell, ts, p):
    tau = p.tau_base + p.tau_growth*H
    elapsed = p.wall_length/ts + dwell
    heat = p.dt_layer/(1+H/p.h_mass)
    return p.t_amb + (T+heat-p.t_amb)*math.exp(-(elapsed/tau)**p.cooling_exponent)


def _thermal_derivatives(T, H, dwell, ts, p):
    tau = p.tau_base+p.tau_growth*H
    elapsed = p.wall_length/ts+dwell
    power = (elapsed/tau)**p.cooling_exponent
    decay = math.exp(-power)
    heat = p.dt_layer/(1+H/p.h_mass)
    heat_slope = -p.dt_layer/p.h_mass/(1+H/p.h_mass)**2
    dH = decay*(heat_slope+(T+heat-p.t_amb)*p.cooling_exponent*power*p.tau_growth/tau)
    return dH, decay


class EKF:
    """Predict with the applied controls, then assimilate layer-end measurements."""

    def __init__(self, H0=0.0, standoff0=CTWD_NOMINAL, T0=25.0, bias0=1.0,
                 params=None):
        self.p = params or KFParams()
        self.x = np.array([H0, standoff0, T0, bias0, 0.0])
        self.P = np.diag([0.5 ** 2, 1.0 ** 2, 50.0 ** 2, 0.1 ** 2, 0.5 ** 2])
        self.Q = np.diag([0.1 ** 2, 0.3 ** 2, 20.0 ** 2, 0.01 ** 2, 0.1 ** 2])
        self.R_scanner = SCANNER_SIGMA ** 2
        self.R_pyro = PYRO_NOISE_SIGMA ** 2
        # inflate R_ctwd to cover the nonlinearity the KF doesn't model
        self.R_ctwd = (CTWD_NOISE_SIGMA * 1.5) ** 2

    def predict(self, control, dwell):
        wfs = control["wfs"]
        ts = control["ts"]
        r_z = control["r_z"]
        H, s, T, b, _ = self.x
        h = _bead_height(wfs, ts, T, self.p)
        H_new = H + h
        s_new = s + r_z - h
        T_new = _thermal_predict(T, H_new, dwell, ts, self.p)
        self.x = np.array([H_new, s_new, T_new, b, H])

        dh_dT = _dh_dT(wfs, ts, T, self.p)
        thermal_H, thermal_T = _thermal_derivatives(T, H_new, dwell, ts, self.p)
        F = np.array([
            [1, 0, dh_dT, 0, 0],
            [0, 1, -dh_dT, 0, 0],
            [thermal_H, 0, thermal_T+thermal_H*dh_dT, 0, 0],
            [0, 0, 0, 1, 0],
            [1, 0, 0, 0, 0],
        ])
        self.P = F @ self.P @ F.T + self.Q

    def _update_scalar(self, innovation, H_row, R):
        H_row = np.asarray(H_row, dtype=float).reshape(1, -1)
        S = (H_row @ self.P @ H_row.T).item() + R
        K = (self.P @ H_row.T).flatten() / S
        self.x = self.x + K * innovation
        residual = np.eye(5)-np.outer(K, H_row.flatten())
        self.P = residual @ self.P @ residual.T + np.outer(K, K)*R
        self.P = (self.P+self.P.T)/2

    def _update_scanner(self, z):
        pred = self.x[4]
        self._update_scalar(z - pred, [0, 0, 0, 0, 1], self.R_scanner)

    def _update_pyro(self, z):
        T_est, b_est = self.x[2], self.x[3]
        pred = b_est * T_est
        self._update_scalar(z - pred, [0, 0, b_est, T_est, 0], self.R_pyro)

    def _update_ctwd(self, z):
        pred = self.x[1]
        self._update_scalar(z - pred, [0, 1, 0, 0, 0], self.R_ctwd)

    def update(self, obs, control, active_sensors=None):
        # active_sensors: subset to use, None = all three
        self.predict(control, dwell=control.get("dwell", 0.0))
        use = active_sensors if active_sensors is not None else {"scanner", "pyro", "ctwd"}
        if "scanner" in use and obs["scanner"] is not None:
            self._update_scanner(obs["scanner"])
        if "pyro" in use:
            self._update_pyro(obs["pyro"])
        if "ctwd" in use:
            self._update_ctwd(obs["ctwd"])
        return {"H": float(self.x[0]),
                "standoff": float(self.x[1]),
                "T": float(self.x[2])}
