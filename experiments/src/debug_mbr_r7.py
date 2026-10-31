"""Round 7 development check (not a result): run v10 with given parameters on one scenario and print the online model state.

    python debug_mbr_r7.py --params policy_candidates/r7_mb.json --steps 2016 [--building ... --weather ... --set ...]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="heldout_scenarios_r6hs")
    ap.add_argument("--building", default="building_train_8")
    ap.add_argument("--weather", default="fairbanks_c2")
    ap.add_argument("--steps", type=int, default=2016)
    ap.add_argument("--policy-file", default=str(HERE / "policy_candidates" / "transfer_policy_v10.py"))
    ap.add_argument("--params", required=True)
    a = ap.parse_args()
    params = json.loads(Path(HERE / a.params if not Path(a.params).is_absolute() else a.params).read_text())
    scen = KIT / "smart_buildings" / a.set / a.building / a.weather
    env = ev.load_hybrid_environment(scen / "config.gin")
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
    md = ev.create_building_meta_data(env, scen)
    spec = importlib.util.spec_from_file_location("pol", a.policy_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pol = mod.TransferPolicy(md, env.action_spec(), params=params)
    tr.reset()
    obs = tr.last_obs
    tot = 0.0
    leads, floors = [], []
    for t in range(a.steps):
        obs, r, *_ = tr.step(ev.validate_action(pol.get_action(obs), env.action_spec()))
        tot += float(r)
        if np.isfinite(pol.mbr_floor_cache).any():
            floors.append(float(np.nanmean(pol.mbr_floor_cache)))
        leads.append(pol._lead_dbg)
    th = pol.mbr_th
    ok = (pol.mbr_n >= params.get("mbr_min_n", 36)) & (th[:, 0] > 1e-3) & (th[:, 1] > 1e-3)
    print(json.dumps({
        "total_reward": tot, "zones": int(len(th)), "trusted": int(ok.sum()),
        "a_kph_per_kw_median": float(np.median(th[ok, 0])) if ok.any() else None,
        "k_per_h_median": float(np.median(th[ok, 1])) if ok.any() else None,
        "tau_h_median": float(np.median(1 / th[ok, 1])) if ok.any() else None,
        "C_kwh_per_k_median": float(np.median(1 / th[ok, 0])) if ok.any() else None,
        "n_heated_windows_median": float(np.median(pol.mbr_n)),
        "floor_cache_mean_k": float(np.mean(floors)) if floors else None,
        "floor_cache_min_k": float(np.min(floors)) if floors else None,
        "lead_max_seen_h": float(np.max(leads)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
