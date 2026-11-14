"""Round 10: development table and confirmation against the shipped v11 (PREREG round 10).

Trees (results/round6/runs/<variant>/<set>/<b>/<w>/transfer/summary.json; Mac batches arrive via fetch_mac_r10.sh):
  v11 = r10_v11 on r10hc / r10hh / r10dev (Mac, the shipped file) and r9_dow on pub30 / r7hc / r6hs / r5m / r4c
  (round 9, private Kaggle kernels; bit-identical to the Mac kit and to the shipped file).

    python compare_r10.py dev [--variants r10_d_be ...]        -> results/round10/dev_summary.json
    python compare_r10.py confirm --cand r10_K [--hot]          -> results/round10/confirm_<cand>.json

Paired bootstrap of the mean per-scenario difference of |mean reward| (5,000 resamples, seed 0, 95% percentile CI),
as rounds 6-9 (compare_r6.paired). Ship rule (PREREG round 10, Part 1):
  1. HC3: CI entirely below zero AND wins >= 24/40;
  2. HH: with --hot (candidate has a hot-weather component) the same test; otherwise a guard;
  3. public-30: CI not entirely above zero;
  4. guards (HH without --hot, HS, M, FD): no material regression = not (CI entirely above zero AND mean > +0.20%).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import compare_r6 as c6

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
R10 = RES / "round10"
RUNS = c6.RUNS
V11_NEW = "r10_v11"         # v11 on the round-10 sets (Mac, shipped file)
V11_OLD = "r9_dow"          # v11 on the round-6..9 sets (Kaggle)
DEV6 = ["building_train_1/denver_c3", "building_train_4/fairbanks_c4", "building_train_5/denver_c2",
        "building_train_7/minneapolis_c2", "building_train_8/fairbanks_c3", "building_train_8/minneapolis_c3"]
MATERIAL = 0.0020


def ref_for(set_name: str) -> dict:
    return c6.runs(V11_NEW if set_name.startswith("r10") else V11_OLD, set_name)


def summaries(variant: str, set_name: str) -> dict:
    out = {}
    for f in sorted((RUNS / variant / set_name).glob("building*/*/transfer/summary.json")):
        j = json.loads(f.read_text())
        if j.get("total_steps") != c6.STEPS:
            continue
        n = j["total_steps"]
        out[f"{f.parts[-4]}/{f.parts[-3]}"] = {
            "loss": -j["total_reward"] / n,
            "comfort": -0.6 * j["total_normalized_productivity_regret"] / n,
            "energy": 0.2 * j["total_normalized_energy_cost"] / n,
            "carbon": 0.2 * j["total_normalized_carbon_emission"] / n}
    return out


def station(k: str) -> str:
    w = k.split("/")[1]
    return "cold" if "_c" in w else w.split("_")[0]


def dev(variants: list[str] | None) -> dict:
    if not variants:
        variants = sorted(d.name for d in RUNS.iterdir() if d.name.startswith("r10_") and d.name != V11_NEW
                          and ((d / "r10dev").exists() or (d / "r7hc").exists()))
    ref = {**{k: v for k, v in summaries(V11_OLD, "r7hc").items() if k in DEV6}, **summaries(V11_NEW, "r10dev")}
    out = {"ref": "v11", "variants": {}}
    for v in variants:
        cand = {**{k: x for k, x in summaries(v, "r7hc").items() if k in DEV6}, **summaries(v, "r10dev")}
        keys = sorted(set(cand) & set(ref))
        if not keys:
            continue
        rows = []
        for k in keys:
            c, r = cand[k], ref[k]
            rows.append({"scen": k, "st": station(k), "ref": r["loss"], "cand": c["loss"],
                         "d_pct": 100 * (c["loss"] / r["loss"] - 1),
                         **{f"d_{q}_pct": 100 * (c[q] - r[q]) / r["loss"] for q in ("comfort", "energy", "carbon")}})
        by = {}
        for st in ("cold", "denver", "atlanta", "phoenix", "singapore"):
            rr = [r for r in rows if r["st"] == st]
            if rr:
                by[st] = {"n": len(rr), "mean_pct": sum(r["d_pct"] for r in rr) / len(rr),
                          "wins": sum(r["d_pct"] < 0 for r in rr),
                          "comfort_pct": sum(r["d_comfort_pct"] for r in rr) / len(rr)}
        pr = c6.paired({k: ref[k]["loss"] for k in keys}, {k: cand[k]["loss"] for k in keys})
        pr.pop("per_scenario", None)
        out["variants"][v] = {"n": len(keys), "all": pr, "by_station": by, "rows": rows}
        print(f"\n{v}: n={len(keys)} {c6.fmt(pr)}")
        for st, b in by.items():
            print(f"   {st:9s} n={b['n']:2d} mean {b['mean_pct']:+.2f}%  wins {b['wins']}/{b['n']}  "
                  f"comfort {b['comfort_pct']:+.2f}%")
    R10.mkdir(parents=True, exist_ok=True)
    (R10 / "dev_summary.json").write_text(json.dumps(out, indent=1))
    return out


def material(r: dict | None) -> bool | None:
    if not r:
        return None
    return r["ci_lo"] > 0 and r["rel"] > MATERIAL


def confirm(cand: str, hot: bool, seeds: int = 10) -> dict:
    sets = {"HC3": ("r10hc", None), "HH": ("r10hh", None), "P": ("pub30", None), "HS": ("r6hs", None),
            "M": ("r5m", None), "FD": ("r4c", c6.FD_B)}
    need = {"HC3": 40, "HH": 40, "P": 30, "HS": 18, "M": 12, "FD": 20}
    res = {"cand": cand, "ref": "v11 (shipped, sha256 f9c0ad1a...)", "hot_component": hot, "steps": c6.STEPS,
           "sets": {}}
    pairs = {}
    for s, (sn, keep) in sets.items():
        r, c = ref_for(sn), c6.runs(cand, sn)
        if keep:
            r = {k: v for k, v in r.items() if k.split("/")[0] in keep}
            c = {k: v for k, v in c.items() if k.split("/")[0] in keep}
        pairs[s] = (r, c)
        res["sets"][s] = c6.paired(r, c)
        print(f"{s:4s} {c6.fmt(res['sets'][s])}")
    S = res["sets"]
    complete = {s: bool(S[s]) and S[s]["n"] == need[s] for s in sets}
    res["complete"] = complete
    if all(complete.values()):
        rule = {"hc3_better": S["HC3"]["ci_hi"] < 0 and S["HC3"]["wins"] >= 24,
                "public_not_worse": S["P"]["ci_lo"] <= 0}
        if hot:
            rule["hh_better"] = S["HH"]["ci_hi"] < 0 and S["HH"]["wins"] >= 24
        guards = ["HS", "M", "FD"] + ([] if hot else ["HH"])
        rule["no_material_regression"] = {g: not material(S[g]) for g in guards}
        rule["met"] = (rule["hc3_better"] and rule["public_not_worse"] and rule.get("hh_better", True)
                       and all(rule["no_material_regression"].values()))
        res["rule"] = rule
        res["seed_ci"] = {s: [[100 * q["rel_ci_lo"], 100 * q["rel_ci_hi"]]
                              for q in (c6.paired(*pairs[s], seed=sd) for sd in range(seeds))]
                          for s in ("HC3", "HH", "P")}
        print("rule:", json.dumps(rule))
    else:
        res["rule"] = {"met": None, "note": "incomplete"}
        print("incomplete:", {s: (S[s]["n"] if S[s] else 0) for s in sets})
    R10.mkdir(parents=True, exist_ok=True)
    (R10 / f"confirm_{cand}.json").write_text(json.dumps(res, indent=1))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dev")
    d.add_argument("--variants", nargs="*")
    c = sub.add_parser("confirm")
    c.add_argument("--cand", required=True)
    c.add_argument("--hot", action="store_true")
    a = ap.parse_args()
    if a.cmd == "dev":
        dev(a.variants)
    else:
        confirm(a.cand, a.hot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
