"""Rank the v5 candidates against the baked v4 policy.

Two views, both read from result trees fetched from the Mac (fetch_mac_results.sh):

  screening  results/mac/tune/tune_log.json (merged into results/tune/tune_log.json): every
             evaluation on the 6 screening scenarios at 1,440 steps; candidates carry
             params["_policy"] == "v5", the baked v4 is the entry whose params equal
             results/tune/best_params.json; pid_water from results/mac/tune_baseline
  full       results/mac/full_v5/<candidate>/transfer__agg.json vs results/mac/full/transfer__agg.json
             (v4 on the same machine): leaderboard metric, paired per-scenario differences with
             a bootstrap 95% CI, wins/losses, per-station means

Writes results/candidates_summary.json for make_macros.py and prints the tables.

Usage:  python compare_candidates.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE.parents[0] / "results"
STEPS = 8640
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore")


def merge_tune_logs() -> dict:
    local = RES / "tune" / "tune_log.json"
    mac = RES / "mac" / "tune" / "tune_log.json"
    log = json.loads(local.read_text()) if local.exists() else {"evals": {}}
    if mac.exists():
        mlog = json.loads(mac.read_text())
        for h, rec in mlog.get("evals", {}).items():
            cur = log["evals"].get(h)
            if cur is None or len(rec.get("totals", {})) > len(cur.get("totals", {})):
                log["evals"][h] = rec
        local.write_text(json.dumps(log, indent=1))
    return log


def screening(log: dict) -> list[dict]:
    v4 = RES / "tune" / "best_params_v4.json"     # written when the v5 winner was baked
    best = json.loads((v4 if v4.exists() else RES / "tune" / "best_params.json").read_text())
    rows = []
    for h, rec in log["evals"].items():
        if "score" not in rec:
            continue
        p = rec["params"]
        tag = p.get("_policy", "v4")
        core = {k: v for k, v in p.items() if not k.startswith("_")}
        diff = {k: v for k, v in core.items() if best.get(k) != v}
        rows.append({"hash": h, "tag": tag, "score": rec["score"], "diff_vs_best": diff,
                     "is_best_v4": (tag == "v4" and not diff), "totals": rec["totals"]})
    rows.sort(key=lambda r: r["score"])
    return rows


def full_candidates() -> dict:
    base = RES / "mac" / "full" / "transfer__agg.json"
    out = {"v4_mac": None, "candidates": []}
    if not base.exists():
        return out
    b = json.loads(base.read_text())
    bper = {k: v["score"] for k, v in b["per_scenario"].items()}
    out["v4_mac"] = {"metric": b["leaderboard_metric"], "n": b["n_scenarios"]}
    rng = np.random.default_rng(0)
    for d in sorted((RES / "mac" / "full_v5").glob("c*")):
        f = d / "transfer__agg.json"
        if not f.exists():
            continue
        c = json.loads(f.read_text())
        cper = {k: v["score"] for k, v in c["per_scenario"].items()}
        keys = sorted(set(bper) & set(cper))
        if not keys:
            continue
        A = np.array([cper[k] for k in keys])
        B = np.array([bper[k] for k in keys])
        dlt = A - B
        idx = rng.integers(0, len(keys), size=(5000, len(keys)))
        boots = dlt[idx].mean(axis=1)
        rel = A.mean() / B.mean()
        by_st = {st: float(np.mean([cper[k] for k in keys if k.split("/")[1].startswith(st)]))
                 for st in STATIONS if any(k.split("/")[1].startswith(st) for k in keys)}
        params = json.loads((HERE / "policy_candidates" / f"{d.name}.json").read_text())
        out["candidates"].append({
            "name": d.name, "params": params, "n": len(keys), "metric": float(A.mean()),
            "metric_v4_same_scenarios": float(B.mean()), "ratio_vs_v4": float(rel),
            "diff": float(dlt.mean()), "ci_lo": float(np.percentile(boots, 2.5)),
            "ci_hi": float(np.percentile(boots, 97.5)), "wins": int((dlt < 0).sum()),
            "losses": int((dlt > 0).sum()), "by_station": by_st,
            "complete": len(keys) == 30 and c["n_scenarios"] == 30,
        })
    out["candidates"].sort(key=lambda r: r["metric"])
    return out


def main() -> int:
    log = merge_tune_logs()
    scr = screening(log)
    pw = RES / "mac" / "tune_baseline" / "pid_water__agg.json"
    pw_metric = json.loads(pw.read_text())["leaderboard_metric"] if pw.exists() else None
    print(f"== screening (6 scenarios x 1,440 steps); pid_water = {pw_metric}")
    for r in scr[:25]:
        flag = " <= baked v4" if r["is_best_v4"] else ""
        print(f"  {r['score']:.5f} [{r['tag']}] {r['hash']} {r['diff_vs_best']}{flag}")
    full = full_candidates()
    print("== full length (30 public scenarios, Mac), v4 on the same machine:", full["v4_mac"])
    for c in full["candidates"]:
        print(f"  {c['name']:<28} metric={c['metric']:.5f} (v4 {c['metric_v4_same_scenarios']:.5f}) "
              f"ratio={c['ratio_vs_v4']:.3f} diff={c['diff']:+.5f} [{c['ci_lo']:+.5f},{c['ci_hi']:+.5f}] "
              f"wins={c['wins']}/{c['n']} complete={c['complete']} "
              + " ".join(f"{st[:3]}={v:.4f}" for st, v in c["by_station"].items()))
    out = {"screening": scr, "screening_pid_water": pw_metric, "full": full}
    (RES / "candidates_summary.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
