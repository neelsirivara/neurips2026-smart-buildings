"""Round 11: leave-one-out ablation of the shipped v12 on private Kaggle kernels (plan: results/round11/PLAN.md).

    python ablation_r11.py make        # writes results/round11/params/*.json and the shard job files, prints them
    python ablation_r11.py enqueue     # make + kaggle_sim.py enqueue, in priority order
Results land in results/round6/runs/<arm>/<set>/... after kaggle_sim.py fetch (the dispatcher fetches on its own).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R11 = ROOT / "experiments" / "results" / "round11"
POLICY = ROOT / "submission" / "transfer_policy.py"
sys.path.insert(0, str(HERE))
import jobs_r6  # noqa: E402

# priority order: the reference, the frost pair, the v4-v6 design facts, then the v7-v12 additions
ARMS = [
    ("ab12_ref", {}),
    ("ab12_noarea", {"gain_area_scaling": 0.0}),
    ("ab12_nozone", {"per_zone_start": 0.0}),
    ("ab12_sat293", {"sat_cool_hi": 293.0}),
    ("ab12_tw330", {"tw_hot_k": 330.0}),
    ("ab12_nomodel", {"mbr_on": 0.0, "mpr_on": 0.0}),
    ("ab12_noweekend", {"wk_ext_lo": 0.0, "wk_ext_hi": 0.0}),
    ("ab12_nodow", {"dow_snap": 0.0}),
    ("ab12_noboost", {"sb_boost": 0.0, "sb_boost_floor_k": 0.0}),
    ("ab12_noseason", {"season_ext_steps": 0.0}),
    ("ab12_noecon", {"econ_on": 0.0}),
    ("ab12_nowcap", {"water_cap": 0.0}),
    ("ab12_nofloor", {"adaptive_floor": 0.0}),
    ("ab12_noflush", {"flush_on": 0.0}),
    ("ab12_nooccdyn", {"occ_press_dyn": 0.0}),
    ("ab12_noneutral", {"sb_neutral": 0.0}),
    ("ab12_qcap12", {"q_cap_w": 12000.0}),
]
HS_ARMS = [("ab12_ref", {}), ("ab12_frost5", {"frost_floor_k": 278.15})]


def make() -> list[Path]:
    pdir = R11 / "params"
    pdir.mkdir(parents=True, exist_ok=True)
    files = []
    plan = [(a, d, "pub30") for a, d in ARMS[:1]] + [(a, d, "r6hs") for a, d in HS_ARMS] + \
           [(a, d, "pub30") for a, d in ARMS[1:]]
    for arm, delta, s in plan:
        pfile = None
        if delta:
            pfile = pdir / f"{arm}.json"
            pfile.write_text(json.dumps(delta, indent=1))
        out = jobs_r6.make(arm, s, str(pfile) if pfile else None, False, 10, None, None, str(POLICY))
        if arm == "ab12_ref":
            for f in out:
                jobs = json.loads(f.read_text())
                for j in jobs:
                    j["save_ts"] = True
                f.write_text(json.dumps(jobs, indent=1))
        files += out
    (R11 / "job_files.json").write_text(json.dumps([str(f) for f in files], indent=1))
    return files


def main() -> int:
    files = make()
    if sys.argv[1:] == ["enqueue"]:
        subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                       check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
