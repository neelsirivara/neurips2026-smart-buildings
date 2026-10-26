"""Numbers for smart_buildings/DEEP_DIVE.md (round 6): where SADR's remaining loss sits, by component and weather.

Reads existing result files only (no simulation):
  results/round4/loss_decomposition_public_v7.json   v7 on the 30 public scenarios (diag runs)
  results/round5/loss_decomposition_r5m_v7.json      v7 on M (shipped six x Minneapolis)
  results/round6/decomp_v8_r6hs.json                 v8 on HS (harsh screening set, Kaggle diag runs)
  results/round6/set_match.json                      v8 level per set and station, Kaggle mixture
  v8 summaries (round-5 laptop pub30, round-6 Kaggle r6hc/r6hs) for the comfort / energy / carbon split per station
Writes results/round6/deep_dive_numbers.json and prints a summary.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
R6 = RES / "round6"
STEPS = 8640


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def comp_split(dirs, policy="transfer"):
    """comfort / energy / carbon shares of the leaderboard loss from summary.json totals, by station."""
    by = defaultdict(lambda: defaultdict(float))
    seen = set()
    for d in dirs:
        for f in sorted(Path(d).glob(f"building*/*/{policy}/summary.json")):
            k = (f.parts[-4], f.parts[-3])
            if k in seen:
                continue
            s = json.loads(f.read_text())
            if s.get("total_steps") != STEPS:
                continue
            seen.add(k)
            w = f.parts[-3]
            st = w.rsplit("_", 1)[0] + ("_cold" if w.rsplit("_", 1)[1].startswith("c") else "")
            comfort = -s["productivity_weight"] * s["total_normalized_productivity_regret"] / STEPS
            energy = s["energy_weight"] * s["total_normalized_energy_cost"] / STEPS
            carbon = s["carbon_weight"] * s["total_normalized_carbon_emission"] / STEPS
            for key in (st, "all"):
                b = by[key]
                b["n"] += 1
                b["metric"] += abs(s["total_reward"]) / STEPS
                b["comfort"] += comfort
                b["energy"] += energy
                b["carbon"] += carbon
    out = {}
    for k, b in by.items():
        n = b["n"]
        tot = b["comfort"] + b["energy"] + b["carbon"]
        out[k] = {"n": int(n), "metric": b["metric"] / n, "comfort_share": b["comfort"] / tot,
                  "energy_share": b["energy"] / tot, "carbon_share": b["carbon"] / tot}
    return out


def decomp_summary(d):
    if not d:
        return None
    o = d["overall"]
    out = {"n": d.get("n_scenarios", d.get("n")), "metric": o["metric"], "shares": o["shares"]}
    bs = d.get("by_station") or {}
    out["by_station"] = {k: {"metric": v.get("metric"), "shares": v.get("shares")} for k, v in bs.items()}
    if "by_hour" in o:
        bh = o["by_hour"]
        if isinstance(bh, dict) and "total" in bh:
            bh = bh["total"]
        if isinstance(bh, list) and len(bh) == 24:
            t = sum(bh)
            out["share_04_07"] = sum(bh[4:7]) / t if t else None
    return out


def main() -> int:
    out = {}
    out["v7_public_decomp"] = decomp_summary(load(RES / "round4" / "loss_decomposition_public_v7.json"))
    out["v7_M_decomp"] = decomp_summary(load(RES / "round5" / "loss_decomposition_r5m_v7.json"))
    out["v8_HS_decomp"] = decomp_summary(load(R6 / "decomp_v8_r6hs.json"))
    sm = load(R6 / "set_match.json") or {}
    out["v8_level_by_set"] = {k: {"n": v["n_v8"], "L_v8": v["L_v8"], "level": v["level"]}
                              for k, v in (sm.get("sets") or {}).items()}
    out["v8_by_station"] = sm.get("v8_by_station")
    out["mixture_P_HC"] = sm.get("mixture_P_HC")
    out["v8_split_public"] = comp_split([RES / "round5" / "full" / "r5_c12_comp" / "pub30"])
    out["v8_split_HC"] = comp_split([R6 / "runs" / "v8" / "r6hc"])
    out["v8_split_HS"] = comp_split([R6 / "runs" / "v8" / "r6hs"])
    lb = load(RES / "kaggle_feedback.json") or {}
    out["kaggle_v8"] = (lb.get("scores_by_policy") or {}).get("v8_r5_c12_comp")
    # Kaggle-weighted component shares: w * L_HC(v8) with HS shares + (1 - w) * L_P(v8) with v7's public shares
    mx = out["mixture_P_HC"] or {}
    lv = out["v8_level_by_set"]
    if mx and "P" in lv and "HC" in lv and out["v7_public_decomp"] and out["v8_HS_decomp"]:
        w = mx["w_HC"]
        partP, partH = (1 - w) * lv["P"]["L_v8"], w * lv["HC"]["L_v8"]
        sp, sh = out["v7_public_decomp"]["shares"], out["v8_HS_decomp"]["shares"]
        comp = {k: partP * sp[k] + partH * sh[k] for k in sp}
        tot = sum(comp.values())
        out["kaggle_weighted_shares"] = {k: v / tot for k, v in comp.items()}
        out["kaggle_weighted_note"] = "public part: v7 public shares (round 4); harsh part: v8 HS shares; weights from mixture_P_HC"
        out["billing_quirk_estimate"] = {"gas_billed_factor": 0.38,
                                         "v8_if_gas_at_0.38": out["kaggle_v8"] * (1 - out["kaggle_weighted_shares"]["gas"] * 0.62)}
        print("Kaggle-weighted shares", {k: round(100 * v, 1) for k, v in out["kaggle_weighted_shares"].items()},
              out["billing_quirk_estimate"])
    (R6 / "deep_dive_numbers.json").write_text(json.dumps(out, indent=1))
    for k in ("v8_split_public", "v8_split_HC", "v8_split_HS"):
        print(k)
        for st, v in sorted(out[k].items(), key=lambda kv: -kv[1]["metric"]):
            print(f"  {st:18s} n={v['n']:2d} metric {v['metric']:.5f} comfort {100 * v['comfort_share']:5.1f}% "
                  f"energy {100 * v['energy_share']:5.1f}% carbon {100 * v['carbon_share']:5.1f}%")
    for k in ("v7_public_decomp", "v7_M_decomp", "v8_HS_decomp"):
        v = out[k]
        if v:
            print(k, f"metric {v['metric']:.5f}", {a: round(100 * b, 1) for a, b in v["shares"].items()},
                  "04-07h share", v.get("share_04_07"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
