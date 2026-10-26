"""Round 6: make and enqueue the screen shards of the given candidates (PREREG part 2): r6hs (18) + pub12, 8,640 steps.

    python screen_jobs_r6.py r6_c01_boost8 r6_c02_boost4 ... [--front] [--sets r6hs,pub12] [--shard 10]
Each candidate = transfer_policy_v9.py + policy_candidates/<cand>.json. Shards mix nothing: one candidate per shard.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import jobs_r6
from compare_r6 import PUB12

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="+")
    ap.add_argument("--front", action="store_true")
    ap.add_argument("--sets", default="r6hs,pub12")
    ap.add_argument("--shard", type=int, default=10)
    ap.add_argument("--policy-file", default=None)
    a = ap.parse_args()
    files: list[Path] = []
    for c in a.cands:
        params = str(HERE / "policy_candidates" / f"{c}.json")
        short = c.split("_")[1] if c.startswith("r6_") else c       # r6_c01_boost8 -> c01
        for s in a.sets.split(","):
            if s == "pub12":
                files += jobs_r6.make(c, "pub30", params, False, a.shard, f"{short}-pub12", PUB12, a.policy_file)
            else:
                files += jobs_r6.make(c, s, params, False, a.shard, f"{short}-{s}", None, a.policy_file)
    cmd = [sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)]
    if a.front:
        cmd.append("--front")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
