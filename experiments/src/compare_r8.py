"""Round 8: confirmation of r7L_mbr2 against the shipped v9 under the rule of results/round8/PREREG.md.

Same computation as compare_r7.confirm (paired bootstrap of the mean per-scenario difference, 5,000 resamples, seed 0;
rule = public-30 CI not entirely above zero AND HC2 CI entirely below zero; seed_ci = seeds 0-9), written to
results/round8/confirm_r7L_mbr2.json. Secondaries (HS, M, FD; HC was not run) are reported when present.

    python compare_r8.py            -> results/round8/confirm_r7L_mbr2.json and a printed summary
"""
from __future__ import annotations

import json
from pathlib import Path

import compare_r7 as c7

HERE = Path(__file__).resolve().parent
R8 = HERE.parent / "results" / "round8"
CAND = "r7L_mbr2"


def main() -> int:
    R8.mkdir(parents=True, exist_ok=True)
    c7.R7 = R8                      # compare_r7.confirm writes confirm_<cand>.json into its module-level R7
    res = c7.confirm(CAND)
    for s, r in res["sets"].items():
        if r:
            print(f"  {s:4s} worst {r['worst']} {100 * r['worst_rel']:+.2f}%")
    print(json.dumps(res.get("rule"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
