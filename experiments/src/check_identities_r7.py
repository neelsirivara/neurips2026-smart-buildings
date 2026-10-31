"""Round 7, ANALYSIS.md check 1: the heating-mode cost identities, read from the simulator's own internals.

Runs SADR (default: the shipped v9) for a few hundred steps on one scenario and records, inside every step, what the
simulator computes (by wrapping the kit's own methods, no re-implementation):
  * AirHandler.get_supply_air_temp(recirculation_temp, ambient_temp) -> T_sa, plus the handler's recirculation r;
  * VAV.compute_reheat_energy_rate(T_sa, T_w) -> reheat W (the water side), VAV.compute_zone_supply_temp -> T_disch,
    VAV.flow_rate_demand (m3/s), the zone temperature the VAV senses;
  * Boiler.compute_thermal_energy_rate(...) -> the gas the boiler is billed for.
and checks the identities used in the analysis:
  (1) T_sa = min(SAT setpoint, r T_ret + (1 - r) T_oa)                                 (the handler can only cool)
  (2) T_disch <= 308.15 K, and = 308.15 K whenever the coil is effectiveness-limited by the discharge cap
  (3) net heat into the zone Q = rho cp F (T_disch - T); reheat (gas) = rho cp F (T_disch - T_sa), hence
      gas per joule of net heat g = (T_disch - T_sa) / (T_disch - T) = 1 + (T - T_sa) / (T_disch - T)
  (4) billed boiler gas = sum of reheat W + tank / dissipation terms (small)

    python check_identities_r7.py [--building building_train_8 --weather fairbanks_c2 --set heldout_scenarios_r6hs]
        [--steps 576] [--policy-file ../../submission/transfer_policy.py] --out ../results/round7/check_identities.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = Path(os.environ["SB_KIT_DIR"]) if os.environ.get("SB_KIT_DIR") else ROOT / "kit"
ORIG = Path.cwd()
sys.path.insert(0, str(KIT))
os.chdir(KIT)

import numpy as np  # noqa: E402

from smart_buildings import evaluate as ev  # noqa: E402
from smart_buildings.smart_control.simulator import air_handler as ahm  # noqa: E402
from smart_buildings.smart_control.simulator import boiler as bm  # noqa: E402
from smart_buildings.smart_control.simulator import vav as vm  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402

RHO_CP = 1.2 * 1006.0
LOG = {"sa": [], "reheat": [], "supply": [], "boiler": []}


def _wrap():
    o_sa = ahm.AirHandler.get_supply_air_temp
    o_rh = vm.Vav.compute_reheat_energy_rate if hasattr(vm, "Vav") else vm.VAV.compute_reheat_energy_rate
    cls = vm.Vav if hasattr(vm, "Vav") else vm.VAV
    o_zs = cls.compute_zone_supply_temp
    o_b = bm.Boiler.compute_thermal_energy_rate

    def sa(self, recirculation_temp, ambient_temp):
        out = o_sa(self, recirculation_temp, ambient_temp)
        LOG["sa"].append((self.device_id(), float(recirculation_temp), float(ambient_temp), float(self.recirculation),
                          float(self.supply_air_temperature_setpoint), float(out)))
        return out

    def rh(self, supply_air_temp, input_water_temp):
        out = o_rh(self, supply_air_temp, input_water_temp)
        eff = self._reheat_effectiveness(supply_air_temp, input_water_temp)
        td = supply_air_temp + eff * (input_water_temp - supply_air_temp)
        LOG["reheat"].append((self.device_id(), float(supply_air_temp), float(input_water_temp), float(out),
                              float(self.flow_rate_demand), float(self.zone_air_temperature),
                              float(self.reheat_valve_setting), float(td)))
        return out

    def zs(self, supply_air_temp, input_water_temp):
        out = o_zs(self, supply_air_temp, input_water_temp)
        LOG["supply"].append((self.device_id(), float(out)))
        return out

    def bo(self, return_water_temp, outside_temp, total_flow_rate):
        out = o_b(self, return_water_temp, outside_temp, total_flow_rate)
        LOG["boiler"].append(float(out))
        return out

    ahm.AirHandler.get_supply_air_temp = sa
    cls.compute_reheat_energy_rate = rh
    cls.compute_zone_supply_temp = zs
    bm.Boiler.compute_thermal_energy_rate = bo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--building", default="building_train_8")
    ap.add_argument("--weather", default="fairbanks_c2")
    ap.add_argument("--set", default="heldout_scenarios_r6hs")
    ap.add_argument("--steps", type=int, default=576)
    ap.add_argument("--policy-file", default=str(ROOT / "submission" / "transfer_policy.py"))
    ap.add_argument("--out", default=str(ROOT / "experiments" / "results" / "round7" / "check_identities.json"))
    a = ap.parse_args()
    _wrap()
    scen = KIT / "smart_buildings" / a.set / a.building / a.weather
    env = ev.load_hybrid_environment(scen / "config.gin")
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
    md = ev.create_building_meta_data(env, scen)
    spec = importlib.util.spec_from_file_location("pol", a.policy_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pol = mod.TransferPolicy(md, env.action_spec())
    tr.reset()
    obs = tr.last_obs
    rows = defaultdict(list)
    for step in range(a.steps):
        for k in LOG:
            LOG[k].clear()
        obs, *_ = tr.step(ev.validate_action(pol.get_action(obs), env.action_spec()))
        # (1) supply air
        for (_, tret, toa, r, sp, out) in LOG["sa"]:
            mix = r * tret + (1 - r) * toa
            rows["sa_err"].append(abs(out - min(sp, mix)))
            rows["recirc"].append(r)
        # (2)-(3) VAV: pair reheat calls with zone-supply calls in order (one each per VAV per step)
        n_heat = 0
        seen = set()
        for (vid, tsa, tw, rw, flow, tz, valve, td) in LOG["reheat"]:
            if rw <= 1.0 or vid in seen:
                continue
            seen.add(vid)
            n_heat += 1
            q_net = rw + RHO_CP * flow * (tsa - tz)
            rows["td"].append(td)
            rows["td_at_cap"].append(abs(td - 308.15) < 0.01)
            rows["reheat_identity_err"].append(abs(rw - RHO_CP * flow * (td - tsa)) / max(rw, 1.0))
            if q_net > 1.0 and td - tz > 0.5:
                rows["g_meas"].append(rw / q_net)
                rows["g_formula"].append(1.0 + (tz - tsa) / (td - tz))
                rows["g_oat"].append(LOG["sa"][0][2] if LOG["sa"] else float("nan"))
                rows["g_tz"].append(tz)
                rows["g_rw"].append(rw)
                rows["g_q"].append(q_net)
                rows["g_cap"].append(abs(td - 308.15) < 0.01)
                rows["g_tsa"].append(tsa)
        if LOG["boiler"] and LOG["reheat"]:
            rows["boiler_w"].append(float(np.mean(LOG["boiler"])))      # the reward path may evaluate it more than once
            first = {}
            for x in LOG["reheat"]:
                first.setdefault(x[0], x[3])
            rows["reheat_w"].append(sum(first.values()))
        rows["n_heat"].append(n_heat)
    g_m, g_f = np.array(rows["g_meas"]), np.array(rows["g_formula"])
    oat = np.array(rows["g_oat"]) - 273.15
    bw, rw = np.array(rows["boiler_w"]), np.array(rows["reheat_w"])
    out = {
        "scenario": f"{a.set}/{a.building}/{a.weather}", "steps": a.steps, "policy_file": Path(a.policy_file).name,
        "sa_identity_max_abs_err_k": float(np.max(rows["sa_err"])) if rows["sa_err"] else None,
        "recirc_share_at_cap_0p7": float(np.mean(np.isclose(rows["recirc"], 0.7))) if rows["recirc"] else None,
        "heated_vav_steps": int(len(rows["td"])),
        "discharge_max_k": float(np.max(rows["td"])) if rows["td"] else None,
        "discharge_at_cap_share": float(np.mean(rows["td_at_cap"])) if rows["td"] else None,
        "reheat_identity_max_rel_err": float(np.max(rows["reheat_identity_err"])) if rows["reheat_identity_err"] else None,
        "g_n": int(len(g_m)),
        "g_meas_mean": float(g_m.mean()) if len(g_m) else None,
        "g_formula_max_abs_err": float(np.max(np.abs(g_m - g_f))) if len(g_m) else None,
        "g_by_oat_bin": {},
        "boiler_over_reheat_sum": float(bw.sum() / rw.sum()) if rw.sum() > 0 else None,
        "boiler_minus_reheat_mean_w": float((bw - rw).mean()) if len(bw) else None,
    }
    rwv, qv, cap = np.array(rows["g_rw"]), np.array(rows["g_q"]), np.array(rows["g_cap"], dtype=bool)
    tzv, tsav = np.array(rows["g_tz"]), np.array(rows["g_tsa"])
    if len(g_m):
        out["g_energy_weighted"] = float(rwv.sum() / qv.sum())
        out["g_energy_weighted_at_cap"] = float(rwv[cap].sum() / qv[cap].sum()) if cap.any() else None
        out["g_energy_weighted_below_cap"] = float(rwv[~cap].sum() / qv[~cap].sum()) if (~cap).any() else None
        out["net_heat_share_at_cap"] = float(qv[cap].sum() / qv.sum())
        out["mean_tz_minus_tsa_at_cap_k"] = float((tzv - tsav)[cap].mean()) if cap.any() else None
    for lo in range(-45, 15, 10):
        m = (oat >= lo) & (oat < lo + 10)
        if m.sum() >= 20:
            out["g_by_oat_bin"][f"{lo}..{lo + 10}C"] = {
                "n": int(m.sum()), "g_meas_mean": float(g_m[m].mean()),
                "g_energy_weighted": float(rwv[m].sum() / qv[m].sum()),
                "g_energy_weighted_at_cap": float(rwv[m & cap].sum() / qv[m & cap].sum()) if (m & cap).any() else None,
                "g_meas_p10": float(np.percentile(g_m[m], 10)), "g_meas_p90": float(np.percentile(g_m[m], 90))}
    op = Path(a.out)
    if not op.is_absolute():
        op = (ORIG / op).resolve()
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
