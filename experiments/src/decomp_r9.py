"""Round 9: loss decomposition of the shipped v10 on the public 30 and HC2 (coordinator item 1).

Input: the Kaggle run_diag.py outputs merged by kaggle_sim.py into results/round6/runs/v10diag/{pub30,r7hc}/... (diag.csv.gz,
zones.npz, summary.json).  The diag files are unpacked into results/round9/v10diag/<set>/... and passed to the round-3
decompose_loss.py (unchanged), which splits the per-step loss into comfort / fan / cooling / pump / gas.  Also checks
that the diag runs reproduce round 8's v10 confirmation runs (same totals, results/round6/runs/r7L_mbr2/<set>).

    python decomp_r9.py      -> results/round9/decomp_v10_pub30.json, decomp_v10_hc2.json, decomp_r9_summary.json
"""
from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
SRC_RUNS = RES / "round6" / "runs" / "v10diag"
REF_RUNS = RES / "round6" / "runs" / "r7L_mbr2"
OUT = RES / "round9" / "v10diag"


def unpack(set_name: str) -> int:
    n = 0
    for s in sorted((SRC_RUNS / set_name).glob("building_*/*/transfer/summary.json")):
        d = s.parent
        dst = OUT / set_name / d.relative_to(SRC_RUNS / set_name)
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("summary.json", "zones.npz"):
            if (d / f).exists():
                shutil.copyfile(d / f, dst / f)
        if (d / "diag.csv.gz").exists():
            with gzip.open(d / "diag.csv.gz", "rb") as fi, open(dst / "diag.csv", "wb") as fo:
                shutil.copyfileobj(fi, fo)
        n += 1
    return n


def check_ref(set_name: str) -> dict:
    out = {"n": 0, "max_abs_diff": 0.0, "mismatch": []}
    for s in sorted((OUT / set_name).glob("building_*/*/transfer/summary.json")):
        rel = s.relative_to(OUT / set_name)
        r = REF_RUNS / set_name / rel
        if not r.exists():
            continue
        a, b = json.loads(s.read_text())["total_reward"], json.loads(r.read_text())["total_reward"]
        out["n"] += 1
        out["max_abs_diff"] = max(out["max_abs_diff"], abs(a - b))
        if abs(a - b) > 1e-6:
            out["mismatch"].append([str(rel.parent.parent), a, b])
    return out


def main() -> int:
    summ = {}
    for set_name, tag in (("pub30", "pub30"), ("r7hc", "hc2")):
        n = unpack(set_name)
        summ[set_name] = {"unpacked": n, "ref_check": check_ref(set_name)}
        print(set_name, summ[set_name])
        r = subprocess.run([sys.executable, str(HERE / "decompose_loss.py"), "--dirs", str(OUT / set_name),
                            "--policy", "transfer", "--out", str(RES / "round9" / f"decomp_v10_{tag}.json"),
                            "--label", f"v10_{tag}"], capture_output=True, text=True)
        print("\n".join(l for l in r.stdout.splitlines() if not l.strip().startswith("by hour"))[-3000:])
        if r.returncode:
            print(r.stderr[-2000:])
    (RES / "round9" / "decomp_r9_summary.json").write_text(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
