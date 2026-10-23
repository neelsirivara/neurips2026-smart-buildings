"""Run ONE policy on ONE scenario and write a score_leaderboard-compatible summary.json.

Light replacement for the kit's evaluate.py loop (same environment loading,
same tracker, same reward path; skips the matplotlib charts). Output layout
matches the kit so `score_leaderboard.py <results-dir> --policy <name>` works:

    <results-dir>/<building>/<weather>/<policy>/summary.json
    <results-dir>/<building>/<weather>/<policy>/timeseries.csv   (--save-ts)

Usage:
    python run_scenario.py --policy transfer --building building_train_1 \
        --weather atlanta_2 --steps 8640 --results-dir ../results/full \
        [--params-json params.json] [--save-ts] [--policy-file path/to/transfer_policy.py]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]            # smart_buildings/
KIT = ROOT / "kit"
ORIG_CWD = Path(os.getcwd())      # relative CLI paths are resolved against this
sys.path.insert(0, str(KIT))
os.chdir(KIT)                     # the gin configs use kit-relative paths


def _abs(path_str: str | None) -> str | None:
    if path_str is None:
        return None
    p = Path(path_str)
    return str(p if p.is_absolute() else (ORIG_CWD / p).resolve())

import numpy as np  # noqa: E402

from smart_buildings.evaluate import (  # noqa: E402
    POLICY_MAP, create_building_meta_data, load_hybrid_environment, validate_action)
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402


def load_policy_class(policy: str, policy_file: str | None):
    if policy == "transfer":
        path = Path(policy_file) if policy_file else ROOT / "submission" / "transfer_policy.py"
        spec = importlib.util.spec_from_file_location("sadr_transfer_policy", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TransferPolicy
    return POLICY_MAP[policy]


def params_hash(params_json: str | None) -> str:
    if not params_json:
        return "default"
    return hashlib.md5(Path(params_json).read_bytes()).hexdigest()[:10]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--building", required=True)
    ap.add_argument("--weather", required=True)
    ap.add_argument("--steps", type=int, default=8640)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--scenarios-dir", default=str(KIT / "smart_buildings" / "training_scenarios"))
    ap.add_argument("--params-json", default=None)
    ap.add_argument("--policy-file", default=None)
    ap.add_argument("--save-ts", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    a.policy_file = _abs(a.policy_file)
    a.params_json = _abs(a.params_json)
    a.scenarios_dir = _abs(a.scenarios_dir)

    results_dir = Path(a.results_dir)
    if not results_dir.is_absolute():
        results_dir = (HERE / a.results_dir).resolve()
    scen_dir = Path(a.scenarios_dir) / a.building / a.weather
    gin_path = scen_dir / "config.gin"
    if not gin_path.exists():
        print(f"missing {gin_path}", file=sys.stderr)
        return 2

    out_dir = results_dir / a.building / a.weather / a.policy
    out_dir.mkdir(parents=True, exist_ok=True)
    summ_path = out_dir / "summary.json"
    phash = params_hash(a.params_json)
    if summ_path.exists() and not a.force:
        try:
            old = json.loads(summ_path.read_text())
            if old.get("total_steps") == a.steps and old.get("params_hash") == phash:
                print(f"skip (done): {a.building}/{a.weather}/{a.policy} {old['total_reward']:.2f}")
                return 0
        except (OSError, ValueError):
            pass

    if a.params_json:
        os.environ["SADR_PARAMS_JSON"] = str(Path(a.params_json).resolve())

    t_load = time.time()
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    tracker = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
    md = create_building_meta_data(env, scen_dir)
    spec = env.action_spec()
    pol_cls = load_policy_class(a.policy, a.policy_file)
    policy = pol_cls(md, spec)
    load_s = time.time() - t_load

    tracker.reset()
    obs = tracker.last_obs
    t0 = time.time()
    pol_time = 0.0
    n = 0
    for _ in range(a.steps):
        tp = time.time()
        act = validate_action(policy.get_action(obs), spec)
        pol_time += time.time() - tp
        obs, _, term, trunc, _ = tracker.step(act)
        n += 1
        if term or trunc:
            break
    wall = time.time() - t0

    rewards = np.asarray(tracker.rewards, dtype=float)
    rc = tracker.reward_components
    occ = np.asarray(tracker.occupancy, dtype=float)
    zt = np.asarray(tracker.zone_temps, dtype=float)

    def tot(key):
        return float(sum(r.get(key, 0.0) for r in rc))

    summary = {
        "policy": a.policy,
        "building": a.building,
        "weather": a.weather,
        "station": a.weather.rsplit("_", 1)[0],
        "total_reward": float(rewards.sum()),
        "total_steps": int(len(rewards)),
        "avg_reward": float(rewards.mean()) if len(rewards) else 0.0,
        "avg_occupancy": float(occ.mean()) if len(occ) else 0.0,
        "avg_zone_temp": float(zt.mean()) if zt.size else 0.0,
        "productivity_weight": float(tracker.productivity_weight),
        "energy_weight": float(tracker.energy_weight),
        "carbon_weight": float(tracker.carbon_weight),
        "total_normalized_productivity_regret": tot("normalized_productivity_regret"),
        "total_normalized_energy_cost": tot("normalized_energy_cost"),
        "total_normalized_carbon_emission": tot("normalized_carbon_emission"),
        "seconds_per_step": wall / max(n, 1),
        "policy_seconds_per_step": pol_time / max(n, 1),
        "env_load_seconds": load_s,
        "n_discrete_action": int(md["n_discrete_action"]),
        "n_continuous_action": int(md["n_continuous_action"]),
        "num_zones": int(len(md["zone_temp_indices"])),
        "num_ahus": int(len(md["ahu_zone_assignments"])),
        "params_hash": phash,
        "params_json": a.params_json,
    }
    # occupied-hours comfort diagnostics
    if zt.size and len(rc):
        occ_mask = occ > 0
        summary["frac_steps_occupied"] = float(occ_mask.mean())
        summary["mean_regret_occupied"] = float(np.mean([
            r.get("normalized_productivity_regret", 0.0) for r, m in zip(rc, occ_mask) if m])) if occ_mask.any() else 0.0
    summ_path.write_text(json.dumps(summary, indent=2))

    if a.save_ts:
        import csv
        with open(out_dir / "timeseries.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "reward", "productivity_regret", "energy_cost", "carbon", "occupancy"]
                       + [f"zone_{i}_temp" for i in range(zt.shape[1] if zt.ndim == 2 else 0)])
            for i in range(len(rewards)):
                row = [tracker.timestamps[i].isoformat(), f"{rewards[i]:.6f}",
                       f"{rc[i].get('normalized_productivity_regret', 0.0):.6f}",
                       f"{rc[i].get('normalized_energy_cost', 0.0):.6f}",
                       f"{rc[i].get('normalized_carbon_emission', 0.0):.6f}",
                       f"{occ[i]:.2f}"]
                if zt.ndim == 2:
                    row += [f"{v:.3f}" for v in zt[i]]
                w.writerow(row)
        # per-step AHU log (plant commands actually taken) is large; keep it only for the paper trace
        if tracker.ahu_log:
            import pandas as pd
            pd.DataFrame(tracker.ahu_log).to_csv(out_dir / "ahu_log.csv", index=False)

    print(f"{a.building}/{a.weather}/{a.policy}: total={summary['total_reward']:.2f} "
          f"steps={n} sec/step={summary['seconds_per_step']:.3f} "
          f"(policy {summary['policy_seconds_per_step']*1000:.2f} ms) "
          f"regret={summary['total_normalized_productivity_regret']:.2f} "
          f"energy={summary['total_normalized_energy_cost']:.2f} carbon={summary['total_normalized_carbon_emission']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
