"""Round 4: if the confirmed candidate met the ship rule, assemble results/final_r4 for the official scorer.

    results/final_r4/<b>/<w>/transfer        the shipped v7 runs (results/[mac/]round4/full/<cand>/pub30)
    results/final_r4/<b>/<w>/<baseline>      pid_water, pid, fixed_setpoint, bang_bang copied from results/final

The round-3 trees (results/final, final_heldout, final_heldout_r3) stay as they are (transfer = v6), so the
round-3 numbers of the paper do not change meaning. Idempotent; does nothing when the rule was not met.
Then runs kit/score_leaderboard.py on results/final_r4 -> results/score_leaderboard_final_r4.txt.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
BASELINES = ("pid_water", "pid", "fixed_setpoint", "bang_bang")


def copy_run(src: Path, dst: Path) -> bool:
    if not (src / "summary.json").exists():
        return False
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    return True


def main() -> int:
    dec = json.loads((RES / "round4" / "decision.json").read_text())
    cand = dec.get("chosen")
    conf = json.loads((RES / "round4" / f"confirm_{cand}.json").read_text()) if cand else {}
    if not conf.get("ship_rule_met"):
        print(f"round 4: ship rule not met for {cand}; results/final_r4 not assembled")
        return 0
    tree = RES / "final_r4"
    n = nb = 0
    for base in (RES / "round4" / "full" / cand / "pub30", RES / "mac" / "round4" / "full" / cand / "pub30"):
        for f in sorted(base.glob("building_*/*/transfer/summary.json")):
            b, w = f.parts[-4], f.parts[-3]
            if copy_run(f.parent, tree / b / w / "transfer"):
                n += 1
                for bl in BASELINES:
                    nb += copy_run(RES / "final" / b / w / bl, tree / b / w / bl)
    print(f"results/final_r4: {n} transfer (v7) runs, {nb} baseline runs")
    kit = ROOT / "kit"
    py = kit / ".venv" / "Scripts" / "python.exe"
    if not py.exists():
        py = kit / ".venv" / "bin" / "python"
    out = RES / "score_leaderboard_final_r4.txt"
    r = subprocess.run([str(py), "score_leaderboard.py", str(tree), "--policy", "transfer", "--expect", "30"],
                       cwd=str(kit), capture_output=True, text=True)
    out.write_text((r.stdout or "") + (r.stderr or ""))
    for line in (r.stdout or "").splitlines():
        if "LEADERBOARD" in line:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
