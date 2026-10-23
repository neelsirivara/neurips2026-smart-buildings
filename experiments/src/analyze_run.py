"""Diagnose where a policy loses reward on one scenario run (needs --save-ts output).

Reads <results-dir>/<building>/<weather>/<policy>/{summary.json,timeseries.csv,ahu_log.csv}
and prints: totals, decomposition (regret / energy / carbon) split by occupied vs
unoccupied steps, by local hour of day, zone-temperature statistics relative to
the band while occupied, and AHU flow statistics. Several policies can be
compared side by side.

Usage:
    python analyze_run.py ../results/full building_train_1/fairbanks_1 pid_water transfer
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent

COMFORT = (294.0, 297.0)
ECO = (289.0, 298.0)


def load(results_dir: Path, scen: str, policy: str):
    d = results_dir / scen / policy
    summ = json.loads((d / "summary.json").read_text())
    ts = pd.read_csv(d / "timeseries.csv", parse_dates=["timestamp"])
    ahu = pd.read_csv(d / "ahu_log.csv") if (d / "ahu_log.csv").exists() else None
    return summ, ts, ahu


def describe(results_dir: Path, scen: str, policies: list[str]) -> None:
    w = 0.6, 0.2, 0.2
    rows = {}
    for p in policies:
        try:
            summ, ts, ahu = load(results_dir, scen, p)
        except FileNotFoundError as e:
            print(f"[{p}] missing: {e}")
            continue
        n = len(ts)
        hod = ts.timestamp.dt.hour + ts.timestamp.dt.minute / 60.0
        dow = ts.timestamp.dt.dayofweek
        occ = ts.occupancy.values > 0
        comfort_hours = (dow < 5) & (hod >= 6) & (hod < 19)
        zcols = [c for c in ts.columns if c.startswith("zone_") and c.endswith("_temp")]
        Z = ts[zcols].values
        lo = np.where(comfort_hours, COMFORT[0], ECO[0])[:, None]
        hi = np.where(comfort_hours, COMFORT[1], ECO[1])[:, None]
        dev = np.maximum(0.0, np.maximum(lo - Z, Z - hi))
        reg = -w[0] * ts.productivity_regret.values  # positive = loss
        en = w[1] * ts.energy_cost.values
        cb = w[2] * ts.carbon.values
        tot = reg + en + cb
        rows[p] = dict(
            total=summ["total_reward"], steps=n, score=abs(summ["total_reward"]) / n,
            regret=reg.sum(), energy=en.sum(), carbon=cb.sum(),
            regret_occ=reg[occ].sum(), energy_occ=en[occ].sum(), energy_unocc=en[~occ].sum(),
            carbon_occ=cb[occ].sum(), carbon_unocc=cb[~occ].sum(),
            frac_occ=occ.mean(),
            dev_occ_mean=float(dev[occ].mean()) if occ.any() else 0.0,
            dev_occ_worst_mean=float(dev[occ].max(axis=1).mean()) if occ.any() else 0.0,
            frac_zone_steps_out_occ=float((dev[occ] > 0).mean()) if occ.any() else 0.0,
            frac_zone_steps_out_gt1_occ=float((dev[occ] > 1).mean()) if occ.any() else 0.0,
            frac_zone_steps_out_gt5_occ=float((dev[occ] > 5).mean()) if occ.any() else 0.0,
            zmean_occ=float(Z[occ].mean()) if occ.any() else 0.0,
            zmin=float(Z.min()), zmax=float(Z.max()),
            sec_per_step=summ.get("seconds_per_step"),
        )
        # by hour of day
        byh = pd.DataFrame({"h": np.floor(hod).astype(int), "reg": reg, "en": en, "cb": cb, "tot": tot,
                            "occ": occ, "devmax": dev.max(axis=1)}).groupby("h").agg(
            reg=("reg", "sum"), en=("en", "sum"), cb=("cb", "sum"), tot=("tot", "sum"),
            occ=("occ", "mean"), devmax=("devmax", "mean"))
        rows[p]["_byh"] = byh
        if ahu is not None:
            def listcol(prefix):
                cols = [c for c in ahu.columns if c.startswith(prefix)]
                if not cols:
                    return None
                if len(cols) == 1 and ahu[cols[0]].dtype == object:
                    import re as _re
                    num = _re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")
                    return np.array([[float(x) for x in num.findall(str(v))] for v in ahu[cols[0]]],
                                    dtype=float)
                return ahu[cols].values.astype(float)
            F = listcol("ahu_flow_rates")
            R = listcol("ahu_run_cmds")
            if F is not None:
                rows[p]["ahu_flow_mean"] = float(F.sum(axis=1).mean())
                rows[p]["ahu_flow_occ"] = float(F.sum(axis=1)[occ[: len(F)]].mean()) if occ.any() else 0.0
                rows[p]["ahu_flow_unocc"] = float(F.sum(axis=1)[~occ[: len(F)]].mean())
            if R is not None:
                rows[p]["ahu_on_frac"] = float(R.mean())
                rows[p]["ahu_on_frac_unocc"] = float(R[~occ[: len(R)]].mean())
            rows[p]["oat_mean"] = float(ahu.outside_air.mean())
            rows[p]["oat_min"] = float(ahu.outside_air.min())
            rows[p]["oat_max"] = float(ahu.outside_air.max())

    if not rows:
        return
    print(f"\n=== {scen} ===")
    keys = [k for k in next(iter(rows.values())).keys() if not k.startswith("_")]
    hdr = f"{'metric':<28}" + "".join(f"{p:>16}" for p in rows)
    print(hdr)
    for k in keys:
        line = f"{k:<28}"
        for p in rows:
            v = rows[p].get(k)
            line += f"{v:>16.4f}" if isinstance(v, (int, float)) and v is not None else f"{str(v):>16}"
        print(line)
    print("\nby hour of day (loss = regret + energy + carbon, summed over episode; occ = occupied fraction)")
    print(f"{'h':>3}" + "".join(f"{p+':tot':>12}{p+':reg':>12}{p+':en+cb':>12}{p+':dev':>10}" for p in rows) + f"{'occ':>8}")
    byhs = {p: rows[p]["_byh"] for p in rows}
    first = next(iter(byhs.values()))
    for h in first.index:
        line = f"{h:>3}"
        for p in rows:
            b = byhs[p].loc[h]
            line += f"{b.tot:>12.3f}{b.reg:>12.3f}{b.en + b.cb:>12.3f}{b.devmax:>10.3f}"
        line += f"{first.loc[h].occ:>8.2f}"
        print(line)


def main() -> int:
    results_dir = Path(sys.argv[1])
    if not results_dir.is_absolute():
        results_dir = (HERE / results_dir).resolve()
    scen = sys.argv[2]
    policies = sys.argv[3:] or ["pid_water", "transfer"]
    describe(results_dir, scen, policies)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
