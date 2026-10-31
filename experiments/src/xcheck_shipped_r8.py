"""Round 8: the shipped v10 file (submission/transfer_policy.py, parameters baked, no params JSON) against the Kaggle
confirmation runs of r7L_mbr2 at 8,640 steps on two HC2 scenarios (one laptop worker each, sequential).
-> results/round8/xcheck_shipped_v10.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
KB = ROOT / "kit" / "smart_buildings"
SHIP = ROOT / "submission" / "transfer_policy.py"
SCEN = [("building_train_8", "minneapolis_c2"), ("building_train_8", "denver_c1")]


def main() -> int:
    out = {}
    md5 = hashlib.md5(SHIP.read_bytes()).hexdigest()
    for b, w in SCEN:
        rd = RES / "round8" / "xcheck_shipped" / b / w
        cmd = [sys.executable, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", b, "--weather", w,
               "--steps", "8640", "--results-dir", str(rd), "--scenarios-dir", str(KB / "heldout_scenarios_r7hc"),
               "--policy-file", str(SHIP), "--force"]
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        if rc:
            return rc
        mine = json.loads(next(rd.rglob("summary.json")).read_text())
        kag = json.loads(next((RES / "round6" / "runs" / "r7L_mbr2" / "r7hc" / b / w).rglob("summary.json")).read_text())
        out[f"{b}/{w}"] = {"shipped_laptop_total": mine["total_reward"], "r7L_mbr2_kaggle_total": kag["total_reward"],
                           "identical": mine["total_reward"] == kag["total_reward"],
                           "rel_diff": (mine["total_reward"] - kag["total_reward"]) / abs(kag["total_reward"]),
                           "steps": mine["total_steps"], "shipped_md5": md5}
        print(b, w, out[f"{b}/{w}"])
    (RES / "round8" / "xcheck_shipped_v10.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
