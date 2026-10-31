"""
stop B / Q3: exact Shapley values and error-vs-cost Pareto front.
output: reports/stopB/pareto_front.png
"""

import io
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from simulator import run_build, WFS_CMD, TS_CMD
from sensors import SensorState, observe
from ekf import EKF
from harness import run_closed_loop
from learned import train_models, Learned, _features, _blank_obs, OUTPUTS

ALL_SENSORS = ["scanner", "pyro", "ctwd"]
STATE_NAMES = ["H", "standoff", "T"]
OUT = Path(__file__).resolve().parents[1] / "reports" / "stopB"

# scanner is most expensive, ctwd is cheap (existing arc channel)
SENSOR_COST = {"scanner": 5.0, "pyro": 2.0, "ctwd": 1.0}


def subset_cost(subset):
    return sum(SENSOR_COST[s] for s in subset)


def subset_label(s):
    if not s:
        return "none"
    short = {"scanner": "scan", "pyro": "pyro", "ctwd": "ctwd"}
    return "+".join(short[k] for k in ALL_SENSORS if k in s)


def sensor_subsets():
    subs = []
    for r in range(len(ALL_SENSORS) + 1):
        for combo in itertools.combinations(ALL_SENSORS, r):
            subs.append(set(combo))
    return subs


def _mask_obs(obs, subset):
    masked = dict(obs)
    if "scanner" not in subset:
        masked["scanner"] = None
    if "pyro" not in subset:
        masked["pyro"] = 0.0
    if "ctwd" not in subset:
        masked["ctwd"] = 0.0
    return masked


def _collect_training_data_subset(subset, builds, n_layers=31, dwell=60):
    """collect GBR training data with obs masked to this subset"""
    X_rows = []
    Y = {k: [] for k in OUTPUTS}
    for dw, seed in builds:
        ekf_builder = lambda: EKF()
        rows, _, _, _, obs_list = run_closed_loop(
            n_layers, dw, seed, estimator_builder=ekf_builder)
        prev_obs = _blank_obs()
        for r, o in zip(rows, obs_list):
            masked = _mask_obs(o, subset)
            X_rows.append(_features(masked, _mask_obs(prev_obs, subset), dw, r["layer"]))
            Y["H"].append(r["H_out"])
            Y["standoff"].append(r["standoff"])
            Y["T"].append(r["T_out"])
            prev_obs = o
    return np.array(X_rows), {k: np.array(v) for k, v in Y.items()}


def train_subset_learned(subset, builds=None):
    from sklearn.ensemble import GradientBoostingRegressor
    if builds is None:
        builds = [(60, s) for s in range(8)]
    X, Y = _collect_training_data_subset(subset, builds)
    models = {}
    for k in OUTPUTS:
        m = GradientBoostingRegressor(
            n_estimators=120, max_depth=4, learning_rate=0.08, random_state=0)
        m.fit(X, Y[k])
        models[k] = m
    return models


class LearnedSubset:
    """learned estimator that masks obs to match a subset"""
    def __init__(self, models, subset):
        self.models = models
        self.subset = subset
        self.prev_obs = _blank_obs()
        self.layer = 0

    def update(self, obs, control):
        self.layer += 1
        dwell = control.get("dwell", 0.0)
        masked = _mask_obs(obs, self.subset)
        prev_masked = _mask_obs(self.prev_obs, self.subset)
        feats = _features(masked, prev_masked, dwell, self.layer).reshape(1, -1)
        out = {k: float(m.predict(feats)[0]) for k, m in self.models.items()}
        self.prev_obs = obs
        return out


def composite_rmse(rmse_dict):
    """normalize H/1mm, s/1mm, T/10C then combine"""
    return np.sqrt((rmse_dict["H"] / 1.0) ** 2 +
                   (rmse_dict["standoff"] / 1.0) ** 2 +
                   (rmse_dict["T"] / 10.0) ** 2)


def _run_ekf_subset_manual(subset, n_seeds=10, n_layers=31, dwell=60,
                           error_type="fw", error_level=0.30):
    """closed-loop EKF with planted error to break model-match circularity"""
    from process import S_NOM
    from simulator import T_AMB, START_Z, thermal_update
    from process import deposit
    from ekf import KFParams

    NOMINAL_GROWTH = 1.8
    R_Z_MIN, R_Z_MAX = 0.5, 3.5
    wfs, ts = 70, 10

    # plant error so EKF model doesn't match sim
    p = KFParams()
    if error_type == "fw":
        p.fw_slope *= (1.0 + error_level)
    elif error_type == "tau":
        p.tau_base *= (1.0 + error_level)

    errs = {k: [] for k in STATE_NAMES}
    for seed in range(n_seeds):
        rng = np.random.default_rng(seed)
        sens_rng = np.random.default_rng(seed + 1000)
        sens_state = SensorState(sens_rng)
        ekf = EKF(params=p)

        H, Z, T, prev_H = 0.0, START_Z, T_AMB, 0.0
        r_z_next = NOMINAL_GROWTH

        for k in range(1, n_layers + 1):
            standoff = Z - H
            area, width, height, regime = deposit(wfs, ts, standoff, T)
            spatter = rng.random() < 0.02
            H_out = H + height
            T_out = thermal_update(T, H_out, dwell, ts)

            row = {"layer": k, "H_in": H, "Z": Z, "standoff": standoff,
                   "T_in": T, "T_out": T_out, "area": area, "width": width,
                   "height": height, "regime": regime, "spatter": spatter,
                   "H_out": H_out}

            obs = observe(row, prev_H, sens_state)
            ctrl = {"wfs": wfs, "ts": ts, "r_z": r_z_next, "dwell": dwell}
            est = ekf.update(obs, ctrl,
                             active_sensors=subset if subset else set())

            errs["H"].append((est["H"] - H_out) ** 2)
            errs["standoff"].append((est["standoff"] - standoff) ** 2)
            errs["T"].append((est["T"] - T_out) ** 2)

            s_err = S_NOM - est["standoff"]
            r_z_next = NOMINAL_GROWTH + 1.0 * s_err
            r_z_next = max(R_Z_MIN, min(R_Z_MAX, r_z_next))

            H, Z, T, prev_H = H_out, Z + r_z_next, T_out, H_out

    return {k: float(np.sqrt(np.mean(v))) for k, v in errs.items()}


def _run_learned_subset_manual(subset, models, n_seeds=10, n_layers=31, dwell=60):
    """closed-loop with retrained learned model, no planted error needed"""
    from process import S_NOM
    from simulator import T_AMB, START_Z, thermal_update
    from process import deposit

    NOMINAL_GROWTH = 1.8
    R_Z_MIN, R_Z_MAX = 0.5, 3.5
    wfs, ts = 70, 10

    errs = {k: [] for k in STATE_NAMES}
    for seed in range(n_seeds):
        rng = np.random.default_rng(seed)
        sens_rng = np.random.default_rng(seed + 1000)
        sens_state = SensorState(sens_rng)
        est_obj = LearnedSubset(models, subset)

        H, Z, T, prev_H = 0.0, START_Z, T_AMB, 0.0
        r_z_next = NOMINAL_GROWTH

        for k in range(1, n_layers + 1):
            standoff = Z - H
            area, width, height, regime = deposit(wfs, ts, standoff, T)
            spatter = rng.random() < 0.02
            H_out = H + height
            T_out = thermal_update(T, H_out, dwell, ts)

            row = {"layer": k, "H_in": H, "Z": Z, "standoff": standoff,
                   "T_in": T, "T_out": T_out, "area": area, "width": width,
                   "height": height, "regime": regime, "spatter": spatter,
                   "H_out": H_out}

            obs = observe(row, prev_H, sens_state)
            ctrl = {"wfs": wfs, "ts": ts, "r_z": r_z_next, "dwell": dwell}
            out = est_obj.update(obs, ctrl)

            errs["H"].append((out["H"] - H_out) ** 2)
            errs["standoff"].append((out["standoff"] - standoff) ** 2)
            errs["T"].append((out["T"] - T_out) ** 2)

            s_err = S_NOM - out["standoff"]
            r_z_next = NOMINAL_GROWTH + 1.0 * s_err
            r_z_next = max(R_Z_MIN, min(R_Z_MAX, r_z_next))

            H, Z, T, prev_H = H_out, Z + r_z_next, T_out, H_out

    return {k: float(np.sqrt(np.mean(v))) for k, v in errs.items()}


def compute_all_subsets(error_type="fw", error_level=0.30):
    subsets = sensor_subsets()
    results = {}
    for s in subsets:
        lab = subset_label(s)
        print(f"  subset: {lab}")

        ekf_rmse = _run_ekf_subset_manual(s, error_type=error_type,
                                          error_level=error_level)

        if s:
            models = train_subset_learned(s)
            learned_rmse = _run_learned_subset_manual(s, models)
        else:
            learned_rmse = None

        best_rmse = {}
        for k in STATE_NAMES:
            if s and learned_rmse:
                best_rmse[k] = min(ekf_rmse[k], learned_rmse[k])
            else:
                best_rmse[k] = ekf_rmse[k]

        results[lab] = {
            "ekf_rmse": ekf_rmse,
            "learned_rmse": learned_rmse,
            "best_rmse": best_rmse,
            "composite": composite_rmse(best_rmse),
            "cost": subset_cost(s),
            "subset": s,
        }
    return results


def compute_multi_error_sweep(error_configs=None):
    """run Shapley across multiple planted error types, check ranking robustness"""
    if error_configs is None:
        error_configs = [("fw", 0.30), ("tau", 0.30)]

    all_results = {}
    all_shapley = {}
    for etype, elevel in error_configs:
        tag = f"{etype}_{elevel}"
        print(f"\n--- error config: {tag} ---")
        res = compute_all_subsets(error_type=etype, error_level=elevel)
        shap = exact_shapley(res)
        all_results[tag] = res
        all_shapley[tag] = shap
        print(f"  Shapley: " + ", ".join(f"{s}={v:.3f}" for s, v in shap.items()))

    # average composite across error configs
    tags = list(all_results.keys())
    first = all_results[tags[0]]
    avg_results = {}
    for lab in first:
        avg_comp = np.mean([all_results[t][lab]["composite"] for t in tags])
        avg_best = {}
        for k in STATE_NAMES:
            avg_best[k] = np.mean([all_results[t][lab]["best_rmse"][k] for t in tags])
        avg_results[lab] = {
            "best_rmse": avg_best,
            "composite": float(avg_comp),
            "cost": first[lab]["cost"],
            "subset": first[lab]["subset"],
        }

    avg_shapley = exact_shapley(avg_results)

    return {
        "per_config": all_results,
        "per_config_shapley": all_shapley,
        "averaged": avg_results,
        "averaged_shapley": avg_shapley,
        "configs": error_configs,
    }


def exact_shapley(results):
    """v(S) = -composite_rmse(S), exact over 3! permutations"""
    def v(subset):
        return -results[subset_label(subset)]["composite"]

    shapley = {}
    n = len(ALL_SENSORS)
    for sensor in ALL_SENSORS:
        sv = 0.0
        others = [s for s in ALL_SENSORS if s != sensor]
        for r in range(len(others) + 1):
            for combo in itertools.combinations(others, r):
                S = set(combo)
                marginal = v(S | {sensor}) - v(S)
                weight = (math.factorial(len(S)) *
                          math.factorial(n - len(S) - 1) /
                          math.factorial(n))
                sv += weight * marginal
        shapley[sensor] = sv
    return shapley


def is_pareto(costs, errors):
    n = len(costs)
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if costs[j] <= costs[i] and errors[j] <= errors[i]:
                if costs[j] < costs[i] or errors[j] < errors[i]:
                    mask[i] = False
                    break
    return mask


def plot_pareto(results, shapley, save_path=None):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    labels = list(results.keys())
    costs = np.array([results[l]["cost"] for l in labels])
    comp = np.array([results[l]["composite"] for l in labels])

    ax1.scatter(costs, comp, s=80, zorder=3, c="steelblue", edgecolors="k", lw=0.5)
    for i, lab in enumerate(labels):
        ax1.annotate(lab, (costs[i], comp[i]),
                     textcoords="offset points", xytext=(5, 5), fontsize=7.5)

    pareto = is_pareto(costs, comp)
    p_idx = np.where(pareto)[0]
    p_sorted = p_idx[np.argsort(costs[p_idx])]
    ax1.plot(costs[p_sorted], comp[p_sorted], "r--", lw=1.5, alpha=0.7,
             label="Pareto front")
    ax1.scatter(costs[p_sorted], comp[p_sorted], s=100, facecolors="none",
                edgecolors="red", lw=2, zorder=4)

    ax1.set_xlabel("sensor cost (relative units)")
    ax1.set_ylabel("composite RMSE (normalized)")
    ax1.set_title("error vs cost Pareto front")
    ax1.legend()
    ax1.grid(alpha=0.3)

    sensors = list(shapley.keys())
    vals = [shapley[s] for s in sensors]
    colors = ["#4c72b0", "#dd8452", "#55a868"]
    ax2.barh(sensors, vals, color=colors, edgecolor="k", lw=0.5)
    ax2.set_xlabel("Shapley value (negative RMSE units)")
    ax2.set_title("exact Shapley value per sensor")
    ax2.grid(alpha=0.3, axis="x")
    for i, v in enumerate(vals):
        ax2.text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=9)

    fig.tight_layout()

    if save_path is None:
        OUT.mkdir(parents=True, exist_ok=True)
        save_path = OUT / "pareto_front.png"

    buf = io.BytesIO()
    fig.savefig(buf, dpi=160, format="png")
    plt.close(fig)
    Path(save_path).write_bytes(buf.getvalue())
    return save_path


def plot_pareto_sweep(sweep, save_path=None):
    """pareto from averaged results + grouped bar comparing Shapley across error types"""
    avg = sweep["averaged"]
    avg_shap = sweep["averaged_shapley"]
    per_shap = sweep["per_config_shapley"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # left: pareto from averaged composite
    labels = list(avg.keys())
    costs = np.array([avg[l]["cost"] for l in labels])
    comp = np.array([avg[l]["composite"] for l in labels])

    ax1.scatter(costs, comp, s=80, zorder=3, c="steelblue", edgecolors="k", lw=0.5)
    for i, lab in enumerate(labels):
        ax1.annotate(lab, (costs[i], comp[i]),
                     textcoords="offset points", xytext=(5, 5), fontsize=7.5)

    pareto = is_pareto(costs, comp)
    p_idx = np.where(pareto)[0]
    p_sorted = p_idx[np.argsort(costs[p_idx])]
    ax1.plot(costs[p_sorted], comp[p_sorted], "r--", lw=1.5, alpha=0.7,
             label="Pareto front (averaged)")
    ax1.scatter(costs[p_sorted], comp[p_sorted], s=100, facecolors="none",
                edgecolors="red", lw=2, zorder=4)

    ax1.set_xlabel("sensor cost (relative units)")
    ax1.set_ylabel("composite RMSE (averaged across error types)")
    ax1.set_title("error vs cost Pareto front (multi-error avg)")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # right: grouped bar of Shapley per error config + average
    sensors = list(avg_shap.keys())
    tags = list(per_shap.keys())
    n_groups = len(tags) + 1  # per-config + avg
    bar_w = 0.8 / n_groups
    y_pos = np.arange(len(sensors))

    config_colors = ["#7faadb", "#f4a582"]
    for gi, tag in enumerate(tags):
        vals = [per_shap[tag][s] for s in sensors]
        ax2.barh(y_pos + gi * bar_w, vals, height=bar_w, label=tag,
                 color=config_colors[gi % len(config_colors)],
                 edgecolor="k", lw=0.5)
    # avg bar
    avg_vals = [avg_shap[s] for s in sensors]
    ax2.barh(y_pos + len(tags) * bar_w, avg_vals, height=bar_w, label="averaged",
             color="#2d2d2d", edgecolor="k", lw=0.5)
    for i, v in enumerate(avg_vals):
        ax2.text(v + 0.005, y_pos[i] + len(tags) * bar_w, f"{v:.3f}",
                 va="center", fontsize=8)

    ax2.set_yticks(y_pos + bar_w * n_groups / 2 - bar_w / 2)
    ax2.set_yticklabels(sensors)
    ax2.set_xlabel("Shapley value (negative RMSE units)")
    ax2.set_title("Shapley robustness across error types")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, axis="x")

    fig.tight_layout()

    if save_path is None:
        OUT.mkdir(parents=True, exist_ok=True)
        save_path = OUT / "pareto_front.png"

    buf = io.BytesIO()
    fig.savefig(buf, dpi=160, format="png")
    plt.close(fig)
    Path(save_path).write_bytes(buf.getvalue())
    return save_path


def summary_table(results, shapley):
    print(f"\n{'subset':<20} {'cost':>5} {'H':>8} {'s':>8} {'T':>8} {'comp':>8}")
    print("-" * 60)
    for lab in results:
        r = results[lab]
        rm = r["best_rmse"]
        print(f"{lab:<20} {r['cost']:5.1f} {rm['H']:8.3f} {rm['standoff']:8.3f} "
              f"{rm['T']:8.1f} {r['composite']:8.3f}")
    print(f"\nShapley values:")
    for s, v in shapley.items():
        print(f"  {s}: {v:.4f}")


if __name__ == "__main__":
    print("computing RMSE per sensor subset...")
    results = compute_all_subsets()
    shapley = exact_shapley(results)
    summary_table(results, shapley)
    p = plot_pareto(results, shapley)
    print(f"\nfigure: {p}")
