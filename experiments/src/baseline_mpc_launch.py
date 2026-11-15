"""MPC baseline (results/baseline_mpc/PLAN.md): full-length runs of policies_baseline/mpc_rc.py on pub30, r10hc, r10hh.

    python baseline_mpc_launch.py make      # job files only -> results/baseline_mpc/jobs/ (prints them)
    python baseline_mpc_launch.py check     # dry run: make, then validate every job file (no Kaggle, no simulation)
    python baseline_mpc_launch.py enqueue   # make + kaggle_sim.py enqueue (the main session runs this)
    python baseline_mpc_launch.py table     # after the runs: MPC vs v14 vs pid_water per set, paired bootstrap

Variant tag `mpc_rc` (runs land in results/round6/runs/mpc_rc/<set>/<building>/<weather>/transfer/summary.json after
`kaggle_sim.py fetch`). Same job schema, shard balancing and runner as buildup_launch.py (jobs_r6.make); only the job
directory differs, so nothing is written into round6/kaggle_jobs.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
OUT = RES / "baseline_mpc"
POLICY = HERE / "policies_baseline" / "mpc_rc.py"
VARIANT = "mpc_rc"
SETS = ("pub30", "r10hc", "r10hh")
sys.path.insert(0, str(HERE))
import jobs_r6  # noqa: E402

jobs_r6.JOBDIR = OUT / "jobs"   # module global read inside jobs_r6.make; keeps the shared job dir untouched


def make() -> list[Path]:
    files = []
    for s in SETS:
        files += jobs_r6.make(VARIANT, s, None, False, 10, f"mpcrc-{s}", None, str(POLICY))
    (OUT / "jobs" / "policy_sha256.txt").write_text(
        hashlib.sha256(POLICY.read_bytes()).hexdigest() + "  " + POLICY.name + "\n")
    for f in files:
        print(f)
    return files


def check() -> int:
    files = make()
    expect = {s: len(jobs_r6.scenarios(s)) for s in SETS}
    seen = {s: [] for s in SETS}
    need = {"id", "tag", "policy", "policy_path", "set_dir", "building", "weather", "steps", "params", "save_ts", "script"}
    bad = []
    # the queue must not already contain these names (enqueue skips duplicates silently)
    q = jobs_r6.R6 / "kaggle_queue.json"
    queued = {x["name"] for x in json.loads(q.read_text())} if q.exists() else set()
    reg = jobs_r6.R6 / "kaggle_registry.json"
    pushed = set(json.loads(reg.read_text()).get("kernels", {})) if reg.exists() else set()
    for f in files:
        jobs = json.loads(f.read_text())
        if f.stem in queued or f.stem in pushed:
            bad.append(f"{f.name}: name already in queue/registry")
        for j in jobs:
            miss = need - set(j)
            if miss:
                bad.append(f"{f.name}: missing {sorted(miss)}")
            s = j["tag"].split("/")[1]
            seen[s].append(f"{j['building']}/{j['weather']}")
            gin = jobs_r6.KB / j["set_dir"] / j["building"] / j["weather"] / "config.gin"
            if not gin.exists():
                bad.append(f"{f.name}: missing {gin}")
            if Path(j["policy_path"]).resolve() != POLICY.resolve() or j["policy"] != "transfer":
                bad.append(f"{f.name}: wrong policy {j['policy']} {j['policy_path']}")
            if j["steps"] != 8640 or j["params"] is not None or j["tag"] != f"{VARIANT}/{s}":
                bad.append(f"{f.name}: bad steps/params/tag {j['steps']} {j['tag']}")
    for s in SETS:
        if len(seen[s]) != expect[s] or len(set(seen[s])) != expect[s]:
            bad.append(f"{s}: {len(seen[s])} jobs ({len(set(seen[s]))} unique), expected {expect[s]}")
    # the policy must be self-contained (embedded alone in the kernel): numpy + stdlib imports only
    src = POLICY.read_text(encoding="utf-8")
    imports = sorted({ln.split()[1].split(".")[0] for ln in src.splitlines() if ln.startswith(("import ", "from "))})
    if set(imports) - {"__future__", "itertools", "json", "math", "os", "re", "collections", "typing", "numpy"}:
        bad.append(f"policy imports {imports}")
    print(json.dumps({"files": len(files), "jobs": {s: len(seen[s]) for s in SETS}, "policy_imports": imports,
                      "problems": bad}, indent=1))
    return 1 if bad else 0


def enqueue() -> int:
    files = make()
    r = subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                       capture_output=True, text=True, cwd=str(HERE / "kaggle_sim"))
    print(r.stdout[-400:], r.stderr[-400:])
    return r.returncode


def _losses(pattern: str) -> dict:
    out = {}
    for p in RES.glob(pattern):
        s = json.loads(p.read_text())
        if int(s.get("total_steps", 0)) == 8640:
            parts = p.as_posix().split("/")
            out[f"{parts[-4]}/{parts[-3]}"] = (abs(float(s["avg_reward"])),
                                               abs(float(s["total_normalized_productivity_regret"])) * 0.6 / 8640)
    return out


def _ratio(a: dict, b: dict, rng) -> dict:
    keys = sorted(set(a) & set(b))
    if not keys:
        return {"n_paired": 0}
    x = np.array([a[k][0] for k in keys]); y = np.array([b[k][0] for k in keys])
    boots = [x[i].mean() / y[i].mean() for i in (rng.integers(0, len(keys), len(keys)) for _ in range(2000))]
    return {"n_paired": len(keys), "ratio": float(x.mean() / y.mean()),
            "ci95": [float(v) for v in np.percentile(boots, [2.5, 97.5])], "wins": int((x < y).sum())}


def table() -> int:
    rng = np.random.default_rng(20261116)
    res = {}
    for s in SETS:
        mpc = _losses(f"round6/runs/{VARIANT}/{s}/*/*/transfer/summary.json")
        v14 = _losses(f"round6/runs/struct_HA/{s}/*/*/transfer/summary.json")
        pw = _losses("final/*/*/pid_water/summary.json" if s == "pub30"
                     else f"round6/runs/pid_water/{s}/*/*/pid_water/summary.json")
        row = {}
        for n, d in (("mpc_rc", mpc), ("v14", v14), ("pid_water", pw)):
            row[n] = {"n": len(d), "loss": float(np.mean([v[0] for v in d.values()])) if d else None,
                      "comfort_part": float(np.mean([v[1] for v in d.values()])) if d else None}
        row["mpc_over_v14"] = _ratio(mpc, v14, rng)
        row["mpc_over_pid_water"] = _ratio(mpc, pw, rng)
        res[s] = row
    (OUT / "table.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit({"make": lambda: (make(), 0)[1], "check": check, "enqueue": enqueue, "table": table}[sys.argv[1]]())
