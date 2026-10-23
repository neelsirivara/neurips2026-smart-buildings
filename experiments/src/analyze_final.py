"""Diagnostics behind the Analysis section, from the saved per-step timeseries of the final runs.

For every scenario that has both policies (default: transfer and pid_water) with a
timeseries.csv under <results-dir>, computes per policy:

  * share of the total loss incurred on unoccupied steps (energy + carbon only there)
  * comfort regret share of the total loss
  * occupied zone-steps outside the comfort band (fraction), and the mean worst-zone deviation
  * regret on the first workday relative to the mean regret of the other workdays
    (does the optimum start learn?)
  * loss by hour of day (mean over scenarios, metric units per step)

and writes <out> (JSON) with per-scenario rows and means over scenarios, for make_macros.py
and make_figures.py.

Usage:
    python analyze_final.py --results-dir ../results/full --out ../results/analysis.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
W = (0.6, 0.2, 0.2)
COMFORT = (294.0, 297.0)


def one_run(d: Path) -> dict | None:
    f = d / "timeseries.csv"
    if not f.exists():
        return None
    ts = pd.read_csv(f, parse_dates=["timestamp"])
    reg = -W[0] * ts.productivity_regret.values          # positive = loss
    en = W[1] * ts.energy_cost.values
    cb = W[2] * ts.carbon.values
    tot = reg + en + cb
    occ = ts.occupancy.values > 0
    hod = ts.timestamp.dt.hour.values + ts.timestamp.dt.minute.values / 60.0
    day = (ts.timestamp.dt.normalize() - ts.timestamp.dt.normalize().iloc[0]).dt.days.values
    zcols = [c for c in ts.columns if c.startswith("zone_") and c.endswith("_temp")]
    Z = ts[zcols].values
    dev = np.maximum(0.0, np.maximum(COMFORT[0] - Z, Z - COMFORT[1]))
    total = float(tot.sum())
    out = {
        "total_loss": total,
        "steps": int(len(ts)),
        "unocc_share": float(tot[~occ].sum() / total) if total > 0 else None,
        "regret_share": float(reg.sum() / total) if total > 0 else None,
        "energy_share": float(en.sum() / total) if total > 0 else None,
        "carbon_share": float(cb.sum() / total) if total > 0 else None,
        "occ_frac_zone_steps_out": float((dev[occ] > 0).mean()) if occ.any() else None,
        "occ_frac_zone_steps_out_gt1": float((dev[occ] > 1.0).mean()) if occ.any() else None,
        "occ_mean_worst_dev_k": float(dev[occ].max(axis=1).mean()) if occ.any() else None,
        "occ_mean_zone_temp_k": float(Z[occ].mean()) if occ.any() else None,
    }
    # workdays = days with any occupancy; regret per workday
    wd = sorted({int(x) for x in day[occ]})
    per_day = {int(dd): float(reg[(day == dd)].sum()) for dd in wd}
    if len(wd) >= 3:
        first = per_day[wd[0]]
        rest = np.mean([per_day[dd] for dd in wd[1:]])
        out["first_workday_regret"] = first
        out["other_workdays_regret_mean"] = float(rest)
        out["first_workday_regret_ratio"] = float(first / rest) if rest > 0 else None
        out["n_workdays"] = len(wd)
    # loss by hour of day (per step, metric units)
    hb = np.floor(hod).astype(int)
    out["loss_by_hour"] = [float(tot[hb == h].mean()) if (hb == h).any() else 0.0 for h in range(24)]
    out["regret_by_hour"] = [float(reg[hb == h].mean()) if (hb == h).any() else 0.0 for h in range(24)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="../results/full")
    ap.add_argument("--policies", nargs="+", default=["transfer", "pid_water"])
    ap.add_argument("--out", default="../results/analysis.json")
    a = ap.parse_args()
    rd = Path(a.results_dir)
    if not rd.is_absolute():
        rd = (HERE / rd).resolve()
    rows: dict[str, dict[str, dict]] = {}
    for sdir in sorted(rd.glob("building_*/*")):
        if not sdir.is_dir():
            continue
        key = f"{sdir.parent.name}/{sdir.name}"
        per = {}
        for pol in a.policies:
            r = one_run(sdir / pol)
            if r is not None and r["steps"] == 8640:
                per[pol] = r
        if len(per) == len(a.policies):
            rows[key] = per
            print(f"{key}: " + "  ".join(
                f"{p}: unocc {100 * per[p]['unocc_share']:.0f}% regret {100 * per[p]['regret_share']:.0f}% "
                f"out {100 * (per[p]['occ_frac_zone_steps_out'] or 0):.1f}%" for p in a.policies), flush=True)
    scalar_keys = ["unocc_share", "regret_share", "energy_share", "carbon_share", "occ_frac_zone_steps_out",
                   "occ_frac_zone_steps_out_gt1", "occ_mean_worst_dev_k", "occ_mean_zone_temp_k",
                   "first_workday_regret_ratio"]
    means = {}
    for pol in a.policies:
        means[pol] = {}
        for k in scalar_keys:
            vals = [rows[s][pol][k] for s in rows if rows[s][pol].get(k) is not None]
            means[pol][k] = float(np.mean(vals)) if vals else None
            means[pol][k + "_median"] = float(np.median(vals)) if vals else None
        means[pol]["loss_by_hour"] = list(np.mean([rows[s][pol]["loss_by_hour"] for s in rows], axis=0)) if rows else []
        means[pol]["regret_by_hour"] = list(np.mean([rows[s][pol]["regret_by_hour"] for s in rows], axis=0)) if rows else []
        # by station
        means[pol]["unocc_share_by_station"] = {}
        for st in ("fairbanks", "denver", "atlanta", "phoenix", "singapore"):
            vals = [rows[s][pol]["unocc_share"] for s in rows if s.split("/")[1].startswith(st)
                    and rows[s][pol].get("unocc_share") is not None]
            if vals:
                means[pol]["unocc_share_by_station"][st] = float(np.mean(vals))
    # first-workday ratio: how many scenarios have a worse first workday than the rest (ours)
    pol0 = a.policies[0]
    fr = [rows[s][pol0].get("first_workday_regret_ratio") for s in rows]
    fr = [v for v in fr if v is not None]
    means[pol0]["n_first_workday_worse"] = int(sum(1 for v in fr if v > 1.0))
    means[pol0]["n_first_workday_total"] = len(fr)
    out = {"results_dir": str(rd), "n_scenarios": len(rows), "policies": a.policies, "per_scenario": rows,
           "means": means}
    op = Path(a.out)
    if not op.is_absolute():
        op = (HERE / op).resolve()
    op.write_text(json.dumps(out, indent=1))
    print(f"n={len(rows)} -> {op}")
    for pol in a.policies:
        m = means[pol]
        print(f"  {pol}: unocc share {m['unocc_share']:.3f}  regret share {m['regret_share']:.3f}  "
              f"occupied zone-steps out of band {m['occ_frac_zone_steps_out']:.4f}  "
              f"first-workday ratio {m['first_workday_regret_ratio']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
