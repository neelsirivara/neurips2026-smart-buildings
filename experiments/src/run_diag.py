"""Run ONE policy on ONE scenario with per-step diagnostics (round 3).

Same environment loading, tracker and reward path as run_scenario.py, and the same
score_leaderboard-compatible summary.json, plus two diagnostic files:

    <results-dir>/<building>/<weather>/<policy>/diag.csv    one row per step:
        timestamp, reward, regret_n, energy_n, carbon_n, occupancy, oat_k,
        blower_w, cool_w, pump_w, gas_w (plant energy rates read from the RewardInfo),
        elec_cost_usd, gas_cost_usd, carbon_kg, mode (policy mode if exposed, else -1),
        n_ahu_on, sum_flow_m3s, max_p_pa, min_sat_k, hw_t_k, hw_dp_bar, pump_on
    <results-dir>/<building>/<weather>/<policy>/timeseries.csv  as run_scenario.py --save-ts
    <results-dir>/<building>/<weather>/<policy>/zones.npz  per-step arrays:
        zone_t (steps x V, K), zone_occ (steps x V), damper (steps x V), valve (steps x V),
        ahu_run (steps x K), ahu_p (Pa), ahu_sat (K), ahu_recirc, ahu_flow (m3/s, after the step),
        vav_ids (V,), ahu_of_zone (V,), zone_area_m2 (V,)

Skips scenarios already done at the same step count / parameter hash (resumable).

Usage:
    python run_diag.py --policy transfer --building building_train_1 --weather fairbanks_1 \
        --steps 8640 --results-dir ../results/round3/diag_v5 [--policy-file ...] [--params-json ...]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = Path(os.environ["SB_KIT_DIR"]) if os.environ.get("SB_KIT_DIR") else ROOT / "kit"   # round 5: kit copy (PR #2 check)
ORIG_CWD = Path(os.getcwd())
sys.path.insert(0, str(KIT))
os.chdir(KIT)


def _abs(path_str):
    if path_str is None:
        return None
    p = Path(path_str)
    return str(p if p.is_absolute() else (ORIG_CWD / p).resolve())


import numpy as np  # noqa: E402

from smart_buildings.evaluate import (  # noqa: E402
    POLICY_MAP, create_building_meta_data, load_hybrid_environment, validate_action)
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402


def load_policy_class(policy, policy_file):
    if policy == "transfer":
        path = Path(policy_file) if policy_file else ROOT / "submission" / "transfer_policy.py"
        spec = importlib.util.spec_from_file_location("sadr_transfer_policy_diag", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TransferPolicy
    return POLICY_MAP[policy]


def params_hash(params_json):
    if not params_json:
        return "default"
    return hashlib.md5(Path(params_json).read_bytes()).hexdigest()[:10]


def zone_areas(zone_map, vav_ids):
    """Floor area (m2) per VAV from the metadata zone map (4-connected rooms in raster order)."""
    if zone_map is None:
        return np.full(len(vav_ids), np.nan)
    zm = np.asarray(zone_map)
    H, W = zm.shape
    free = zm == 0
    lab = np.zeros((H, W), dtype=np.int32)
    n = 0
    rows, cols = np.nonzero(free)
    for r0, c0 in zip(rows, cols):
        if lab[r0, c0]:
            continue
        n += 1
        lab[r0, c0] = n
        dq = deque([(r0, c0)])
        while dq:
            r, c = dq.popleft()
            for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= rr < H and 0 <= cc < W and free[rr, cc] and not lab[rr, cc]:
                    lab[rr, cc] = n
                    dq.append((rr, cc))
    counts = np.bincount(lab.ravel(), minlength=n + 1)
    out = np.full(len(vav_ids), np.nan)
    for i, v in enumerate(vav_ids):
        try:
            k = int(v.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            continue
        if 1 <= k <= n:
            out[i] = counts[k] * 0.04
    return out


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
    if summ_path.exists() and (out_dir / "diag.csv").exists() and not a.force:
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

    # ---- index maps for decoding the action vector ----
    ahus = tracker.ahus
    K = len(ahus)
    vav_ids = list(tracker.vavs.keys())          # zone order of tracker.zone_temps
    V = len(vav_ids)
    temp_idx = list(md["temp_indices"])[:K]
    press_idx = list(md["pressure_indices"])
    recirc_idx = list(md["recirculation_indices"])[:K]
    water_t_idx = list(md["water_indices"])
    hw_dp_idx = press_idx[K] if len(press_idx) > K else None
    za = md["zone_action_indices"]
    d_idx = np.array([za.get(v, {}).get("supply_air_damper_percentage_command", -1) for v in vav_ids])
    v_idx = np.array([za.get(v, {}).get("reheat_valve_percentage_command", -1) for v in vav_ids])
    anorm = md.get("action_normalization_metadata", {}) or {}

    def rng(sub, lo, hi):
        for k, v in anorm.items():
            if sub in k:
                return float(v["min_native_value"]), float(v["max_native_value"])
        return lo, hi

    sat_rng = rng("supply_air_temperature_setpoint", 285.0, 305.0)
    p_rng = rng("static_pressure_setpoint", 0.0, 2000.0)
    tw_rng = rng("supply_water_temperature_setpoint", 310.0, 350.0)
    dp_rng = rng("differential_pressure_setpoint", 0.0, 20.0)

    def denorm(x, r):
        return (float(x) + 1.0) / 2.0 * (r[1] - r[0]) + r[0]

    ahu_ids = [ahu.device_id() for ahu in ahus]
    room_to_ahu = {}
    for aid, rooms in (md.get("ahu_zone_assignments") or {}).items():
        for r in rooms:
            room_to_ahu[r.replace("room_", "VAV_")] = ahu_ids.index(aid) if aid in ahu_ids else -1
    ahu_of_zone = np.array([room_to_ahu.get(v, -1) for v in vav_ids])
    areas = zone_areas(md.get("zone_map"), vav_ids)
    oat_name = next((n for n in md["observation_field_names"] if n.endswith("outside_air_temperature_sensor")), None)
    oat_i = md["observation_field_names"].index(oat_name) if oat_name else -1
    onorm = md.get("observation_normalization_metadata", {}) or {}
    oat_n = onorm.get("outside_air_temperature_sensor", {})
    oat_mean, oat_std = float(oat_n.get("sample_mean", 295.0)), float(oat_n.get("sample_std", 10.0)) or 10.0

    tracker.reset()
    obs = tracker.last_obs
    n_steps = a.steps
    zone_t = np.zeros((n_steps, V), dtype=np.float32)
    zone_occ = np.zeros((n_steps, V), dtype=np.float32)
    damper = np.zeros((n_steps, V), dtype=np.float32)
    valve = np.zeros((n_steps, V), dtype=np.float32)
    ahu_run = np.zeros((n_steps, K), dtype=np.int8)
    ahu_p = np.zeros((n_steps, K), dtype=np.float32)
    ahu_sat = np.zeros((n_steps, K), dtype=np.float32)
    ahu_rc = np.zeros((n_steps, K), dtype=np.float32)
    ahu_flow = np.zeros((n_steps, K), dtype=np.float32)
    rows = []
    t0 = time.time()
    pol_time = 0.0
    n = 0
    for _ in range(n_steps):
        tp = time.time()
        act = validate_action(policy.get_action(obs), spec)
        pol_time += time.time() - tp
        cont, disc = act["continuous_action"], act["discrete_action"]
        # record the commands (native units) before stepping
        for k in range(K):
            ahu_run[n, k] = int(disc[k])
            ahu_sat[n, k] = denorm(cont[temp_idx[k]], sat_rng) if k < len(temp_idx) else np.nan
            ahu_p[n, k] = denorm(cont[press_idx[k]], p_rng) if k < len(press_idx) else np.nan
            ahu_rc[n, k] = (float(cont[recirc_idx[k]]) + 1.0) / 2.0 if k < len(recirc_idx) else np.nan
        damper[n] = np.where(d_idx >= 0, (cont[np.maximum(d_idx, 0)] + 1.0) / 2.0, np.nan)
        valve[n] = np.where(v_idx >= 0, (cont[np.maximum(v_idx, 0)] + 1.0) / 2.0, np.nan)
        hw_t = denorm(cont[water_t_idx[0]], tw_rng) if water_t_idx else np.nan
        hw_dp = denorm(cont[hw_dp_idx], dp_rng) if hw_dp_idx is not None else np.nan
        pump_on = int(disc[-1])
        oat_obs = float(obs[oat_i]) if oat_i >= 0 else np.nan
        if oat_name and not oat_name.startswith("ahs_"):
            oat_obs = oat_obs * oat_std + oat_mean

        obs, _, term, trunc, _ = tracker.step(act)
        info, resp = env.get_reward_info_and_response()
        blower = sum(x.blower_electrical_energy_rate for x in info.air_handler_reward_infos.values())
        cool = sum(x.air_conditioning_electrical_energy_rate for x in info.air_handler_reward_infos.values())
        pump = sum(x.pump_electrical_energy_rate for x in info.boiler_reward_infos.values())
        gas = sum(x.natural_gas_heating_energy_rate for x in info.boiler_reward_infos.values())
        zocc = {zid: z.average_occupancy for zid, z in info.zone_reward_infos.items()}
        zone_occ[n] = [zocc.get(v.replace("VAV_", "room_"), 0.0) for v in vav_ids]
        zone_t[n] = tracker.zone_temps[-1]
        ahu_flow[n] = [ahu.air_flow_rate for ahu in ahus]
        rows.append([
            tracker.timestamps[-1].isoformat(), f"{tracker.rewards[-1]:.6f}",
            f"{resp.normalized_productivity_regret:.6f}", f"{resp.normalized_energy_cost:.6f}",
            f"{resp.normalized_carbon_emission:.6f}", f"{resp.total_occupancy:.2f}", f"{oat_obs:.2f}",
            f"{blower:.1f}", f"{cool:.1f}", f"{pump:.1f}", f"{gas:.1f}",
            f"{resp.electricity_energy_cost:.5f}", f"{resp.natural_gas_energy_cost:.5f}", f"{resp.carbon_emitted:.5f}",
            str(getattr(policy, "mode", -1)), str(int(ahu_run[n].sum())), f"{ahu_flow[n].sum():.3f}",
            f"{np.nanmax(ahu_p[n]):.0f}", f"{np.nanmin(ahu_sat[n]):.2f}", f"{hw_t:.1f}", f"{hw_dp:.2f}", str(pump_on),
        ])
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
        "policy": a.policy, "building": a.building, "weather": a.weather,
        "station": a.weather.rsplit("_", 1)[0],
        "total_reward": float(rewards.sum()), "total_steps": int(len(rewards)),
        "avg_reward": float(rewards.mean()) if len(rewards) else 0.0,
        "avg_occupancy": float(occ.mean()) if len(occ) else 0.0,
        "avg_zone_temp": float(zt.mean()) if zt.size else 0.0,
        "productivity_weight": float(tracker.productivity_weight),
        "energy_weight": float(tracker.energy_weight),
        "carbon_weight": float(tracker.carbon_weight),
        "total_normalized_productivity_regret": tot("normalized_productivity_regret"),
        "total_normalized_energy_cost": tot("normalized_energy_cost"),
        "total_normalized_carbon_emission": tot("normalized_carbon_emission"),
        "seconds_per_step": wall / max(n, 1), "policy_seconds_per_step": pol_time / max(n, 1),
        "env_load_seconds": load_s,
        "n_discrete_action": int(md["n_discrete_action"]), "n_continuous_action": int(md["n_continuous_action"]),
        "num_zones": int(len(md["zone_temp_indices"])), "num_ahus": int(len(md["ahu_zone_assignments"])),
        "params_hash": phash, "params_json": a.params_json, "diag": True,
    }
    summ_path.write_text(json.dumps(summary, indent=2))
    with open(out_dir / "diag.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "reward", "regret_n", "energy_n", "carbon_n", "occupancy", "oat_k",
                    "blower_w", "cool_w", "pump_w", "gas_w", "elec_cost_usd", "gas_cost_usd", "carbon_kg",
                    "mode", "n_ahu_on", "sum_flow_m3s", "max_p_pa", "min_sat_k", "hw_t_k", "hw_dp_bar", "pump_on"])
        w.writerows(rows)
    # the same timeseries.csv as run_scenario.py --save-ts, so analyze_final.py and the trace figure work
    with open(out_dir / "timeseries.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "reward", "productivity_regret", "energy_cost", "carbon", "occupancy"]
                   + [f"zone_{i}_temp" for i in range(zt.shape[1] if zt.ndim == 2 else 0)])
        for i in range(len(rewards)):
            row = [tracker.timestamps[i].isoformat(), f"{rewards[i]:.6f}",
                   f"{rc[i].get('normalized_productivity_regret', 0.0):.6f}",
                   f"{rc[i].get('normalized_energy_cost', 0.0):.6f}",
                   f"{rc[i].get('normalized_carbon_emission', 0.0):.6f}", f"{occ[i]:.2f}"]
            if zt.ndim == 2:
                row += [f"{v:.3f}" for v in zt[i]]
            w.writerow(row)
    np.savez_compressed(out_dir / "zones.npz", zone_t=zone_t[:n], zone_occ=zone_occ[:n], damper=damper[:n],
                        valve=valve[:n], ahu_run=ahu_run[:n], ahu_p=ahu_p[:n], ahu_sat=ahu_sat[:n],
                        ahu_recirc=ahu_rc[:n], ahu_flow=ahu_flow[:n], vav_ids=np.array(vav_ids),
                        ahu_of_zone=ahu_of_zone, zone_area_m2=areas)
    print(f"{a.building}/{a.weather}/{a.policy}: total={summary['total_reward']:.2f} steps={n} "
          f"sec/step={summary['seconds_per_step']:.3f} (policy {summary['policy_seconds_per_step']*1000:.2f} ms) "
          f"regret={summary['total_normalized_productivity_regret']:.2f} "
          f"energy={summary['total_normalized_energy_cost']:.2f} carbon={summary['total_normalized_carbon_emission']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
