"""Round 7 ANALYSIS.md numbers: marginal gas cost of each heating-mode lever, from the simulator's equations and the
fitted first-order zone models (fit_zone_model_r7.py on the zone logs of v9 on six harsh screening scenarios).

Levers (heating, the handler only cools, the boxes reheat; identities checked in check_identities_r7.py):
  L1 outside-air fraction at the 30% floor: gas per joule of net zone heat at the discharge cap
       g = (Td - Tsa)/(Td - T) = 1 + (T - Tsa)/(Td - T),  Tsa = Tmix = r Tret + (1 - r) Tout,  r <= 0.7
     -> table of g against Tout (T = Tret = 294 K) and the sensitivity dg/d(1 - r) = (Tret - Tout)/(Td - T)
  L2 discharge temperature at the 308.15 K cap: dg/dTd = -(T - Tsa)/(Td - T)^2
  L3 setback depth: with the zone model C dT/dt = Q - U (T - Tout) + G, the predicted gas of a night at floor F =
     hold (g(F) x (U (F - Tout) - G) x hold time) + recovery at the cap (closed form); per zone and for the logged
     weeknights, the marginal saving per K of a deeper floor at v9's 279.15 K and the share of nights the floor binds;
     prediction for round 6's c08 (floor 281.15 -> 279.15 K)
  L4 preconditioning start: with the cap fixed, the latest start that reaches the target is optimal (any earlier start
     only adds hold time at the highest temperature); the hold time actually observed under v9 and its gas share bound
     what a better start can save; prediction for round 6's c07 (lead safety 1.3 -> 1.15)
Writes results/round7/analysis_r7.json.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
R7 = HERE.parent / "results" / "round7"
TD = 308.15
RHO_CP = 1.2 * 1006.0
A_KW = RHO_CP * 2.0 * np.sqrt(0.1) / 1000.0     # kW/K: v9's preconditioning cap (fully open box at floor pressure)
ECO_LO = 289.15


def g_formula(T, Tout, r=0.7, Tret=None, Td=TD):
    Tret = T if Tret is None else Tret
    tsa = r * Tret + (1 - r) * Tout
    return 1.0 + (T - tsa) / (Td - T)


def night_cost(F, T0, Tout, a, k, c, H, target, safety=1.0):
    """Predicted gas (kWh) from T0 at departure to target at the start, holding floor F, recovering at the cap."""
    beta = a * A_KW + k
    tinf = (a * A_KW * TD + k * Tout + c) / beta
    if tinf <= target + 0.05:
        return None
    t_rec = np.log((tinf - F) / (tinf - target)) / beta if F < target else 0.0
    if safety * t_rec > H:
        return None
    g_rec = A_KW * ((TD - 0.3 * Tout - 0.7 * tinf) * t_rec + 0.7 * (tinf - F) * (1 - np.exp(-beta * t_rec)) / beta)
    teq = Tout + c / k
    if F <= teq + 0.05 or T0 <= F:
        t_ff = np.inf if T0 > F else 0.0
    else:
        t_ff = np.log((T0 - teq) / (F - teq)) / k
    t_hold = float(np.clip(H - safety * t_rec - t_ff, 0.0, H))
    q_hold = max((k * (F - Tout) - c) / a, 0.0)
    g_hold = 1.0 + 0.3 * (F - Tout) / max(TD - F, 0.5)
    if t_hold <= 0:
        # floor never reached: the zone free-floats to T(H - t_rec) and recovers from there
        tf = teq + (T0 - teq) * np.exp(-k * max(H - safety * t_rec, 0.0))
        t_rec2 = np.log((tinf - tf) / (tinf - target)) / beta if tf < target else 0.0
        g_rec = A_KW * ((TD - 0.3 * Tout - 0.7 * tinf) * t_rec2 + 0.7 * (tinf - tf) * (1 - np.exp(-beta * t_rec2)) / beta)
    return {"gas_kwh": float(g_hold * q_hold * t_hold + g_rec), "t_hold_h": t_hold, "t_rec_h": float(t_rec),
            "reached": bool(t_hold > 0)}


def main() -> int:
    fit = json.loads((R7 / "zone_model_fit.json").read_text())
    out = {}
    # L1 / L2
    tab = []
    for c in (0, -10, -20, -30, -40):
        Tout = 273.15 + c
        T = 294.15
        g = g_formula(T, Tout)
        tab.append({"tout_c": c, "g": float(g), "dg_d_oa_frac": float((T - Tout) / (TD - T)),
                    "dg_dTd_per_k": float(-(T - (0.7 * T + 0.3 * Tout)) / (TD - T) ** 2),
                    "g_at_zone_281K": float(g_formula(281.15, Tout))})
    out["L1_L2_table_T294"] = tab
    ci = json.loads((R7 / "check_identities.json").read_text())
    cm = json.loads((R7 / "check_identities_minneapolis.json").read_text())
    out["identity_checks"] = {k: ci.get(k) for k in ("sa_identity_max_abs_err_k", "recirc_share_at_cap_0p7",
                                                     "discharge_max_k", "discharge_at_cap_share",
                                                     "reheat_identity_max_rel_err", "g_formula_max_abs_err",
                                                     "g_energy_weighted", "g_energy_weighted_at_cap",
                                                     "net_heat_share_at_cap", "boiler_over_reheat_sum",
                                                     "mean_tz_minus_tsa_at_cap_k", "heated_vav_steps")}
    out["identity_checks_minneapolis"] = {k: cm.get(k) for k in ("g_energy_weighted", "g_energy_weighted_at_cap",
                                                                 "boiler_over_reheat_sum", "net_heat_share_at_cap")}
    # zone parameters
    zs = []
    for sname, sc in fit["scenarios"].items():
        for vid, z in sc["zones"].items():
            f = z["fit"]
            if f and f["a_kph_per_kw"] > 1e-3 and 1e-3 < f["k_per_h"] < 3.0:
                zs.append((sname, vid, f))
    taus = np.array([f["tau_h"] for _, _, f in zs])
    Cs = np.array([f["C_kwh_per_k"] for _, _, f in zs])
    Us = np.array([f["U_kw_per_k"] for _, _, f in zs])
    out["zone_params"] = {"n": len(zs), "tau_h_p10_p50_p90": [float(np.percentile(taus, q)) for q in (10, 50, 90)],
                          "C_kwh_per_k_p10_p50_p90": [float(np.percentile(Cs, q)) for q in (10, 50, 90)],
                          "U_kw_per_k_p10_p50_p90": [float(np.percentile(Us, q)) for q in (10, 50, 90)],
                          "recovery_rate_slope_kph_per_k_median": float(np.median(
                              [-(f["a_kph_per_kw"] * A_KW + f["k_per_h"]) for _, _, f in zs]))}
    # L3 / L4 period-based predictions on the logged scenarios (first `days` days, as the short check runs):
    # every unoccupied period of every zone (start temperature and mean outside air from the log, horizon = the
    # period until the next occupied step); floors F0 = v9's (eco_lo - 10 K; weekends a further 6 K) and F0 - d
    logs = {Path(f).stem: np.load(f) for f in glob.glob(str(R7 / "zone_logs" / "*.npz"))}
    zfit = {(sname, vid): f for sname, vid, f in zs}
    days = 7
    target = 294.15 + 0.5                       # v9: comfort_lo + margin_pre 0.5
    pred = {}
    for sname, zl in logs.items():
        n = min(days * 288, len(zl["tout"]))
        T, QH, mode, tout = zl["T"][:n].astype(float), zl["QH"][:n].astype(float), zl["mode"][:n], zl["tout"][:n]
        dow, hod = zl["dow"][:n], zl["hod"][:n]
        gas_total = float(np.nansum(QH)) * 300.0 / 3.6e6          # kWh over the window (reheat = billed gas)
        d_floor = {"nle12": 2.0, "nle14": 4.0, "mbf16": None}
        acc = {k: 0.0 for k in d_floor}
        n_per, n_reach = 0, 0
        for v, vid in enumerate(zl["vav_ids"]):
            f = zfit.get((sname, str(vid)))
            if not f:
                continue
            a, k, c = f["a_kph_per_kw"], f["k_per_h"], f["c_kph"]
            unocc = mode[:, v] != 0
            i = 0
            while i < n:
                if unocc[i] and (i == 0 or not unocc[i - 1]):
                    j = i
                    while j < n and unocc[j]:
                        j += 1
                    if j < n:                                     # period ends at an occupied step
                        H = (j - i) / 12.0
                        weekend = H > 30.0
                        F0 = ECO_LO - 10.0 - (6.0 if weekend else 0.0)
                        To = float(np.mean(tout[i:j]))
                        base = night_cost(F0, float(T[i, v]), To, a, k, c, H, target, safety=1.3)
                        if base:
                            n_per += 1
                            n_reach += base["reached"]
                            for key, dd in d_floor.items():
                                if dd is not None:
                                    r = night_cost(F0 - dd, float(T[i, v]), To, a, k, c, H, target, safety=1.3)
                                    if r:
                                        acc[key] += r["gas_kwh"] - base["gas_kwh"]
                                else:
                                    best = base["gas_kwh"]
                                    for Fc in np.arange(F0, ECO_LO - 16.0 - 1e-9, -0.5):
                                        r = night_cost(Fc, float(T[i, v]), To, a, k, c, H, target, safety=1.1)
                                        if r and r["reached"] and r["gas_kwh"] < best:
                                            best = r["gas_kwh"]
                                    acc[key] += best - base["gas_kwh"]
                    i = j
                else:
                    i += 1
        # L4: start -- for each recovery ending at an occupied step, the hold before the start and its heat
        acc_s = {"ls115": 0.0, "ls100": 0.0}
        for v in range(T.shape[1]):
            pre = mode[:, v] == 1
            i = 0
            while i < n:
                if pre[i] and (i == 0 or not pre[i - 1]):
                    j = i
                    while j < n and pre[j]:
                        j += 1
                    if j < n and mode[j, v] == 0:
                        seg = T[i:j, v]
                        reach = i + int(np.argmax(seg >= seg[-1] - 0.2))
                        hold_h = (j - reach) / 12.0
                        lead_h = (j - i) / 12.0
                        q_hold = float(np.nanmean(QH[reach:j, v])) / 1000.0 if j > reach else 0.0   # kW of gas
                        for key, s_new in (("ls115", 1.15), ("ls100", 1.0)):
                            dt = max(lead_h - 0.5, 0.0) * (1.0 - s_new / 1.3)
                            acc_s[key] -= min(dt, hold_h) * q_hold
                    i = j
                else:
                    i += 1
        pred[sname] = {"days": days, "gas_kwh": gas_total, "periods": n_per, "share_periods_floor_reached":
                       n_reach / max(n_per, 1),
                       **{f"pred_rel_{k}": acc[k] / gas_total for k in acc},
                       **{f"pred_rel_{k}": acc_s[k] / gas_total for k in acc_s}}
    out["predictions_7d"] = pred
    # L4 over the full 14-day logs: hold before the start and its gas share (bound on what a better start saves)
    hold_q, all_q, hold_h = 0.0, 0.0, []
    for sname, zl in logs.items():
        QH, mode, T = zl["QH"].astype(float), zl["mode"], zl["T"].astype(float)
        all_q += float(np.nansum(QH))
        for v in range(T.shape[1]):
            pre = mode[:, v] == 1
            i = 0
            while i < len(pre):
                if pre[i] and (i == 0 or not pre[i - 1]):
                    j = i
                    while j < len(pre) and pre[j]:
                        j += 1
                    if j < len(pre) and mode[j, v] == 0:
                        seg = T[i:j, v]
                        reach = i + int(np.argmax(seg >= seg[-1] - 0.2))
                        hold_q += float(np.nansum(QH[reach:j, v]))
                        hold_h.append((j - reach) / 12.0)
                    i = j
                else:
                    i += 1
    sm = fit["summary"]
    out["L4_start"] = {"n_recoveries": sm["n_recoveries"], "recovery_dur_h_mean": sm["recovery_dur_h_mean"],
                       "hold_h_mean": float(np.mean(hold_h)) if hold_h else None,
                       "hold_gas_share_of_all_gas": hold_q / all_q if all_q else None,
                       "model_recovery_rel_err_median": sm["recovery_pred_rel_err_median"],
                       "model_r2_median": sm["r2_p10_p50_p90"][1]}
    (R7 / "analysis_r7.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
