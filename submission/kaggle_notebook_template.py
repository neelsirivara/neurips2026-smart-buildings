"""Kaggle notebook template for the SB26 Smart Buildings Challenge -- SADR policy (v5, final).

HOW TO USE (the official template could not be read without a Kaggle login, so this
mirrors the starter kit's own evaluation loop; adapt cell by cell):

  Cell 1  -- paste the full contents of `transfer_policy.py` (the class must stay
             named `TransferPolicy`).  This file does that with `exec` of a sibling
             file for local testing; on Kaggle paste the code inline instead.
  Cell 2  -- the harness below: it is the kit's `evaluate.py` loop without plots and
             is only needed if the official template does not already drive the
             policy.  If the template calls `TransferPolicy(building_meta_data,
             action_spec).get_action(obs)` itself, delete Cell 2.

Nothing here needs network access, torch, or files other than the kit itself.
"""

# ----------------------------------------------------------------------------- Cell 1
import os
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
_POLICY_SRC = _HERE / "transfer_policy.py"
if _POLICY_SRC.exists():
    # Local convenience only. On Kaggle, paste transfer_policy.py's code here instead.
    exec(compile(_POLICY_SRC.read_text(), str(_POLICY_SRC), "exec"))
else:
    raise SystemExit("Paste the contents of transfer_policy.py into Cell 1 (TransferPolicy class).")

assert "TransferPolicy" in globals()

# ----------------------------------------------------------------------------- Cell 2
# Optional harness: run the policy on the public training scenarios with the kit's
# own environment loader, exactly as score_leaderboard.py expects.
KIT_ROOT = os.environ.get("SB26_KIT_ROOT", "/kaggle/input/smart-buildings-starter-kit")
if Path(KIT_ROOT).exists():
    sys.path.insert(0, KIT_ROOT)
    os.chdir(KIT_ROOT)
    from smart_buildings.evaluate import (create_building_meta_data, load_hybrid_environment,
                                          validate_action)
    from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker

    def run_scenario(scen_dir: Path, steps: int = 8640) -> float:
        env = load_hybrid_environment(scen_dir / "config.gin")
        env.metrics_path = None
        env._occupancy_normalization_constant = 125.0
        tracker = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
        md = create_building_meta_data(env, scen_dir)
        spec = env.action_spec()
        policy = TransferPolicy(md, spec)  # noqa: F821  (defined in Cell 1)
        tracker.reset()
        obs = tracker.last_obs
        for _ in range(steps):
            obs, _, term, trunc, _ = tracker.step(validate_action(policy.get_action(obs), spec))
            if term or trunc:
                break
        return float(np.sum(tracker.rewards))

    scen = Path(KIT_ROOT) / "smart_buildings" / "training_scenarios" / "building_train_1" / "fairbanks_1"
    if scen.exists():
        print("smoke test (288 steps, not comparable to full-length numbers):", run_scenario(scen, 288))
else:
    print(f"kit not found at {KIT_ROOT}; set SB26_KIT_ROOT or rely on the official template's harness")
