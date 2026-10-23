"""Round-3 candidates ledger -> results/round3/candidates.json (+ a printed table).

Merges the hand-written notes (candidates_notes.json: idea, rationale, status, code changes,
ideas not run) with every number on disk:
  * screening: results/round3/screen_summary.json (screen_round3.py summarize), both sets
  * full length: results/final*_scores.json comparisons transfer_vs_transfer_v5 when present
  * the ten-day diagnostic tests on building_0502/denver_1 (results/round3/b0502_*)

Usage:  python ledger_round3.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parents[0] / "results"
R3 = RES / "round3"


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def outcome(pub: dict | None, held: dict | None) -> str:
    """Screen verdict against the v6 defaults under the shipping rule (paired bootstrap 95% CIs over
    scenarios): 'worse' if either CI lies above zero; 'rule met' if the held-out CI lies below zero
    (and the public one does not lie above it); 'public only' if only the public CI lies below zero;
    'n.s.' otherwise; 'incomplete' while a set is missing."""
    if not pub or not held or pub.get("ci_lo") is None or held.get("ci_lo") is None or held.get("n_paired") != 6:
        return "incomplete"
    if pub["ci_lo"] > 0 or held["ci_lo"] > 0:
        return "worse"
    if held["ci_hi"] < 0:
        return "rule met"
    if pub["ci_hi"] < 0:
        return "public only"
    return "n.s."


def full_c00_public() -> dict | None:
    """The v6 defaults (r3_c00) at full length on the 30 public scenarios (laptop run), paired against
    v5 on the Mac (diag_v5_public; the simulator reproduces bit for bit across the two machines)."""
    import numpy as np
    agg = load(R3 / "laptop_full_c00_public" / "transfer__agg.json")
    if not agg:
        return None
    v5 = {}
    for f in sorted((RES / "mac" / "round3" / "diag_v5_public").glob("building_*/*/transfer/summary.json")):
        s = json.loads(f.read_text())
        v5[f"{f.parts[-4]}/{f.parts[-3]}"] = abs(s["total_reward"]) / s["total_steps"]
    c0 = {k: v["score"] for k, v in agg["per_scenario"].items()}
    keys = sorted(set(c0) & set(v5))
    out = {"machine": "laptop", "n": len(keys), "metric": float(np.mean([c0[k] for k in keys])) if keys else None}
    if keys:
        from score_all import paired_bootstrap
        out["vs_v5"] = paired_bootstrap(np.array([c0[k] for k in keys]), np.array([v5[k] for k in keys]))
        out["metric_v5"] = float(np.mean([v5[k] for k in keys]))
    out["per_scenario"] = {k: c0[k] for k in keys}
    return out


def _tree_scores(*dirs: Path) -> dict:
    out = {}
    for d in dirs:
        for f in sorted(d.glob("building_*/*/transfer/summary.json")):
            s = json.loads(f.read_text())
            if s.get("total_steps") == 8640:
                out[f"{f.parts[-4]}/{f.parts[-3]}"] = abs(s["total_reward"]) / s["total_steps"]
    return out


def full_c00_heldout() -> dict | None:
    """The v6 defaults (r3_c00) at full length on both held-out sets (Mac, run after the shipped
    variant, for the ledger only), pooled over the 40 scenarios and paired against v5 and the shipped
    variant on the same scenarios."""
    import numpy as np
    from score_all import paired_bootstrap
    m3 = RES / "mac" / "round3"
    c0 = _tree_scores(m3 / "final_c00_heldout", m3 / "final_c00_r3")
    if len(c0) < 40:
        return {"n": len(c0), "complete": False}
    v5 = _tree_scores(m3 / "diag_v5_heldout", m3 / "diag_v5_r3")
    v6 = _tree_scores(m3 / "final_v6_heldout", m3 / "final_v6_r3")
    keys = sorted(set(c0) & set(v5) & set(v6))
    A = np.array([c0[k] for k in keys])
    out = {"machine": "mac", "complete": True, "n": len(keys), "metric": float(A.mean()),
           "metric_v5": float(np.mean([v5[k] for k in keys])), "metric_shipped": float(np.mean([v6[k] for k in keys])),
           "vs_v5": paired_bootstrap(A, np.array([v5[k] for k in keys])),
           "shipped_vs_c00": paired_bootstrap(np.array([v6[k] for k in keys]), A)}
    return out


def main() -> int:
    notes = load(HERE / "candidates_notes.json")
    screen = load(R3 / "screen_summary.json")
    rows = {r["name"]: r for r in (screen or {}).get("rows", [])}
    # the same screens paired against the v6 defaults (screen_round3.py summarize --ref r3_c00_v6_default)
    screen0 = load(R3 / "screen_summary_vs_r3_c00_v6_default.json")
    rows0 = {r["name"]: r for r in (screen0 or {}).get("rows", [])}
    ledger = {"doc": notes["_doc"], "v6_code_changes": notes["v6_code_changes"],
              "ideas_not_run": notes["ideas_not_run"], "screen_steps": (screen or {}).get("steps"),
              "screen_sets": (screen or {}).get("sets"), "shipped": notes.get("shipped"),
              "decision_rule": notes.get("decision_rule"), "candidates": {}}
    for name, note in notes["candidates"].items():
        entry = dict(note)
        entry["params"] = load(HERE / "policy_candidates" / f"{name}.json") if name != "ref_v5" else {}
        r = rows.get(name)
        keys = ("n", "metric", "ref_metric", "diff", "ratio", "ci_lo", "ci_hi", "wins", "losses", "n_paired")
        if r:
            for s in ("public", "held"):
                d = r.get(s) or {}
                entry[f"screen_{s}"] = {k: d.get(k) for k in keys}
        r0 = rows0.get(name)
        if r0 and name != "r3_c00_v6_default":
            for s in ("public", "held"):
                d = r0.get(s) or {}
                entry[f"screen_{s}_vs_c00"] = {k: d.get(k) for k in keys}
            entry["screen_outcome_vs_c00"] = outcome(entry.get("screen_public_vs_c00"), entry.get("screen_held_vs_c00"))
        ledger["candidates"][name] = entry
    # ten-day diagnostic tests on the large held-out building
    tests = {}
    for d in sorted(R3.glob("b0502_*")):
        f = d / "building_0502" / "denver_1" / "transfer" / "summary.json"
        if f.exists():
            s = json.loads(f.read_text())
            tests[d.name] = {"steps": s["total_steps"], "score": abs(s["total_reward"]) / s["total_steps"],
                             "regret": s["total_normalized_productivity_regret"],
                             "energy": s["total_normalized_energy_cost"], "carbon": s["total_normalized_carbon_emission"]}
    ledger["ten_day_tests_building_0502_denver_1"] = {
        "doc": "v5 = shipped; v6 = area scaling + physical caps + per-zone start; v6b = + water-limited cap; v6c = v6b + preconditioning latch (rejected)",
        **tests}
    # full-length comparisons
    full = {}
    for label, f in (("public", RES / "final_scores.json"), ("heldout", RES / "heldout_scores.json"),
                     ("heldout_r3", RES / "heldout_r3_scores.json")):
        sc = load(f)
        if sc and "transfer_vs_transfer_v5" in sc.get("comparisons", {}):
            c = sc["comparisons"]["transfer_vs_transfer_v5"]
            full[label] = {"n": sc["n_scenarios"], "metric_new": sc["policies"]["transfer"]["metric"],
                           "metric_v5": sc["policies"]["transfer_v5"]["metric"], **{k: c.get(k) for k in
                           ("diff", "ci_lo", "ci_hi", "ratio", "ratio_ci_lo", "ratio_ci_hi", "wins", "losses")},
                           "wilcoxon_p": (c.get("wilcoxon") or {}).get("p_value")}
    ledger["full_length_shipped_vs_v5"] = full
    c0 = full_c00_public()
    ledger["full_length_c00_public"] = c0
    ledger["full_length_c00_heldout"] = full_c00_heldout()
    # the shipped variant against the v6 defaults at full length on the public set
    fs = load(RES / "final_scores.json")
    ship = (fs or {}).get("policies", {}).get("transfer", {}).get("per_scenario") or {}
    if c0 and ship and fs.get("policies", {}).get("transfer_v5"):
        import numpy as np
        from score_all import paired_bootstrap
        keys = sorted(set(ship) & set(c0["per_scenario"]))
        A = np.array([ship[k]["score"] for k in keys]); B = np.array([c0["per_scenario"][k] for k in keys])
        ledger["full_length_shipped_vs_c00_public"] = {"n": len(keys), "metric_shipped": float(A.mean()),
                                                      "metric_c00": float(B.mean()), **paired_bootstrap(A, B)}
    out = R3 / "candidates.json"
    out.write_text(json.dumps(ledger, indent=1))
    print(f"-> {out}")
    print(f"{'candidate':<26} {'status':<10} {'public':>22} {'held':>22}")
    for name, e in ledger["candidates"].items():
        def cell(s):
            d = e.get(f"screen_{s}")
            if not d or d.get("metric") is None:
                return "-"
            if d.get("ratio") is None:
                return f"{d['metric']:.5f} (n={d['n']})"
            return f"{d['metric']:.5f} r={d['ratio']:.3f} w={d['wins']}/{d['n_paired']}"
        print(f"{name:<26} {e['status']:<10} {cell('public'):>22} {cell('held'):>22}  vs c00: {e.get('screen_outcome_vs_c00', '-')}")
    for k, v in tests.items():
        print(f"  ten-day 0502/denver_1 {k}: score {v['score']:.5f} regret {v['regret']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
