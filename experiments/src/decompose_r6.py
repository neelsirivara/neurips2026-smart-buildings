"""Round 6: loss decomposition of v8 on the harsh screening set (by mode / hour / day type / zone), gas-focused.

Inputs: run_diag.py outputs fetched from the Kaggle kernels (diag.csv.gz, zones.npz, summary.json) under
results/round6/runs/<variant>/<set>/<building>/<weather>/transfer/. Uses decompose_loss.decompose for the
round-3..5 split (comfort / fan / cooling / pump / gas, by hour, by policy mode, occupied / unoccupied, weekday /
weekend) and adds, per step and per zone:

  * ventilation (outside-air) heat load of running handlers, flow x (1 - recirc) x rho cp x (T_zone - T_oa), split by
    zone state: heated zones (valve open), idle zones on a running handler (damper at the 10% floor, valve shut);
    zone flow = damper x 2 m3/s x sqrt(P / 2000 Pa) (every box has the same design flow);
  * gas by policy mode x day type, and the share of gas spent while some handler runs only for set-back zones;
  * the coldest zone temperatures on weekends (frost check) and at the end of each night;
  * morning recovery: hours before 06:00 at which each zone entered PRECONDITION (from the zone temperatures
    and the handler run state is not identifiable per zone, so the building-level mode column is used).

    python decompose_r6.py --dirs ../results/round6/runs/v8/r6hs --label v8_r6hs --out ../results/round6/decomp_v8_r6hs.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import decompose_loss as dl

HERE = Path(__file__).resolve().parent
RHO_CP = 1.2 * 1006.0


def ensure_csv(d: Path) -> None:
    gz = d / "diag.csv.gz"
    if gz.exists() and not (d / "diag.csv").exists():
        with gzip.open(gz, "rb") as fi, open(d / "diag.csv", "wb") as fo:
            shutil.copyfileobj(fi, fo)


def extra(d: Path, base: dict) -> dict:
    ts = pd.read_csv(d / "diag.csv", parse_dates=["timestamp"])
    z = np.load(d / "zones.npz", allow_pickle=False)
    zt, dmp, vlv = z["zone_t"].astype(float), z["damper"].astype(float), z["valve"].astype(float)
    run, ahu_p, rec = z["ahu_run"] > 0, z["ahu_p"].astype(float), z["ahu_recirc"].astype(float)
    aoz = z["ahu_of_zone"]
    n = min(len(ts), zt.shape[0])
    ts, zt, dmp, vlv, run, ahu_p, rec = ts.iloc[:n], zt[:n], dmp[:n], vlv[:n], run[:n], ahu_p[:n], rec[:n]
    oat = ts.oat_k.values[:, None]
    on_z = run[:, aoz]
    f_real = np.sqrt(np.clip(ahu_p[:, aoz], 200.0, 2000.0) / 2000.0)
    flow_z = np.where(on_z, np.clip(dmp, 0.1, 1.0) * 2.0 * f_real, 0.0)        # m3/s
    oa_frac = 1.0 - rec[:, aoz]
    vent_w = flow_z * oa_frac * RHO_CP * np.maximum(zt - oat, 0.0)              # W per zone
    heated = on_z & (vlv > 1e-3)
    idle = on_z & (vlv <= 1e-3) & (dmp <= 0.1001)
    gas_w = ts.gas_w.values
    mode = ts["mode"].values
    wd = ts.timestamp.dt.dayofweek.values < 5
    hour = ts.timestamp.dt.hour.values
    dtj = 300.0
    gas_j = gas_w.sum() * dtj
    out = {
        "gas_j": float(gas_j),
        "vent_j_total": float(vent_w.sum() * dtj),
        "vent_j_heated_zones": float((vent_w * heated).sum() * dtj),
        "vent_j_idle_zones": float((vent_w * idle).sum() * dtj),
        "vent_j_by_mode": {str(m): float(vent_w[mode == m].sum() * dtj) for m in (0, 1, 2)},
        "gas_j_by_mode_daytype": {f"{m}_{'wd' if w else 'we'}": float(gas_w[(mode == m) & (wd == w)].sum() * dtj)
                                  for m in (0, 1, 2) for w in (True, False)},
        "gas_j_by_hour": [float(gas_w[hour == h].sum() * dtj) for h in range(24)],
        "ahu_zone_on_share": float(on_z.mean()),
        "idle_share_of_on_zone_steps": float(idle.sum() / max(on_z.sum(), 1)),
        "mean_oat_k": float(ts.oat_k.mean()),
        "min_zone_t_weekend": float(zt[~wd].min()) if (~wd).any() else None,
        "p05_zone_t_weekend": float(np.percentile(zt[~wd], 5)) if (~wd).any() else None,
        "min_zone_t_all": float(zt.min()),
        "zone_steps_below_278k": float((zt < 278.15).mean()),
        "zone_steps_below_280k": float((zt < 280.15).mean()),
        "tank_only_gas_j": float(gas_w[ts.n_ahu_on.values == 0].sum() * dtj),
        "hw_hot_share": float((ts.hw_t_k.values > 340).mean()),
    }
    # building-level precondition start (hours before 06:00) on workday mornings
    ts_h = ts.timestamp.dt.hour.values + ts.timestamp.dt.minute.values / 60.0
    day = (ts.timestamp.dt.normalize() - ts.timestamp.dt.normalize().iloc[0]).dt.days.values
    starts = []
    for dd in np.unique(day):
        m = (day == dd) & (ts_h < 6.0) & wd
        if not m.any():
            continue
        idx = np.where(m & (mode == 1))[0]
        if len(idx):
            starts.append(6.0 - ts_h[idx[0]])
    out["pre_start_h_before_6_mean"] = float(np.mean(starts)) if starts else None
    out["pre_start_h_before_6_max"] = float(np.max(starts)) if starts else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = {}
    for dd in a.dirs:
        dp = Path(dd)
        if not dp.is_absolute():
            dp = (HERE / dd).resolve()
        for s in sorted(dp.glob("building_*/*/transfer")):
            ensure_csv(s)
            if not (s / "diag.csv").exists():
                continue
            r = dl.decompose(s)
            if r is None or r["steps"] != 8640:
                continue
            r.update(extra(s, r))
            key = f"{s.parts[-3]}/{s.parts[-2]}"
            r["set"] = dp.name
            rows[key] = r
            print(f"{key:34s} metric {r['metric']:.5f} gas {r['components']['gas']:.5f} vent/gas "
                  f"{r['vent_j_total'] / max(r['gas_j'], 1):.2f} idle-vent/gas {r['vent_j_idle_zones'] / max(r['gas_j'], 1):.2f} "
                  f"minT_we {r['min_zone_t_weekend']:.1f} oat {r['mean_oat_k'] - 273.15:.1f}C", flush=True)
    if not rows:
        print("no runs")
        return 1
    over = dl.agg(rows, lambda k, r: "all")["all"]
    keys = ["gas_j", "vent_j_total", "vent_j_heated_zones", "vent_j_idle_zones", "tank_only_gas_j"]
    over["sums"] = {k: float(sum(r[k] for r in rows.values())) for k in keys}
    over["gas_j_by_mode_daytype"] = {k: float(sum(r["gas_j_by_mode_daytype"][k] for r in rows.values()))
                                     for k in next(iter(rows.values()))["gas_j_by_mode_daytype"]}
    over["vent_j_by_mode"] = {k: float(sum(r["vent_j_by_mode"][k] for r in rows.values())) for k in ("0", "1", "2")}
    over["gas_j_by_hour"] = [float(sum(r["gas_j_by_hour"][h] for r in rows.values())) for h in range(24)]
    over["min_zone_t_weekend"] = float(min(r["min_zone_t_weekend"] for r in rows.values() if r["min_zone_t_weekend"]))
    out = {"label": a.label, "n": len(rows), "overall": over,
           "by_station": dl.agg(rows, lambda k, r: k.split("/")[1].rsplit("_", 1)[0]),
           "per_scenario": {k: {kk: vv for kk, vv in r.items() if kk not in ("zone_area_m2", "zone_weighted_deviation",
                                                                              "recovery_hours_after_6_mean_by_zone")}
                            for k, r in rows.items()}}
    op = Path(a.out)
    if not op.is_absolute():
        op = (HERE / a.out).resolve()
    op.write_text(json.dumps(out, indent=1))
    o = over
    print(f"\n== {a.label} n={len(rows)} metric {o['metric']:.5f}")
    print("   shares: " + " ".join(f"{c} {100 * o['shares'][c]:.1f}%" for c in dl.COMPONENTS))
    g = o["sums"]["gas_j"]
    print(f"   ventilation load / gas: total {o['sums']['vent_j_total'] / g:.2f}, heated zones "
          f"{o['sums']['vent_j_heated_zones'] / g:.2f}, idle zones {o['sums']['vent_j_idle_zones'] / g:.2f}")
    print("   gas by mode x day: " + " ".join(f"{k} {v / g:.3f}" for k, v in o["gas_j_by_mode_daytype"].items()))
    print("   vent by mode: " + " ".join(f"{k} {v / g:.3f}" for k, v in o["vent_j_by_mode"].items()))
    print("   gas by hour: " + " ".join(f"{h}:{v / g:.3f}" for h, v in enumerate(o["gas_j_by_hour"])))
    print(f"   coldest weekend zone {o['min_zone_t_weekend'] - 273.15:.1f} C")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
