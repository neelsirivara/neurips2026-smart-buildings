"""Ablation of the tuned SADR configuration on the tuning screening set.

Starting from the best configuration found by tune.py (results/tune/best_params.json),
each parameter that differs from the policy's untuned default is reverted on its own,
and the resulting configuration is scored on the six screening scenarios at 1,440 steps
with tune.evaluate (cached: a configuration already in tune_log.json is not re-run).
Also scores "default + single change" for each differing parameter, so the table shows
both the loss from removing a change and the gain from adding it alone.

Writes results/tune/ablation.json:
    {"best": {...}, "default": {...}, "rows": [{"macro", "label", "param", "value",
      "score", "rel_vs_best", "rel_vs_default"}, ...]}

Usage:  python ablation.py --workers 4
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import tune

MACRO_NAMES = {"ki_w_per_k_step": "Ki", "margin_pre": "MarginPre", "sat_mix_floor": "SatMix",
               "sb_hyst_k": "SbHyst", "margin_occ": "MarginOcc", "night_low_ext": "NightLow",
               "night_high_ext": "NightHigh", "lead_safety": "LeadSafety", "min_on_steps": "MinOn",
               "kq_w_per_k": "Kq", "sat_cool_hi": "SatCoolHi", "q_sb_w": "QSb", "lead_max_h": "LeadMax",
               "rate0_kph": "RateZero", "holiday_check_h": "Holiday", "heat_season_steps": "HeatSeason",
               "disch_margin_k": "Disch"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--steps", type=int, default=1440)
    a = ap.parse_args()
    log = tune.load_log()
    best = json.loads((tune.TUNE_DIR / "best_params.json").read_text())
    base = tune.default_params()
    # the policy file now carries the tuned values, so the untuned default is reconstructed
    # from the tuning log's is_default record (the values the random search started from)
    dflt_rec = next((v for v in log["evals"].values() if v.get("is_default")), None)
    if dflt_rec is not None:
        base = dict(dflt_rec["params"])
    diff = {k: (base[k], best[k]) for k in best if base.get(k) != best[k]}
    print("tuned parameters:", diff)
    s_best = tune.evaluate(dict(best), a.steps, a.workers, log)
    s_base = tune.evaluate(dict(base), a.steps, a.workers, log)
    rows = []
    for k, (v_base, v_best) in diff.items():
        m = MACRO_NAMES.get(k, k.replace("_", "").title())
        p = dict(best)
        p[k] = v_base
        s_rev = tune.evaluate(p, a.steps, a.workers, log)
        rows.append({"macro": f"Rev{m}", "label": f"best with {k} reverted to {v_base:g}", "param": k,
                     "value": v_base, "score": s_rev,
                     "rel_vs_best": None if s_rev is None or not s_best else s_rev / s_best - 1.0,
                     "rel_vs_default": None if s_rev is None or not s_base else s_rev / s_base - 1.0})
        p = dict(base)
        p[k] = v_best
        s_add = tune.evaluate(p, a.steps, a.workers, log)
        rows.append({"macro": f"Add{m}", "label": f"default with {k} set to {v_best:g}", "param": k,
                     "value": v_best, "score": s_add,
                     "rel_vs_best": None if s_add is None or not s_best else s_add / s_best - 1.0,
                     "rel_vs_default": None if s_add is None or not s_base else s_add / s_base - 1.0})
    out = {"steps": a.steps, "scenarios": tune.SCREEN, "best": {"params": best, "score": s_best},
           "default": {"params": base, "score": s_base}, "rows": rows}
    (tune.TUNE_DIR / "ablation.json").write_text(json.dumps(out, indent=1))
    for r in rows:
        print(f"{r['macro']:<16} {r['label']:<50} score={r['score']:.5f} rel_vs_best={100 * r['rel_vs_best']:+.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
