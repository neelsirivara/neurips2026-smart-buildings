"""Round 6: how the morning recovery rate depends on the outdoor temperature (for the optimum-start candidates).

From v8 diagnostic runs (zones.npz + diag.csv[.gz]): for every workday morning (00:00-06:00) and zone, the steps on
which the zone's handler runs, its reheat valve is open and it is below the preconditioning target (294.8 K) are a
recovery; rate = temperature rise / heating hours (at least 6 such steps), lift = 294.8 K - mean outside air over
them. The within-zone slope of rate on lift (zone means removed, least squares) is what ``rate_oat_slope`` models.

    python fit_recovery_r6.py --dirs ../results/round6/runs/v8/r6hs --out ../results/round6/recovery_fit_v8_r6hs.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from decompose_r6 import ensure_csv

HERE = Path(__file__).resolve().parent
LO_PRE = 294.8


def morning_recoveries(d: Path) -> list[dict]:
    ensure_csv(d)
    ts = pd.read_csv(d / "diag.csv", parse_dates=["timestamp"], usecols=["timestamp", "oat_k", "mode"])
    z = np.load(d / "zones.npz", allow_pickle=False)
    zt, vlv, run, aoz = z["zone_t"].astype(float), z["valve"].astype(float), z["ahu_run"] > 0, z["ahu_of_zone"]
    n = min(len(ts), zt.shape[0])
    ts, zt, vlv, run = ts.iloc[:n], zt[:n], vlv[:n], run[:n]
    on = run[:, aoz]
    h = ts.timestamp.dt.hour.values
    wd = ts.timestamp.dt.dayofweek.values < 5
    day = (ts.timestamp.dt.normalize() - ts.timestamp.dt.normalize().iloc[0]).dt.days.values
    oat = ts.oat_k.values
    out = []
    for dd in np.unique(day):
        m = np.where((day == dd) & wd & (h < 6))[0]
        if len(m) < 12:
            continue
        for j in range(zt.shape[1]):
            heat = on[m, j] & (vlv[m, j] > 0.05) & (zt[m, j] < LO_PRE)
            idx = m[heat]
            if len(idx) < 6:
                continue
            # rise over the heating steps (sum of step-to-step changes while heating)
            nxt = np.minimum(idx + 1, n - 1)
            rise = float((zt[nxt, j] - zt[idx, j]).sum())
            hours = len(idx) / 12.0
            out.append({"day": int(dd), "zone": int(j), "rate": rise / hours, "lift": float(LO_PRE - oat[idx].mean()),
                        "hours": hours, "start_t": float(zt[idx[0], j])})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    for dd in a.dirs:
        dp = Path(dd)
        if not dp.is_absolute():
            dp = (HERE / dd).resolve()
        for s in sorted(dp.glob("building_*/*/transfer")):
            if not (s / "zones.npz").exists():
                continue
            key = f"{s.parts[-3]}/{s.parts[-2]}"
            for r in morning_recoveries(s):
                r["scenario"] = key
                rows.append(r)
    if not rows:
        print("no data")
        return 1
    df = pd.DataFrame(rows)
    df["zkey"] = df.scenario + "#" + df.zone.astype(str)
    g = df.groupby("zkey")
    df = df[g.lift.transform("count") >= 3]
    x = df.lift - df.groupby("zkey").lift.transform("mean")
    y = df.rate - df.groupby("zkey").rate.transform("mean")
    slope = float((x * y).sum() / max((x * x).sum(), 1e-9))
    # bootstrap over zones for a CI
    rng = np.random.default_rng(0)
    zk = df.zkey.unique()
    bs = []
    for _ in range(1000):
        pick = rng.choice(zk, size=len(zk), replace=True)
        sub = pd.concat([df[df.zkey == k] for k in pick[:200]]) if len(zk) > 200 else \
            pd.concat([df[df.zkey == k] for k in pick])
        xx = sub.lift - sub.groupby("zkey").lift.transform("mean")
        yy = sub.rate - sub.groupby("zkey").rate.transform("mean")
        bs.append(float((xx * yy).sum() / max((xx * xx).sum(), 1e-9)))
        if len(bs) >= 200:
            break
    res = {"n_recoveries": int(len(df)), "n_zones": int(len(zk)), "within_zone_slope_kph_per_k": slope,
           "slope_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
           "mean_rate_kph": float(df.rate.mean()), "mean_lift_k": float(df.lift.mean()),
           "rate_by_lift_bin": {f"{int(lo)}-{int(lo + 10)}": float(df[(df.lift >= lo) & (df.lift < lo + 10)].rate.mean())
                                for lo in range(0, 70, 10) if ((df.lift >= lo) & (df.lift < lo + 10)).any()}}
    op = Path(a.out)
    if not op.is_absolute():
        op = (HERE / a.out).resolve()
    op.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
