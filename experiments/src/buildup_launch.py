"""Cumulative build-up (results/buildup/PLAN.md): arms B1-B4 on the public 30 as private Kaggle kernels.

    python buildup_launch.py make       # job files only
    python buildup_launch.py enqueue    # make + kaggle_sim.py enqueue
    python buildup_launch.py table      # summary of every arm with paired bootstrap steps (after the runs)

B0 = v14 (round6/runs/struct_HA/pub30, bit-reproducible); P = pid_water (final/*/*/pid_water). This first pass runs on
the CURRENT kit as a dry run of the arms; the round-2 kit rerun uses the same command after the kit is updated.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
BU = RES / "buildup"
POLICY = ROOT / "submission" / "candidates" / "transfer_policy_v14.py"
sys.path.insert(0, str(HERE))
import jobs_r6  # noqa: E402

ARMS = ["bu1_no_refinements", "bu2_no_building_awareness", "bu3_no_coldest_air", "bu4_no_idling"]


def make() -> list[Path]:
    files = []
    for arm in ARMS:
        files += jobs_r6.make(arm, "pub30", str(BU / "params" / f"{arm}.json"), False, 10, None, None, str(POLICY))
    for f in files:
        print(f)
    return files


def make_harsh() -> list[Path]:
    """Cold (r10hc, 40) and hot (r10hh, 40) sets: pid_water and the design-fact arms first, then the rest."""
    files = []
    order = ["pid_water", "bu3_no_coldest_air", "bu4_no_idling", "bu1_no_refinements", "bu2_no_building_awareness"]
    for arm in order:
        for s in ("r10hc", "r10hh"):
            if arm == "pid_water":
                files += jobs_r6.make("pid_water", s, None, False, 10, None, None, None)
            else:
                files += jobs_r6.make(arm, s, str(BU / "params" / f"{arm}.json"), False, 10, None, None, str(POLICY))
    for f in files:
        print(f)
    return files


def enqueue_harsh() -> int:
    files = make_harsh()
    r = subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                       capture_output=True, text=True, cwd=str(HERE / "kaggle_sim"))
    print(r.stdout[-400:], r.stderr[-400:])
    return r.returncode


def enqueue() -> int:
    files = make()
    r = subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                       capture_output=True, text=True, cwd=str(HERE / "kaggle_sim"))
    print(r.stdout[-400:], r.stderr[-400:])
    return r.returncode


def losses(pattern: str) -> dict:
    out = {}
    for p in RES.glob(pattern):
        s = json.loads(p.read_text())
        if int(s.get("total_steps", 0)) == 8640:
            parts = p.as_posix().split("/")
            out[f"{parts[-4]}/{parts[-3]}"] = abs(float(s["avg_reward"]))
    return out


def table() -> int:
    res = {s: table_set(s) for s in ("pub30", "r10hc", "r10hh")}
    (BU / "table.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def table_set(s: str) -> list:
    rows = [("B0 final (v14)", f"round6/runs/struct_HA/{s}/*/*/transfer/summary.json")]
    rows += [(a, f"round6/runs/{a}/{s}/*/*/transfer/summary.json") for a in ARMS]
    rows += [("P pid_water", "final/*/*/pid_water/summary.json" if s == "pub30" else f"round6/runs/pid_water/{s}/*/*/pid_water/summary.json")]
    data = [(n, losses(g)) for n, g in rows]
    rng = np.random.default_rng(20261115)
    out = []
    prev = None
    b0 = data[0][1]
    p = data[-1][1]
    gap = np.mean(list(p.values())) - np.mean(list(b0.values()))
    for n, d in data:
        rec = {"arm": n, "n": len(d), "loss": float(np.mean(list(d.values()))) if d else None}
        if prev is not None and d and prev[1]:
            keys = sorted(set(d) & set(prev[1]))
            a = np.array([d[k] for k in keys]); b = np.array([prev[1][k] for k in keys])
            boots = [(a[i].mean() / b[i].mean()) for i in (rng.integers(0, len(keys), len(keys)) for _ in range(2000))]
            rec.update({"step_ratio": float(a.mean() / b.mean()), "step_ci": [float(x) for x in np.percentile(boots, [2.5, 97.5])],
                        "gap_share_of_step": float((a.mean() - b.mean()) / gap) if gap else None})
        out.append(rec)
        prev = (n, d)
    return out


if __name__ == "__main__":
    sys.exit({"make": lambda: (make(), 0)[1], "enqueue": enqueue, "enqueue-harsh": enqueue_harsh,
              "table": table}[sys.argv[1]]())
