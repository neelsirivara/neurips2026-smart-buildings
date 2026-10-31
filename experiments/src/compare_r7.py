"""Round 7: screen, decision and confirmation against the shipped v9 (PREREG round 7).

v9 runs = round 6's r6_comp runs (results/round6/runs/r6_comp/<set>/...; v9 on HC2 = r6_comp/r7hc, run in round 7).
Candidates: results/round6/runs/<cand>/<set>/... (Kaggle shards and Mac batches merge there).

    python compare_r7.py checks                  -> results/round7/checks_r7.json (short runs vs predictions)
    python compare_r7.py screen                  -> results/round7/screen_summary.json
    python compare_r7.py decide                  -> results/round7/decision.json
    python compare_r7.py confirm --cand r7_xxx   -> results/round7/confirm_<cand>.json
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import compare_r6 as c6

HERE = Path(__file__).resolve().parent
R7 = HERE.parent / "results" / "round7"
REF = "r6_comp"                                  # v9
CANDS = ["r7_base", "r7_mbr", "r7_mbf", "r7_mb"]


ALIAS = {"r7_base": "r6_compb"}                 # identical parameters; v10 code with the round-7 switches off = v9 code


def runs(cand: str, set_name: str) -> dict:
    out = dict(c6.runs(ALIAS[cand], set_name)) if cand in ALIAS else {}
    out.update(c6.runs(cand, set_name))
    return out


def ref(set_name: str) -> dict:
    return c6.runs(REF, set_name)


def screen() -> dict:
    out = {"ref": "v9 (r6_comp)", "sets": {"HS": "r6hs (18)", "P": "pub30 (30)"}, "cands": {}}
    for c in CANDS:
        hs = c6.paired(ref("r6hs"), runs(c, "r6hs"))
        pub = c6.paired(ref("pub30"), runs(c, "pub30"))
        hs_b = c6.paired(runs("r7_base", "r6hs"), runs(c, "r6hs")) if c != "r7_base" else None
        pub_b = c6.paired(runs("r7_base", "pub30"), runs(c, "pub30")) if c != "r7_base" else None
        out["cands"][c] = {"HS": hs, "P": pub, "HS_vs_base": hs_b, "P_vs_base": pub_b,
                           "class": c6.classify(hs, pub)}
        print(f"{c:10s} HS {c6.fmt(hs)}\n{'':10s} P  {c6.fmt(pub)}   -> {out['cands'][c]['class']}")
        if hs_b:
            print(f"{'':10s} vs base: HS {c6.fmt(hs_b)} | P {c6.fmt(pub_b)}")
    (R7 / "screen_summary.json").write_text(json.dumps(out, indent=1))
    return out


def decide() -> dict:
    sc = json.loads((R7 / "screen_summary.json").read_text())["cands"]
    complete = {c: v for c, v in sc.items() if v["HS"] and v["P"] and v["HS"]["n"] == 18 and v["P"]["n"] == 30}
    pool = {c: v["HS"]["cand"] for c, v in complete.items() if v["class"] == "helps"}
    out = {"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "classes": {c: v["class"] for c, v in sc.items()}, "complete": sorted(complete),
           "pool_hs_metric": pool, "chosen": min(pool, key=pool.get) if pool else None}
    (R7 / "decision.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


def confirm(cand: str) -> dict:
    sets = {"P": ("pub30", None), "HC2": ("r7hc", None), "HS": ("r6hs", None), "HC": ("r6hc", None),
            "M": ("r5m", None), "FD": ("r4c", c6.FD_B)}
    res = {"cand": cand, "ref": "v9 (r6_comp)", "steps": c6.STEPS, "sets": {}}
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
                          for s in ("P", "HC2") }
        print("rule:", res["rule"])
    else:
        res["rule"] = {"met": None, "note": "incomplete"}
        print("incomplete:", {s: (v["n"] if v else 0) for s, v in res["sets"].items()})
    (R7 / f"confirm_{cand}.json").write_text(json.dumps(res, indent=1))
    return res


def _gas_kwh(d: Path) -> dict | None:
    f = d / "diag.csv.gz" if (d / "diag.csv.gz").exists() else d / "diag.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f)
    s = json.loads((d / "summary.json").read_text())
    return {"gas_kwh": float(df.gas_w.sum() * 300.0 / 3.6e6), "reward": float(s["total_reward"]),
            "regret": float(s["total_normalized_productivity_regret"]), "steps": int(s["total_steps"])}


def checks() -> dict:
    """The short (7-day) check runs of v9 parameter changes against analysis_r7.py's predictions."""
    an = json.loads((R7 / "analysis_r7.json").read_text())["predictions_7d"]
    root = c6.RUNS
    out = {}
    for scen in ("building_train_8/fairbanks_c2", "building_train_7/denver_c1", "building_train_1/fairbanks_c2"):
        b, w = scen.split("/")
        base = _gas_kwh(root / "r7chk_v9" / "r6hs" / b / w / "transfer")
        if not base:
            continue
        row = {"v9": base}
        key = f"{b}__{w}"
        for v, pk in (("r7chk_nle12", "pred_rel_nle12"), ("r7chk_nle14", "pred_rel_nle14"),
                      ("r7chk_ls115", "pred_rel_ls115"), ("r7chk_ls100", "pred_rel_ls100")):
            g = _gas_kwh(root / v / "r6hs" / b / w / "transfer")
            if not g:
                continue
            row[v] = {**g, "meas_rel_gas": g["gas_kwh"] / base["gas_kwh"] - 1.0,
                      "meas_rel_loss": abs(g["reward"]) / abs(base["reward"]) - 1.0,
                      "meas_regret_change": g["regret"] - base["regret"],
                      "pred_rel_gas": an.get(key, {}).get(pk)}
        out[scen] = row
        print(scen, {k: (round(100 * v["meas_rel_gas"], 2), round(100 * (v["pred_rel_gas"] or 0), 2),
                         round(100 * v["meas_rel_loss"], 2)) for k, v in row.items() if k != "v9"})
    (R7 / "checks_r7.json").write_text(json.dumps(out, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("checks")
    sub.add_parser("screen")
    sub.add_parser("decide")
    c = sub.add_parser("confirm")
    c.add_argument("--cand", required=True)
    a = ap.parse_args()
    if a.cmd == "checks":
        checks()
    elif a.cmd == "screen":
        screen()
    elif a.cmd == "decide":
        decide()
    else:
        confirm(a.cand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
