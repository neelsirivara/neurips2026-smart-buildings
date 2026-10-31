"""Round-8 macros (called from make_macros.py). Missing inputs -> \\textbf{??}.

Inputs: results/round8/confirm_r7L_mbr2.json (compare_r8.py), results/kaggle_feedback.json (probe of v10 if shipped).
"""
from __future__ import annotations

import json
from pathlib import Path

from make_macros_r7 import MISSING, f, load, macro, pabs

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
R8 = RES / "round8"
SETS = (("P", "Pub"), ("HC2", "HarshCTwo"), ("HS", "HarshS"), ("M", "Minn"), ("FD", "FreshDef"))


def round8_macros() -> list[str]:
    c = load(R8 / "confirm_r7L_mbr2.json") or {}
    L = []
    for s, sn in SETS:
        r = (c.get("sets") or {}).get(s) or {}
        L.append(macro(f"REigConf{sn}N", r.get("n", MISSING)))
        L.append(macro(f"REigConf{sn}Ref", f(r.get("ref"), 5)))
        L.append(macro(f"REigConf{sn}Cand", f(r.get("cand"), 5)))
        L.append(macro(f"REigConf{sn}Rel", f(r.get("rel"), 1, pct=True, signed=True)))
        L.append(macro(f"REigConf{sn}RelAbs", pabs(r.get("rel"))))
        L.append(macro(f"REigConf{sn}RelLo", f(r.get("rel_ci_lo"), 1, pct=True, signed=True)))
        L.append(macro(f"REigConf{sn}RelHi", f(r.get("rel_ci_hi"), 1, pct=True, signed=True)))
        L.append(macro(f"REigConf{sn}RelLoAbs", pabs(r.get("rel_ci_lo"))))
        L.append(macro(f"REigConf{sn}RelHiAbs", pabs(r.get("rel_ci_hi"))))
        L.append(macro(f"REigConf{sn}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
        L.append(macro(f"REigConf{sn}WorstRel", f(r.get("worst_rel"), 1, pct=True, signed=True)))
    # public-30 per-station means of the candidate (Table 1 row if it ships)
    ps = ((c.get("sets") or {}).get("P") or {}).get("per_scenario") or {}
    for st in ("fairbanks", "denver", "atlanta", "phoenix", "singapore"):
        v = [x["cand"] for k, x in ps.items() if k.split("/")[1].rsplit("_", 1)[0] == st]
        L.append(macro(f"REigConfPubCand{st.capitalize()}", f(sum(v) / len(v), 5) if len(v) == 6 else MISSING))
    rule = c.get("rule") or {}
    L.append(macro("REigRuleMet", {True: "met", False: "not met"}.get(rule.get("met"), MISSING)))
    sc = c.get("seed_ci") or {}
    if sc.get("HC2"):
        n_below = sum(1 for lo, hi in sc["HC2"] if hi < 0)
        n_pub = sum(1 for lo, hi in sc.get("P", []) if lo <= 0)
        L.append(macro("REigSeedHCTwoBelow", f"{n_below}/{len(sc['HC2'])}"))
        L.append(macro("REigSeedPubNotWorse", f"{n_pub}/{len(sc.get('P', []))}"))
    else:
        L += [macro("REigSeedHCTwoBelow", MISSING), macro("REigSeedPubNotWorse", MISSING)]
    b9 = load(RES / "tune" / "best_params_v9.json") or {}
    L.append(macro("REigVNineLeadSafety", f"{b9['lead_safety']:g}" if "lead_safety" in b9 else MISSING))
    L.append(macro("REigVNineMarginPre", f"{b9['margin_pre']:g}" if "margin_pre" in b9 else MISSING))
    b10 = load(RES / "tune" / "best_params_v10.json") or {}
    L.append(macro("REigMbrSafety", f"{b10['mbr_safety']:g}" if "mbr_safety" in b10 else MISSING))
    fb = load(RES / "kaggle_feedback.json") or {}
    sc10 = (fb.get("scores_by_policy") or {}).get("v10_r7L_mbr2")
    probed = any(s.get("label") == "v10_r7L_mbr2" for s in fb.get("submissions", []))
    L.append(macro("REigKagVTen", f(sc10, 5) if sc10 is not None else ("pending" if probed else MISSING)))
    return L


if __name__ == "__main__":
    ls = round8_macros()
    print("".join(ls))
    print(sum(1 for x in ls if MISSING in x), "missing of", len(ls))
