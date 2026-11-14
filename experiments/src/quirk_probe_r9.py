"""ANALYSIS ONLY (round 9): how much would the boiler billing quirk lower v10's loss?  NEVER use in a policy.

The shipped boiler bills the loop's flow term at the hot-water SETPOINT while the coils draw heat at the tank's
actual temperature, which falls at a fixed 0.1 K/min whatever the coils take (Kaggle topics 752142 / 751998 /
749531, starter-kit PR #2).  A setpoint saw-tooth therefore gets most reheat unbilled.  This harness measures the
size of that effect on top of the shipped v10 so the round-9 analysis can say whether it explains the leaderboard
gap.  The policy file is untouched: the harness overrides the hot-water setpoint slot after the policy has acted,
with the rule published in topic 752142 (pump on: setpoint minimum while the tank is at or above 345 K, maximum
otherwise).  Nothing here is shipped, submitted or copied into submission/.

Usage (Mac, through mac_runner_r9.py):
    python quirk_probe_r9.py --policy-file policies/v10.py --building building_train_1 --weather fairbanks_1 \
        --scenarios-dir <kit>/smart_buildings/training_scenarios --results-dir out/quirk_probe/pub30 [--no-quirk]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

KIT = Path(os.environ["SB_KIT_DIR"])
sys.path.insert(0, str(KIT))
ORIG = Path(os.getcwd())
os.chdir(KIT)

import numpy as np  # noqa: E402

from smart_buildings.evaluate import create_building_meta_data, load_hybrid_environment, validate_action  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy-file", required=True)
    ap.add_argument("--building", required=True)
    ap.add_argument("--weather", required=True)
    ap.add_argument("--scenarios-dir", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--steps", type=int, default=8640)
    ap.add_argument("--no-quirk", action="store_true", help="reference run through the same harness")
    a = ap.parse_args()
    pf = Path(a.policy_file)
    pf = pf if pf.is_absolute() else (ORIG / pf)
    rd = Path(a.results_dir)
    rd = rd if rd.is_absolute() else (ORIG / rd)
    tag = "ref" if a.no_quirk else "quirk"
    out = rd / a.building / a.weather / tag
    out.mkdir(parents=True, exist_ok=True)
    if (out / "summary.json").exists():
        print("skip (done)")
        return 0
    scen = Path(a.scenarios_dir) / a.building / a.weather
    env = load_hybrid_environment(scen / "config.gin")
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
    md = create_building_meta_data(env, scen)
    spec = importlib.util.spec_from_file_location("v10_probe", pf)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pol = mod.TransferPolicy(md, env.action_spec())
    boiler = env.building.simulator._hvac.hot_water_system._heat_source
    widx = list(md["water_indices"])
    tr.reset()
    obs = tr.last_obs
    t0 = time.time()
    n_over = 0
    for _ in range(a.steps):
        act = pol.get_action(obs)
        if not a.no_quirk and int(act["discrete_action"][-1]) == 1 and widx:
            act["continuous_action"][widx[0]] = -1.0 if float(boiler._current_temperature) >= 345.0 else 1.0
            n_over += 1
        obs, _, term, trunc, _ = tr.step(validate_action(act, env.action_spec()))
        if term or trunc:
            break
    rc = tr.reward_components
    n = len(tr.rewards)
    s = {"building": a.building, "weather": a.weather, "mode": tag, "total_reward": float(np.sum(tr.rewards)),
         "total_steps": n, "avg_reward": float(np.mean(tr.rewards)),
         "total_normalized_productivity_regret": float(sum(r.get("normalized_productivity_regret", 0.0) for r in rc)),
         "total_normalized_energy_cost": float(sum(r.get("normalized_energy_cost", 0.0) for r in rc)),
         "total_normalized_carbon_emission": float(sum(r.get("normalized_carbon_emission", 0.0) for r in rc)),
         "steps_overridden": n_over, "wall_s": time.time() - t0, "policy_file": str(pf)}
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
