"""Round 6: full-length confirmation shards for the chosen candidate C* (PREREG part 2): HC (48), the public scenarios
it has not run yet (to complete public-30), r5m (12) and FD (20, round-4 fresh default-range buildings).

    python confirm_jobs_r6.py r6_cXX [--sets r6hc,pub30,r5m,r4c] [--front]
Skips scenarios that already have an 8,640-step summary for the candidate. Required by the ship rule: r6hc and pub30.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import jobs_r6
from compare_r6 import runs

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cand")
    ap.add_argument("--sets", default="r6hc,pub30,r5m,r4c")
    ap.add_argument("--front", action="store_true")
    ap.add_argument("--shard", type=int, default=12)
    ap.add_argument("--policy-file", default=None)
    a = ap.parse_args()
    params = str(HERE / "policy_candidates" / f"{a.cand}.json")
    short = a.cand.split("_")[1]
    files = []
    for s in a.sets.split(","):
        have = set(runs(a.cand, s))
        todo = [k for k in jobs_r6.scenarios(s) if k not in have]
        if not todo:
            continue
        files += jobs_r6.make(a.cand, s, params, False, a.shard, f"{short}-conf-{s}", todo, a.policy_file)
    if not files:
        print("nothing to run")
        return 0
    cmd = [sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)]
    if a.front:
        cmd.append("--front")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
