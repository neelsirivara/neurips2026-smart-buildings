"""Official-style scoring of a results tree plus paired bootstrap CIs and breakdowns.

Reads <results-dir>/<building>/<weather>/<policy>/summary.json (8,640-step runs only),
computes the leaderboard metric for every policy present (mean over scenarios of
|total_reward| / 8640; lower is better), paired bootstrap 95% CIs of the metric
difference ours - baseline over scenarios (>= 2000 resamples), per-station and
per-building diagnostics, the regret/energy/carbon decomposition, a Wilcoxon
signed-rank test, and the organizer-provided baseline_returns.json numbers for
reference. Everything is written to <out>.json for make_macros.py.

Usage:
    python score_all.py --results-dir ../results/full --ours transfer \
        --baselines pid_water pid fixed_setpoint bang_bang --out ../results/final_scores.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "kit"
STEPS = 8640
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore")


def load_tree(root: Path) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in root.glob("building_*/*/*/summary.json"):
        s = json.loads(f.read_text())
        if int(s.get("total_steps", 0)) != STEPS:
            continue
        key = f"{f.parts[-4]}/{f.parts[-3]}"
        out[key][f.parts[-2]] = s
    return dict(out)


def metric(totals: dict[str, float]) -> float:
    return float(np.mean([abs(v) / STEPS for v in totals.values()]))


def paired_bootstrap(a: np.ndarray, b: np.ndarray, n: int = 5000, seed: int = 0) -> dict:
    """CI for mean(a) - mean(b) over paired scenarios (a, b are per-scenario scores)."""
    rng = np.random.default_rng(seed)
    d = a - b
    k = len(d)
    idx = rng.integers(0, k, size=(n, k))
    boots = d[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    ratio_boots = a[idx].mean(axis=1) / b[idx].mean(axis=1)
    rlo, rhi = np.percentile(ratio_boots, [2.5, 97.5])
    return {"diff": float(d.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "ratio": float(a.mean() / b.mean()), "ratio_ci_lo": float(rlo), "ratio_ci_hi": float(rhi),
            "n": int(k), "n_boot": n, "frac_boot_negative": float((boots < 0).mean()),
            "wins": int((d < 0).sum()), "losses": int((d > 0).sum())}


def wilcoxon(a: np.ndarray, b: np.ndarray) -> dict:
    try:
        from scipy.stats import wilcoxon as _w
        res = _w(a, b, alternative="two-sided")
        return {"statistic": float(res.statistic), "p_value": float(res.pvalue)}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--ours", default="transfer")
    ap.add_argument("--baselines", nargs="*", default=["pid_water", "pid", "fixed_setpoint", "bang_bang"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--official", default=str(KIT / "baseline_returns.json"))
    ap.add_argument("--scenarios", nargs="*", default=None, help="restrict to these building/weather keys")
    ap.add_argument("--label", default="")
    a = ap.parse_args()

    rd = Path(a.results_dir)
    if not rd.is_absolute():
        rd = (HERE / a.results_dir).resolve()
    tree = load_tree(rd)
    official = json.loads(Path(a.official).read_text()) if Path(a.official).exists() else {}
    keys = sorted(k for k in tree if a.ours in tree[k])
    if a.scenarios:
        keys = [k for k in keys if k in set(a.scenarios)]
    out: dict = {"label": a.label, "steps": STEPS, "n_scenarios": len(keys), "scenarios": keys, "policies": {}}

    def per_scen(policy: str, src: str):
        rows = {}
        for k in keys:
            if src == "local":
                s = tree.get(k, {}).get(policy)
                if s is None:
                    continue
                rows[k] = {
                    "total": float(s["total_reward"]), "score": abs(float(s["total_reward"])) / STEPS,
                    "regret": float(s.get("total_normalized_productivity_regret", float("nan"))),
                    "energy": float(s.get("total_normalized_energy_cost", float("nan"))),
                    "carbon": float(s.get("total_normalized_carbon_emission", float("nan"))),
                    "w": [float(s.get("productivity_weight", 0.6)), float(s.get("energy_weight", 0.2)),
                          float(s.get("carbon_weight", 0.2))],
                    "seconds_per_step": s.get("seconds_per_step"),
                    "policy_seconds_per_step": s.get("policy_seconds_per_step"),
                    "num_zones": s.get("num_zones"),
                    "num_ahus": s.get("num_ahus"),
                }
            else:
                v = official.get(k, {}).get(policy)
                if v is None:
                    continue
                rows[k] = {"total": float(v), "score": abs(float(v)) / STEPS}
        return rows

    def summarize(rows: dict) -> dict:
        if not rows:
            return {}
        sc = np.array([r["score"] for r in rows.values()])
        d: dict = {"metric": float(sc.mean()), "metric_sd": float(sc.std(ddof=1)) if len(sc) > 1 else 0.0,
                   "n": len(rows), "per_scenario": rows}
        by_st = {st: float(np.mean([r["score"] for k, r in rows.items() if k.split("/")[1].rsplit("_", 1)[0] == st]))
                 for st in STATIONS if any(k.split("/")[1].rsplit("_", 1)[0] == st for k in rows)}
        d["by_station"] = by_st
        by_b = defaultdict(list)
        for k, r in rows.items():
            by_b[k.split("/")[0]].append(r["score"])
        d["by_building"] = {b: float(np.mean(v)) for b, v in sorted(by_b.items())}
        d["building_size"] = {k.split("/")[0]: {"num_zones": r.get("num_zones"), "num_ahus": r.get("num_ahus")}
                              for k, r in rows.items() if r.get("num_zones") is not None}
        if all("regret" in r for r in rows.values()):
            w = next(iter(rows.values()))["w"]
            # decomposition in metric units (per-step, weighted): mean over scenarios
            d["decomp"] = {
                "comfort": float(np.mean([-w[0] * r["regret"] / STEPS for r in rows.values()])),
                "energy": float(np.mean([w[1] * r["energy"] / STEPS for r in rows.values()])),
                "carbon": float(np.mean([w[2] * r["carbon"] / STEPS for r in rows.values()])),
            }
            d["decomp_by_station"] = {
                st: {
                    "comfort": float(np.mean([-w[0] * r["regret"] / STEPS for k, r in rows.items()
                                              if k.split("/")[1].rsplit("_", 1)[0] == st])),
                    "energy": float(np.mean([w[1] * r["energy"] / STEPS for k, r in rows.items()
                                             if k.split("/")[1].rsplit("_", 1)[0] == st])),
                    "carbon": float(np.mean([w[2] * r["carbon"] / STEPS for k, r in rows.items()
                                             if k.split("/")[1].rsplit("_", 1)[0] == st])),
                } for st in by_st}
            sps = [r["seconds_per_step"] for r in rows.values() if r.get("seconds_per_step")]
            psps = [r["policy_seconds_per_step"] for r in rows.values() if r.get("policy_seconds_per_step")]
            d["seconds_per_step_mean"] = float(np.mean(sps)) if sps else None
            d["policy_ms_per_step_mean"] = float(1000 * np.mean(psps)) if psps else None
        return d

    ours_rows = per_scen(a.ours, "local")
    out["policies"][a.ours] = summarize(ours_rows)
    out["comparisons"] = {}
    for b in a.baselines:
        loc = per_scen(b, "local")
        off = per_scen(b, "official")
        if loc and len(loc) == len(keys):
            out["policies"][b] = summarize(loc)
            out["policies"][b]["source"] = "local"
        elif loc:
            out["policies"][b + "_partial_local"] = summarize(loc)
        if off and len(off) == len(keys):
            out["policies"][b + "_official"] = summarize(off)
            out["policies"][b + "_official"]["source"] = "organizer baseline_returns.json"
        for name, rows in ((b, loc), (b + "_official", off)):
            if rows and len(rows) == len(keys) and ours_rows and len(ours_rows) == len(keys):
                A = np.array([ours_rows[k]["score"] for k in keys])
                B = np.array([rows[k]["score"] for k in keys])
                comp = paired_bootstrap(A, B)
                comp["wilcoxon"] = wilcoxon(A, B)
                comp["by_station_diff"] = {
                    st: float(np.mean([ours_rows[k]["score"] - rows[k]["score"] for k in keys
                                       if k.split("/")[1].rsplit("_", 1)[0] == st])) for st in STATIONS
                    if any(k.split("/")[1].rsplit("_", 1)[0] == st for k in keys)}
                out["comparisons"][f"{a.ours}_vs_{name}"] = comp
    # local-vs-official gap for each baseline present in both
    out["local_vs_official_gap"] = {}
    for b in a.baselines:
        loc, off = per_scen(b, "local"), per_scen(b, "official")
        common = [k for k in keys if k in loc and k in off]
        if common:
            rel = [(loc[k]["total"] - off[k]["total"]) / abs(off[k]["total"]) for k in common]
            out["local_vs_official_gap"][b] = {"n": len(common), "mean_rel_diff": float(np.mean(rel)),
                                               "min_rel_diff": float(np.min(rel)), "max_rel_diff": float(np.max(rel)),
                                               "metric_local": metric({k: loc[k]["total"] for k in common}),
                                               "metric_official": metric({k: off[k]["total"] for k in common})}
    outp = Path(a.out)
    if not outp.is_absolute():
        outp = (HERE / a.out).resolve()
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=1))
    print(f"n={len(keys)} scenarios")
    for pname, d in out["policies"].items():
        if d:
            print(f"  {pname:<26} metric={d['metric']:.5f}  " + " ".join(f"{st}={v:.4f}" for st, v in d.get("by_station", {}).items()))
    for cname, c in out["comparisons"].items():
        print(f"  {cname}: diff={c['diff']:+.5f} [{c['ci_lo']:+.5f},{c['ci_hi']:+.5f}] ratio={c['ratio']:.3f} "
              f"wins={c['wins']}/{c['n']} p_wilcoxon={c['wilcoxon'].get('p_value', float('nan')):.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
