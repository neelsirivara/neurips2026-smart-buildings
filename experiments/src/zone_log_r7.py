"""Round 7: per-zone thermal log for fitting first-order zone models (ANALYSIS.md, sections 3-5).

Runs a policy (default: the shipped v9) on one scenario and records, per step and per VAV, what the simulator
actually delivered (read inside the step from the kit's own methods, as in check_identities_r7.py):
    T     zone temperature the VAV senses at the start of the step (K)
    Q     net heat into the zone = reheat W + rho cp F (T_sa - T)   (W; negative = cooling by the air stream)
    QH    reheat W (= what the boiler is billed for, up to the tank terms)
    F     air flow (m3/s), Tsa (K) supply air entering the box, Td discharge temperature (K)
plus Tout, the policy's per-zone mode (0 occupied, 1 precondition, 2 setback), hour of day and day of week.
Writes <out>.npz; fit_zone_model_r7.py fits C dT/dt = Q - UA (T - Tout) + G per zone.

    python zone_log_r7.py --set heldout_scenarios_r6hs --building building_train_8 --weather fairbanks_c2 \
        --steps 4032 --out ../results/round7/zone_logs/building_train_8__fairbanks_c2.npz
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = Path(os.environ["SB_KIT_DIR"]) if os.environ.get("SB_KIT_DIR") else ROOT / "kit"
sys.path.insert(0, str(KIT))
os.chdir(KIT)

import numpy as np  # noqa: E402

from smart_buildings import evaluate as ev  # noqa: E402
from smart_buildings.smart_control.simulator import vav as vm  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402

RHO_CP = 1.2 * 1006.0
CUR: dict[str, tuple] = {}


def _wrap():
    o_rh = vm.Vav.compute_reheat_energy_rate

    def rh(self, supply_air_temp, input_water_temp):
        out = o_rh(self, supply_air_temp, input_water_temp)
        vid = self.device_id()
        if vid not in CUR:                      # first evaluation inside the step
            eff = self._reheat_effectiveness(supply_air_temp, input_water_temp)
            td = supply_air_temp + eff * (input_water_temp - supply_air_temp)
            on = self.damper_setting > 0 and self.max_air_flow_rate > 0
            f = float(self.flow_rate_demand) if on else 0.0
            tz = float(self.zone_air_temperature)
            CUR[vid] = (tz, float(out) + RHO_CP * f * (supply_air_temp - tz), float(out), f,
                        float(supply_air_temp), float(td))
        return out

    vm.Vav.compute_reheat_energy_rate = rh


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="heldout_scenarios_r6hs")
    ap.add_argument("--building", required=True)
    ap.add_argument("--weather", required=True)
    ap.add_argument("--steps", type=int, default=4032)
    ap.add_argument("--policy-file", default=str(ROOT / "submission" / "transfer_policy.py"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if not out.is_absolute():
        out = (HERE / a.out).resolve()
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
    sim = env.building.simulator
    vav_ids = sorted(sim.hvac.vavs.keys(), key=lambda s: int(s.split("_")[-1]))
    V, n = len(vav_ids), a.steps
    arr = {k: np.full((n, V), np.nan, dtype=np.float32) for k in ("T", "Q", "QH", "F", "Tsa", "Td", "mode")}
    tout = np.full(n, np.nan, dtype=np.float32)
    hod = np.zeros(n, dtype=np.float32)
    dow = np.zeros(n, dtype=np.int8)
    # the policy keeps its zones in the order of md["zone_action_indices"] (orphans dropped; none in the shipped six)
    pol_vavs = [v for v in (md.get("zone_action_indices") or {}) if v in sim.hvac.vavs]
    if len(pol_vavs) != getattr(pol, "V", -1):
        print(f"warning: policy has {getattr(pol, 'V', None)} zones, mapping {len(pol_vavs)}; modes not logged")
        pol_vavs = []
    col = {v: i for i, v in enumerate(vav_ids)}
    tr.reset()
    obs = tr.last_obs
    for t in range(n):
        CUR.clear()
        ts = env.building.current_timestamp
        obs, *_ = tr.step(ev.validate_action(pol.get_action(obs), env.action_spec()))
        tout[t] = sim.weather_controller.get_current_temp(ts)
        hod[t] = ts.hour + ts.minute / 60.0
        dow[t] = ts.dayofweek
        for vid, (tz, q, qh, f, tsa, td) in CUR.items():
            j = col[vid]
            arr["T"][t, j], arr["Q"][t, j], arr["QH"][t, j] = tz, q, qh
            arr["F"][t, j], arr["Tsa"][t, j], arr["Td"][t, j] = f, tsa, td
        zm = getattr(pol, "zone_mode", None)
        if zm is not None and len(pol_vavs) == len(zm):
            for i, v in enumerate(pol_vavs):
                if v in col:
                    arr["mode"][t, col[v]] = zm[i]
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, vav_ids=np.array(vav_ids), tout=tout, hod=hod, dow=dow, **arr)
    print(f"wrote {out}: {n} steps x {V} zones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
