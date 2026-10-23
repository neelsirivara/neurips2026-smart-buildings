"""Assemble the paper's result trees after round 3 (one machine, the Mac, for every policy).

    results/final/<b>/<w>/            30 public scenarios
        transfer       the round-3 policy (v6), from results/mac/round3/<FINAL_NEW[public]>
        transfer_v5    the v5 policy (previous final), moved from the old `transfer` directory
        transfer_v4, pid_water, pid, fixed_setpoint, bang_bang   unchanged
    results/final_heldout/<b>/<w>/    10 generated held-out scenarios (buildings 0501, 0502)
        transfer (v6), transfer_v5 (old transfer), transfer_v4, pid_water   as above
    results/final_heldout_r3/<b>/<w>/ 30 new held-out scenarios (6 generated buildings, round 3)
        transfer (v6), transfer_v5 and pid_water from results/mac/round3/diag_v5_r3

All files of a run directory are copied (summary.json, timeseries.csv, diag.csv, zones.npz); a
stale ahu_log.csv left in a replaced `transfer` directory is removed. Idempotent.

Usage:  python assemble_round3_tree.py [--new-public DIR --new-heldout DIR --new-r3 DIR]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parents[0] / "results"
MAC3 = RES / "mac" / "round3"
FINAL_NEW = {"public": "final_v6_public", "heldout": "final_v6_heldout", "r3": "final_v6_r3"}


def copy_run(src: Path, dst: Path, clean: bool = True) -> bool:
    if not (src / "summary.json").exists():
        return False
    if clean and dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    return True


def promote_old_transfer(tree: Path) -> int:
    """`transfer` (v5, previous final) -> `transfer_v5`, once."""
    n = 0
    for f in tree.glob("building_*/*/transfer/summary.json"):
        d = f.parent
        v5 = d.parent / "transfer_v5"
        if not (v5 / "summary.json").exists():
            if copy_run(d, v5):
                n += 1
    return n


def install_new(tree: Path, new_dir: Path, policy_src: str = "transfer") -> int:
    n = 0
    for f in sorted(new_dir.glob(f"building_*/*/{policy_src}/summary.json")):
        dst = tree / f.parts[-4] / f.parts[-3] / "transfer"
        if copy_run(f.parent, dst):
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-public", default=FINAL_NEW["public"])
    ap.add_argument("--new-heldout", default=FINAL_NEW["heldout"])
    ap.add_argument("--new-r3", default=FINAL_NEW["r3"])
    a = ap.parse_args()
    final, held, r3 = RES / "final", RES / "final_heldout", RES / "final_heldout_r3"
    print("public:  promoted v5 ->", promote_old_transfer(final), "scenarios")
    print("heldout: promoted v5 ->", promote_old_transfer(held), "scenarios")
    for tree, sub in ((final, a.new_public), (held, a.new_heldout)):
        src = MAC3 / sub
        if src.exists():
            print(f"{tree.name}: installed new transfer from {src.relative_to(RES)}:", install_new(tree, src), "scenarios")
        else:
            print(f"{tree.name}: {src.relative_to(RES)} not fetched yet; `transfer` left as is")
    src3 = MAC3 / a.new_r3
    if src3.exists():
        print("r3: installed new transfer:", install_new(r3, src3), "scenarios")
    else:
        print(f"r3: {src3.relative_to(RES)} not fetched yet")
    d5 = MAC3 / "diag_v5_r3"
    if d5.exists():
        n5 = n_pw = 0
        for f in sorted(d5.glob("building_*/*/transfer/summary.json")):
            n5 += copy_run(f.parent, r3 / f.parts[-4] / f.parts[-3] / "transfer_v5")
        for f in sorted(d5.glob("building_*/*/pid_water/summary.json")):
            n_pw += copy_run(f.parent, r3 / f.parts[-4] / f.parts[-3] / "pid_water")
        print(f"r3: transfer_v5 {n5}, pid_water {n_pw} scenarios from diag_v5_r3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
