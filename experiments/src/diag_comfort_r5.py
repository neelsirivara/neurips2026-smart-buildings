"""Round 5: where v7's comfort loss sits (hour, weekday, cold vs hot, zone size), from existing diag runs.

Reads <tree>/<b>/<w>/transfer/{diag.csv, zones.npz}. Comfort loss per step = -0.6 * regret_n (leaderboard units).
Out-of-band zone-steps use the occupied comfort band 294-297 K (the shipped setpoint schedule).

    python diag_comfort_r5.py <label> <tree> [<tree> ...]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LO, HI = 294.0, 297.0
OUT = Path(__file__).resolve().parent.parent / "results" / "round5" / "analysis"


def scen_dirs(tree: Path):
    for b in sorted(tree.iterdir()):
        if not b.is_dir() or not b.name.startswith("building"):
            continue
        for w in sorted(b.iterdir()):
            d = w / "transfer"
            if (d / "zones.npz").exists() and (d / "diag.csv").exists():
                yield f"{b.name}/{w.name}", d


def main() -> int:
    label, trees = sys.argv[1], [Path(t) for t in sys.argv[2:]]
    rows = []
    agg = {"comfort_total": 0.0, "by_hour": np.zeros(24), "by_dow_h6": np.zeros(7), "metric_total": 0.0}
    cold_h6 = hot_h6 = cold_rest = hot_rest = 0.0
    area_bins = np.zeros(4)
    n = 0
    seen = set()
    for tree in trees:
        for key, d in scen_dirs(tree):
            if key in seen:          # the same scenario in two trees (Mac and laptop copies): count once
                continue
            seen.add(key)
            df = pd.read_csv(d / "diag.csv")
            z = np.load(d / "zones.npz")
            T, occ, area = z["zone_t"], z["zone_occ"], z["zone_area_m2"]
            ts = pd.to_datetime(df["timestamp"]) - pd.Timedelta(minutes=5)   # step start
            hour = ts.dt.hour.to_numpy()
            dow = ts.dt.dayofweek.to_numpy()
            comfort = -0.6 * df["regret_n"].to_numpy()
            steps = len(df)
            agg["comfort_total"] += comfort.sum() / steps
            agg["metric_total"] += abs(df["reward"].sum()) / steps
            for h in range(24):
                agg["by_hour"][h] += comfort[hour == h].sum() / steps
            for dd in range(7):
                agg["by_dow_h6"][dd] += comfort[(hour == 6) & (dow == dd)].sum() / steps
            # occupant-weighted deviation (proxy for the regret split)
            dev_c = np.maximum(LO - T, 0.0) * occ
            dev_h = np.maximum(T - HI, 0.0) * occ
            h6 = hour == 6
            cold_h6 += dev_c[h6].sum(); hot_h6 += dev_h[h6].sum()
            cold_rest += dev_c[~h6].sum(); hot_rest += dev_h[~h6].sum()
            q = np.quantile(area, [0.25, 0.5, 0.75])
            qi = np.searchsorted(q, area)
            tot_dev = (dev_c + dev_h).sum(axis=0)
            for i in range(4):
                area_bins[i] += tot_dev[qi == i].sum()
            rows.append({"scenario": key, "metric": abs(df["reward"].sum()) / steps,
                         "comfort": comfort.sum() / steps, "comfort_h6": comfort[h6].sum() / steps,
                         "comfort_h6_monday": comfort[h6 & (dow == 0)].sum() / steps,
                         "n_zones": int(T.shape[1])})
            n += 1
    for k in ("comfort_total", "metric_total"):
        agg[k] /= n
    agg["by_hour"] = (agg["by_hour"] / n).tolist()
    agg["by_dow_h6"] = (agg["by_dow_h6"] / n).tolist()
    cold_h6, hot_h6, cold_rest, hot_rest = map(float, (cold_h6, hot_h6, cold_rest, hot_rest))
    tot = cold_h6 + hot_h6 + cold_rest + hot_rest
    res = {"label": label, "n": n, "metric": agg["metric_total"], "comfort": agg["comfort_total"],
           "comfort_share": agg["comfort_total"] / agg["metric_total"],
           "comfort_by_hour": agg["by_hour"], "comfort_h6_by_dow_mon0": agg["by_dow_h6"],
           "deviation_share": {"cold_h6": cold_h6 / tot, "hot_h6": hot_h6 / tot, "cold_other": cold_rest / tot,
                               "hot_other": hot_rest / tot},
           "deviation_share_by_area_quartile": (area_bins / area_bins.sum()).tolist(),
           "per_scenario": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"comfort_{label}.json").write_text(json.dumps(res, indent=1))
    print(f"{label}: n={n} metric={res['metric']:.5f} comfort={res['comfort']:.6f} ({100*res['comfort_share']:.1f}%)")
    print("  comfort by hour 6..10:", [f"{x:.6f}" for x in res["comfort_by_hour"][6:11]])
    print("  hour-6 comfort by weekday Mon..Fri:", [f"{x:.6f}" for x in res["comfort_h6_by_dow_mon0"][:5]])
    print("  deviation share:", {k: round(v, 3) for k, v in res["deviation_share"].items()})
    print("  by area quartile:", [round(x, 3) for x in res["deviation_share_by_area_quartile"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
