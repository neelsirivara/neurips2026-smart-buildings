"""Round 7: fit first-order zone models C dT/dt = Q - U (T - Tout) + G to the zone logs (ANALYSIS.md sections 3-5).

Input: zone_log_r7.py outputs (npz: T, Q, QH, F, Tsa, Td per step and VAV, tout, mode, hod, dow).
Per zone, unoccupied steps only (policy modes PRECONDITION and SETBACK, where no occupant gains act), 30-min windows:
    y  = (T[t+6] - T[t]) / 0.5 h                     (K/h; the 6-step window also absorbs the one-step sensor lag)
    x1 = mean Q over the window (kW)                 (net heat actually delivered, read from the simulator)
    x2 = mean (T - Tout) over the window (K)
    y  = a x1 - k x2 + c        ->  C = 1/a (kWh/K), U = k/a (kW/K), tau = 1/k (h), G = c/a (kW)
Then, using each zone's fit:
  * morning recoveries (PRECONDITION episodes before a workday start): the duration predicted by the model at the
    heat actually delivered vs the observed duration, and the time spent at the preconditioning target before 06:00
    (the hold that a better start would save) with its loss U (T - Tout) x hold time;
  * the closed-form recovery at the request cap, Q_cap(T) = A (308.15 - T) with A = rho cp x 2 m3/s x sqrt(0.1)
    (the policy's floor-pressure flow cap): dT/dt = (A (Td - T) - U (T - Tout) + G) / C, i.e. a first-order approach to
    T_inf = (A Td + U Tout + G) / (A + U) with time constant C / (A + U); the slope of the recovery rate with T is
    -(A + U)/C, which explains round 6's finding that colder mornings (lower start temperatures) recover faster.
Writes results/round7/zone_model_fit.json.

    python fit_zone_model_r7.py --logs ../results/round7/zone_logs/*.npz
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results" / "round7" / "zone_model_fit.json"
W = 6                      # steps per window (30 min)
DT_H = W * 300.0 / 3600.0
RHO_CP = 1.2 * 1006.0
A_CAP = RHO_CP * 2.0 * np.sqrt(200.0 / 2000.0)   # W/K: floor-pressure flow of a fully open box (the f_cap_pre cap)
TD = 308.15


def fit_zone(T, Q, tout, unocc):
    n = len(T) - W
    idx = np.arange(0, n, 2)                               # overlapping windows, stride 10 min
    ok = np.array([unocc[i:i + W + 1].all() and np.isfinite(T[i:i + W + 1]).all() and np.isfinite(Q[i:i + W]).all()
                   for i in idx])
    idx = idx[ok]
    if len(idx) < 50:
        return None
    y = (T[idx + W] - T[idx]) / DT_H
    x1 = np.array([Q[i:i + W].mean() for i in idx]) / 1000.0
    x2 = np.array([(T[i:i + W] - tout[i:i + W]).mean() for i in idx])
    X = np.column_stack([x1, -x2, np.ones_like(x1)])
    th, *_ = np.linalg.lstsq(X, y, rcond=None)
    a, k, c = th
    pred = X @ th
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - pred) ** 2).sum() / ss if ss > 0 else float("nan")
    heat = x1 > 0.2
    return {"a_kph_per_kw": float(a), "k_per_h": float(k), "c_kph": float(c), "r2": float(r2), "n": int(len(idx)),
            "C_kwh_per_k": float(1 / a) if a > 0 else None, "U_kw_per_k": float(k / a) if a > 0 else None,
            "tau_h": float(1 / k) if k > 0 else None, "G_kw": float(c / a) if a > 0 else None,
            "share_windows_heated": float(heat.mean())}


def recoveries(T, Q, tout, mode, hod, dow, fit):
    """PRECONDITION episodes that end at a workday start: observed vs model-predicted duration, hold at target."""
    out = []
    pre = mode == 1
    i, n = 0, len(T)
    while i < n:
        if pre[i] and (i == 0 or not pre[i - 1]):
            j = i
            while j < n and pre[j]:
                j += 1
            seg = slice(i, j)
            if j < n and mode[j] == 0 and dow[j] < 5 and (j - i) >= 3:
                t0 = T[i]
                tgt = np.nanmax(T[seg]) if j - i > 0 else t0
                # first step within 0.2 K of the episode's end temperature = "reached target"
                reach = i + int(np.argmax(T[seg] >= T[j - 1] - 0.2))
                hold_h = (j - reach) * 300.0 / 3600.0
                dur_h = (reach - i) * 300.0 / 3600.0
                qbar = np.nanmean(Q[i:max(reach, i + 1)])
                pred = None
                if fit and fit["a_kph_per_kw"] > 0 and dur_h > 0.25:
                    a, k, c = fit["a_kph_per_kw"], fit["k_per_h"], fit["c_kph"]
                    tt, tm = t0, 0.0
                    to = float(np.nanmean(tout[seg]))
                    while tt < T[j - 1] - 0.2 and tm < 12.0:
                        tt += (a * qbar / 1000.0 - k * (tt - to) + c) * (5.0 / 60.0)
                        tm += 5.0 / 60.0
                    pred = tm
                out.append({"start_hod": float(hod[i]), "t0": float(t0), "t_end": float(T[j - 1]), "dur_h": dur_h,
                            "pred_h": pred, "hold_h": hold_h, "q_kw": float(qbar / 1000.0),
                            "tout": float(np.nanmean(tout[seg]))})
            i = j
        else:
            i += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", nargs="+", required=True)
    a = ap.parse_args()
    files = sorted({f for g in a.logs for f in glob.glob(g)})
    res = {"window_steps": W, "A_cap_w_per_k": A_CAP, "scenarios": {}}
    allfit, allrec = [], []
    for f in files:
        z = np.load(f)
        name = Path(f).stem
        T, Q, tout, mode = z["T"].astype(float), z["Q"].astype(float), z["tout"].astype(float), z["mode"]
        hod, dow = z["hod"], z["dow"]
        V = T.shape[1]
        sc = {"zones": {}}
        for v in range(V):
            md = mode[:, v]
            unocc = np.isin(md, (1, 2))
            fit = fit_zone(T[:, v], Q[:, v], tout, unocc)
            rec = recoveries(T[:, v], Q[:, v], tout, md, hod, dow, fit)
            sc["zones"][str(z["vav_ids"][v])] = {"fit": fit, "recoveries": rec}
            if fit:
                allfit.append(fit)
            allrec += [r for r in rec if r["pred_h"] is not None]
        res["scenarios"][name] = sc
        good = [x["fit"] for x in sc["zones"].values() if x["fit"]]
        print(f"{name:40s} zones {V} fitted {len(good)} tau_h median "
              f"{np.median([g['tau_h'] for g in good if g['tau_h']]):.1f} R2 median {np.median([g['r2'] for g in good]):.2f}")
    taus = np.array([f_["tau_h"] for f_ in allfit if f_["tau_h"] and f_["tau_h"] > 0])
    r2 = np.array([f_["r2"] for f_ in allfit])
    dur = np.array([r["dur_h"] for r in allrec])
    pr = np.array([r["pred_h"] for r in allrec])
    hold = np.array([r["hold_h"] for r in allrec])
    res["summary"] = {
        "n_zone_fits": len(allfit), "tau_h_p10_p50_p90": [float(np.percentile(taus, q)) for q in (10, 50, 90)],
        "r2_p10_p50_p90": [float(np.percentile(r2, q)) for q in (10, 50, 90)],
        "n_recoveries": int(len(dur)),
        "recovery_dur_h_mean": float(dur.mean()) if len(dur) else None,
        "recovery_pred_abs_err_h_median": float(np.median(np.abs(pr - dur))) if len(dur) else None,
        "recovery_pred_rel_err_median": float(np.median(np.abs(pr - dur) / np.maximum(dur, 0.25))) if len(dur) else None,
        "hold_h_mean": float(hold.mean()) if len(hold) else None,
        "hold_h_p90": float(np.percentile(hold, 90)) if len(hold) else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
