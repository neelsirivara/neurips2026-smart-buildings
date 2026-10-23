"""Robustness checks for a transfer policy file, without the simulator.

Builds synthetic building metadata of several shapes (K air handlers, V zones, with and without a
zone map, with orphan VAVs, K=1/V=1, V=0 zones), feeds random and adversarial observations
(NaN, inf, out-of-range, all zeros) and checks that every action is finite, inside [-1, 1] /
{0, 1}, of the declared shape, deterministic for the same input sequence, and fast.

Usage:  python test_policy_robustness.py [policy_file]   (default submission/transfer_policy.py)
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class Spec:
    def __init__(self, shape):
        self.shape = shape


def make_metadata(K: int, V: int, with_map: bool = True, orphan: bool = False, rng=None):
    rng = rng or np.random.default_rng(0)
    names = []
    for k in range(1, K + 1):
        names += [f"ahs_ahu_{k}_supply_air_temperature_sensor", f"ahs_ahu_{k}_supply_air_static_pressure_sensor",
                  f"ahs_ahu_{k}_outside_air_temperature_sensor", f"ahs_ahu_{k}_recirculation_percentage_command"]
    names += ["hws_supply_water_temperature_sensor", "hws_supply_water_temperature_setpoint"]
    for v in range(1, V + 1):
        names += [f"VAV_{v}_zone_air_temperature_sensor", f"VAV_{v}_zone_air_heating_temperature_setpoint_sensor",
                  f"VAV_{v}_zone_air_cooling_temperature_setpoint_sensor", f"VAV_{v}_supply_air_flowrate_setpoint",
                  f"VAV_{v}_supply_air_damper_percentage_command", f"VAV_{v}_reheat_valve_percentage_command"]
    names += ["hod_sin_000", "hod_cos_000", "dow_sin_000", "dow_cos_000", "comfort_mode_now", "comfort_mode_soon", "num_occupants"]
    # continuous action layout: per AHU temp, pressure, recirc; then water temp, water dP; then per zone damper, valve
    temp_idx, press_idx, rec_idx = [], [], []
    i = 0
    for k in range(K):
        temp_idx.append(i); press_idx.append(i + 1); rec_idx.append(i + 2); i += 3
    water_idx = [i]; press_idx.append(i + 1); i += 2
    zone_actions = {}
    for v in range(1, V + 1):
        zone_actions[f"VAV_{v}"] = {"supply_air_damper_percentage_command": i, "reheat_valve_percentage_command": i + 1}
        i += 2
    if orphan:  # a VAV with actions but no sensors and no handler
        zone_actions["VAV_999"] = {"supply_air_damper_percentage_command": i, "reheat_valve_percentage_command": i + 1}
        i += 2
    n_cont = i
    assignments = {f"ahu_{k + 1}": [] for k in range(K)}
    for v in range(1, V + 1):
        assignments[f"ahu_{(v - 1) % K + 1}"].append(f"room_{v}")
    zone_map = None
    if with_map and V:
        # V rooms of random size in a row, separated by walls, padded by exterior (2)
        widths = rng.integers(10, 60, size=V)
        W = int(widths.sum() + V + 1 + 10)
        H = 30
        zm = np.full((H, W), 2.0)
        zm[5:25, 5:W - 5] = 1.0
        c = 6
        for w in widths:
            zm[6:24, c:c + w] = 0.0
            c += w + 1
        zone_map = zm
    md = {
        "n_discrete_action": K + 1, "n_continuous_action": n_cont,
        "temp_indices": temp_idx, "pressure_indices": press_idx, "recirculation_indices": rec_idx,
        "water_indices": water_idx, "zone_action_indices": zone_actions,
        "zone_temp_indices": [i for i, n in enumerate(names) if "zone_air_temperature" in n],
        "observation_field_names": names, "floor_plan": zone_map, "zone_map": zone_map,
        "ahu_zone_assignments": assignments, "num_floors": 1, "morning_start_hour": 6, "evening_start_hour": 19,
        "comfort_temp_window": (294, 297), "eco_temp_window": (289, 298), "time_zone": "US/Pacific", "holidays": set(),
        "observation_normalization_metadata": {
            "zone_air_temperature_sensor": {"sample_mean": 295.0, "sample_variance": 25.0, "sample_std": 5.0},
            "outside_air_temperature_sensor": {"sample_mean": 295.0, "sample_variance": 100.0, "sample_std": 10.0}},
        "action_normalization_metadata": {
            "ahu_1_supply_air_temperature_setpoint": {"min_native_value": 285.0, "max_native_value": 305.0},
            "ahu_1_supply_air_static_pressure_setpoint": {"min_native_value": 0.0, "max_native_value": 2000.0},
            "supply_water_temperature_setpoint": {"min_native_value": 310.0, "max_native_value": 350.0},
            "differential_pressure_setpoint": {"min_native_value": 0.0, "max_native_value": 20.0}},
    }
    spec = {"continuous_action": Spec((n_cont,)), "discrete_action": Spec((K + 1,))}
    return md, spec, names


def obs_stream(names, V, steps, rng, mode="normal"):
    n = len(names)
    ix = {k: i for i, k in enumerate(names)}
    for t in range(steps):
        obs = np.zeros(n, dtype=np.float32)
        hod = (6.0 + t * 5 / 60.0) % 24.0
        dow = ((6.0 + t * 5 / 60.0) // 24.0) % 7.0
        obs[ix["hod_sin_000"]] = np.sin(2 * np.pi * hod / 24); obs[ix["hod_cos_000"]] = np.cos(2 * np.pi * hod / 24)
        obs[ix["dow_sin_000"]] = np.sin(2 * np.pi * dow / 7); obs[ix["dow_cos_000"]] = np.cos(2 * np.pi * dow / 7)
        now = 1.0 if (dow < 5 and 6 <= hod < 19) else 0.0
        obs[ix["comfort_mode_now"]] = now
        obs[ix["comfort_mode_soon"]] = 1.0 if (dow < 5 and 5 <= hod < 19) else 0.0
        obs[ix["num_occupants"]] = (rng.integers(0, 40) if now else 0) / 126.0 - 125.0 / 126.0
        obs[ix["hws_supply_water_temperature_sensor"]] = 340.0
        obs[ix["hws_supply_water_temperature_setpoint"]] = 340.0
        for k in [n for n in names if n.endswith("outside_air_temperature_sensor")]:
            obs[ix[k]] = 260.0 + 50 * rng.random()
        for v in range(1, V + 1):
            obs[ix[f"VAV_{v}_zone_air_temperature_sensor"]] = (280 + 30 * rng.random() - 295) / 5.0
            obs[ix[f"VAV_{v}_zone_air_heating_temperature_setpoint_sensor"]] = 294.0 if now else 289.0
            obs[ix[f"VAV_{v}_zone_air_cooling_temperature_setpoint_sensor"]] = 297.0 if now else 298.0
            obs[ix[f"VAV_{v}_supply_air_flowrate_setpoint"]] = 2.0
        if mode == "nan" and t % 7 == 3:
            obs[rng.integers(0, n, size=max(1, n // 10))] = np.nan
        if mode == "inf" and t % 5 == 1:
            obs[rng.integers(0, n, size=max(1, n // 10))] = np.inf
        if mode == "zeros" and t % 3 == 0:
            obs[:] = 0.0
        if mode == "huge" and t % 4 == 2:
            obs[:] = 1e9
        yield obs


def check(policy_cls, K, V, with_map, orphan, mode, steps=600):
    rng = np.random.default_rng(1)
    md, spec, names = make_metadata(K, V, with_map, orphan, rng)
    t0 = time.time()
    pol = policy_cls(md, spec)
    t_init = time.time() - t0
    outs = []
    t0 = time.time()
    for obs in obs_stream(names, V, steps, np.random.default_rng(2), mode):
        a = pol.get_action(obs)
        c, d = np.asarray(a["continuous_action"]), np.asarray(a["discrete_action"])
        assert c.shape == spec["continuous_action"].shape, (c.shape, spec["continuous_action"].shape)
        assert d.shape == spec["discrete_action"].shape
        assert c.dtype == np.float32 and d.dtype == np.int32, (c.dtype, d.dtype)
        assert np.all(np.isfinite(c)), "non-finite continuous action"
        assert c.min() >= -1.0 and c.max() <= 1.0, (c.min(), c.max())
        assert set(np.unique(d).tolist()) <= {0, 1}, np.unique(d)
        outs.append(c.copy())
    t_step = (time.time() - t0) / steps
    # determinism: same sequence again from a fresh instance
    pol2 = policy_cls(md, spec)
    for i, obs in enumerate(obs_stream(names, V, steps, np.random.default_rng(2), mode)):
        c2 = np.asarray(pol2.get_action(obs)["continuous_action"])
        assert np.array_equal(c2, outs[i]), f"non-deterministic at step {i}"
    return t_init, t_step, getattr(pol, "area_known", None)


def main() -> int:
    pf = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "submission" / "transfer_policy.py"
    spec = importlib.util.spec_from_file_location("pol_under_test", pf)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = mod.TransferPolicy
    cases = [(4, 39, True, False), (1, 1, True, False), (1, 0, True, False), (12, 120, True, False), (3, 30, False, False),
             (2, 7, True, True), (7, 70, True, False)]
    n = 0
    for K, V, wm, orph in cases:
        for mode in ("normal", "nan", "inf", "zeros", "huge"):
            t_init, t_step, ak = check(cls, K, V, wm, orph, mode, steps=300 if mode != "normal" else 600)
            n += 1
            print(f"ok K={K:2d} V={V:3d} map={int(wm)} orphan={int(orph)} obs={mode:6s} init {t_init*1000:6.1f} ms  "
                  f"step {t_step*1000:5.2f} ms  area_known={ak}")
    print(f"{n} cases passed for {pf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
