"""Round 6: job files for the Kaggle shard runner (experiments/src/kaggle_sim).

Policies are frozen copies in results/round6/policies/ (v8.py = the shipped round-5 file) or round-5 copies
(v7, v6, v5); candidates are policy_candidates/transfer_policy_v9.py + a parameter JSON. Results land (after
`kaggle_sim.py fetch`) in results/round6/runs/<variant>/<set>/<building>/<weather>/<policy>/summary.json.

    python jobs_r6.py make --variant v8 --set r6hs [--diag] [--shard 12] [--prefix NAME]
    python jobs_r6.py make --variant r6_c01 --set r6hs --params ../src/policy_candidates/r6_c01.json
Shards are balanced by expected run time (longest-processing-time first, per-building speed from round 5).
Prints the job-file paths; push each with kaggle_sim.py push --name <stem> --jobs <file>.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R6 = RES / "round6"
KB = ROOT / "kit" / "smart_buildings"
JOBDIR = R6 / "kaggle_jobs"

PUBLIC30 = [f"{b.name}/{w.name}" for b in sorted((KB / "training_scenarios").iterdir()) if b.is_dir()
            for w in sorted(b.iterdir()) if (w / "config.gin").exists()]
SETS = {
    "pub30": "training_scenarios", "r6hc": "heldout_scenarios_r6hc", "r6hs": "heldout_scenarios_r6hs",
    "r5m": "heldout_scenarios_r5m", "r5ms": "heldout_scenarios_r5ms", "r5x": "heldout_scenarios_r5x",
    "r4c": "heldout_scenarios_r4c", "r7hc": "heldout_scenarios_r7hc",
    # round 10 (make_sets_r10.py): HC3 cold confirmation, HH hot confirmation, D10 development only
    "r10hc": "heldout_scenarios_r10hc", "r10hh": "heldout_scenarios_r10hh", "r10dev": "heldout_scenarios_r10dev",
}
FD_BUILDINGS = ("building_0604", "building_0607", "building_0610", "building_0639")
V9 = R6 / "policies" / "v9_screen2.py"  # frozen copy of policy_candidates/transfer_policy_v9.py (v9_screen.py + sb_boost_cold)
VARIANTS = {
    "v8": ("transfer", R6 / "policies" / "v8.py"),
    "v7": ("transfer", RES / "round5" / "policies" / "v7.py"),
    "v6": ("transfer", RES / "round5" / "policies" / "v6.py"),
    "v5": ("transfer", RES / "round5" / "policies" / "v5.py"),
    "pid_water": ("pid_water", None),
}
# relative seconds per step (round-5 v8 public runs; v5 ~3x)
SPEED = {"building_train_1": 0.14, "building_train_2": 0.25, "building_train_4": 0.10, "building_train_5": 0.09,
         "building_train_7": 0.037, "building_train_8": 0.035}


def scenarios(set_name: str) -> list[str]:
    d = KB / SETS[set_name]
    if set_name == "pub30":
        return PUBLIC30
    keys = [f"{b.name}/{w.name}" for b in sorted(d.iterdir()) if b.is_dir()
            for w in sorted(b.iterdir()) if (w / "config.gin").exists()]
    if set_name == "r4c":
        keys = [k for k in keys if k.split("/")[0] in FD_BUILDINGS]
    return keys


def make(variant: str, set_name: str, params: str | None, diag: bool, shard: int, prefix: str | None,
         only: list[str] | None, policy_file: str | None) -> list[Path]:
    if variant in VARIANTS:
        pol, pfile = VARIANTS[variant]
    else:
        pol, pfile = "transfer", Path(policy_file).resolve() if policy_file else V9
    ptxt = Path(params).read_text() if params else None
    keys = only or scenarios(set_name)
    jobs = []
    for k in keys:
        b, w = k.split("/")
        jobs.append({"id": f"{variant}/{set_name}/{k}", "tag": f"{variant}/{set_name}", "policy": pol,
                     "policy_path": str(pfile) if pfile else None, "set_dir": SETS[set_name], "building": b,
                     "weather": w, "steps": 8640, "params": ptxt, "save_ts": False,
                     "script": "run_diag.py" if diag else "run_scenario.py"})
    w_of = lambda j: SPEED.get(j["building"], 0.3) * (3.0 if variant == "v5" else 1.0)  # noqa: E731
    jobs.sort(key=w_of, reverse=True)
    n_sh = max(1, -(-len(jobs) // shard))
    shards = [[] for _ in range(n_sh)]
    load = [0.0] * n_sh
    for j in jobs:
        i = min(range(n_sh), key=lambda s: (load[s], len(shards[s])))
        shards[i].append(j)
        load[i] += w_of(j)
    JOBDIR.mkdir(parents=True, exist_ok=True)
    stem = prefix or f"{variant.replace('_', '')}-{set_name}{'-d' if diag else ''}"
    out = []
    for i, sh in enumerate(shards):
        f = JOBDIR / f"{stem}-{i + 1}.json"
        f.write_text(json.dumps(sh, indent=1))
        out.append(f)
        print(f, len(sh), f"load {load[i] * 8640 / 4 / 60:.0f} min (at laptop speed, 4 workers)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--variant", required=True)
    m.add_argument("--set", required=True)
    m.add_argument("--params")
    m.add_argument("--policy-file")
    m.add_argument("--diag", action="store_true")
    m.add_argument("--shard", type=int, default=12)
    m.add_argument("--prefix")
    m.add_argument("--only", nargs="*")
    a = ap.parse_args()
    make(a.variant, a.set, a.params, a.diag, a.shard, a.prefix, a.only, a.policy_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
