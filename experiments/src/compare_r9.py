"""Round 9: screens and confirmation against the shipped v10 (PREREG round 9).

v10 runs = round 8's r7L_mbr2 runs (results/round6/runs/r7L_mbr2/<set>/...: pub30, r7hc, r6hs, r5m, r4c), which the
shipped file reproduces bit for bit (results/round8/xcheck_shipped_v10.json).  Candidates: results/round6/runs/<cand>/
<set>/... (Kaggle shards merge there; Mac batches are merged by fetch_mac_r9.py).

    python compare_r9.py screen --cands r9_a r9_b           -> results/round9/screen_summary.json
    python compare_r9.py confirm --cand r9_x                -> results/round9/confirm_<cand>.json

Paired bootstrap of the mean per-scenario difference of |mean reward| (5,000 resamples, seed 0, 95% percentile CI),
as rounds 6-8 (compare_r6.paired).  Ship rule (PREREG): public-30 CI not entirely above zero AND HC2 CI entirely
below zero; reported either way: HS, M, FD (FD_B buildings), CI over bootstrap seeds 0-9, wins, worst scenarios.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import compare_r6 as c6

HERE = Path(__file__).resolve().parent
R9 = HERE.parent / "results" / "round9"
REF = "r7L_mbr2"                                   # v10


def runs(cand: str, set_name: str) -> dict:
    return c6.runs(cand, set_name)


def ref(set_name: str) -> dict:
    return c6.runs(REF, set_name)


def screen(cands: list[str]) -> dict:
    out = {"ref": "v10 (r7L_mbr2)", "sets": {"HS": "r6hs (18)", "P": "pub30 (30)"}, "cands": {}}
    for c in cands:
        hs = c6.paired(ref("r6hs"), runs(c, "r6hs"))
        pub = c6.paired(ref("pub30"), runs(c, "pub30"))
        out["cands"][c] = {"HS": hs, "P": pub, "class": c6.classify(hs, pub) if hs and pub else None}
        print(f"{c:12s} HS {c6.fmt(hs)}\n{'':12s} P  {c6.fmt(pub)}   -> {out['cands'][c]['class']}")
    R9.mkdir(parents=True, exist_ok=True)
    (R9 / "screen_summary.json").write_text(json.dumps(out, indent=1))
    return out


def confirm(cand: str) -> dict:
    sets = {"P": ("pub30", None), "HC2": ("r7hc", None), "HS": ("r6hs", None), "M": ("r5m", None),
            "FD": ("r4c", c6.FD_B)}
    res = {"cand": cand, "ref": "v10 (r7L_mbr2)", "steps": c6.STEPS, "sets": {}}
    pairs = {}
    for s, (sn, keep) in sets.items():
        r, c = ref(sn), runs(cand, sn)
        if keep:
            r = {k: v for k, v in r.items() if k.split("/")[0] in keep}
            c = {k: v for k, v in c.items() if k.split("/")[0] in keep}
        pairs[s] = (r, c)
        res["sets"][s] = c6.paired(r, c)
        print(f"{s:4s} {c6.fmt(res['sets'][s])}")
    p, h = res["sets"]["P"], res["sets"]["HC2"]
    if p and h and p["n"] == 30 and h["n"] == 44:
        res["rule"] = {"public_not_worse": p["ci_lo"] <= 0, "hc2_better": h["ci_hi"] < 0}
        res["rule"]["met"] = res["rule"]["public_not_worse"] and res["rule"]["hc2_better"]
        res["seed_ci"] = {s: [[q["ci_lo"], q["ci_hi"]] for q in (c6.paired(*pairs[s], seed=sd) for sd in range(10))]
                          for s in ("P", "HC2")}
        print("rule:", res["rule"])
    else:
        res["rule"] = {"met": None, "note": "incomplete"}
        print("incomplete:", {s: (v["n"] if v else 0) for s, v in res["sets"].items()})
    R9.mkdir(parents=True, exist_ok=True)
    (R9 / f"confirm_{cand}.json").write_text(json.dumps(res, indent=1))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("screen")
    s1.add_argument("--cands", nargs="+", required=True)
    s2 = sub.add_parser("confirm")
    s2.add_argument("--cand", required=True)
    a = ap.parse_args()
    if a.cmd == "screen":
        screen(a.cands)
    else:
        confirm(a.cand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
