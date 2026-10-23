"""Assemble the paper's primary result trees from the Mac runs (one machine for every policy).

    results/final/<building>/<weather>/<policy>/summary.json
        transfer      the final policy (v5 winner), from results/mac/final (run with --save-ts)
        transfer_v4   the baked v4 policy, from results/mac/full
        pid_water     from results/mac/final (same batch as the final policy, with --save-ts)
        pid, fixed_setpoint, bang_bang   from results/mac/full
    results/final_heldout/<building>/<weather>/<policy>/summary.json
        transfer (v5 winner) and pid_water from results/mac/final_heldout, transfer_v4 from
        results/mac/heldout

Time series (timeseries.csv, ahu_log.csv) are copied too when present, so analyze_final.py and
the trace figure can run on the final tree. Existing files are overwritten.

Usage:  python assemble_final_tree.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parents[0] / "results"
FILES = ("summary.json", "timeseries.csv", "ahu_log.csv")


def copy_policy(src_tree: Path, src_policy: str, dst_tree: Path, dst_policy: str) -> int:
    n = 0
    for f in src_tree.glob(f"building_*/*/{src_policy}/summary.json"):
        d = dst_tree / f.parts[-4] / f.parts[-3] / dst_policy
        d.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            s = f.parent / name
            if s.exists():
                shutil.copy2(s, d / name)
        n += 1
    print(f"  {src_tree.relative_to(RES)}/{src_policy} -> {dst_tree.relative_to(RES)}/{dst_policy}: {n} scenarios")
    return n


def main() -> int:
    final, held = RES / "final", RES / "final_heldout"
    print("public scenarios:")
    copy_policy(RES / "mac" / "final", "transfer", final, "transfer")
    copy_policy(RES / "mac" / "final", "pid_water", final, "pid_water")
    copy_policy(RES / "mac" / "full", "transfer", final, "transfer_v4")
    for pol in ("pid", "fixed_setpoint", "bang_bang"):
        copy_policy(RES / "mac" / "full", pol, final, pol)
    print("held-out scenarios:")
    copy_policy(RES / "mac" / "final_heldout", "transfer", held, "transfer")
    copy_policy(RES / "mac" / "final_heldout", "pid_water", held, "pid_water")
    copy_policy(RES / "mac" / "heldout", "transfer", held, "transfer_v4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
