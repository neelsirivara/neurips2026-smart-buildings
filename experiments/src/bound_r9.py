"""Round 9: plant-delivery and trajectory bounds from run_diag_r9.py outputs (diag.csv + zones.npz + vav.npz).

For each scenario directory <set>/<building>/<weather>/transfer:

1. Gas accounting: billed gas = coil duty + tank heating + tank dissipation + warm-up over-billing (the boiler's flow
   term is computed at the setpoint, so while the tank is below its setpoint every m3 of loop water is billed for
   T_sp - T_tank it never carried). Reported as shares of the billed gas.
2. Delivery bound ("same trajectory, ideal delivery"): per zone and per block (a workday comfort window 06-19, or the
   unoccupied stretch between two such windows, which contains the recovery), the zone's net HVAC heat
   Q = reheat + rho cp F (T_sa - T_zone) is what the trajectory needs.  Delivered at the discharge cap with no forced
   cold air, it costs need * g_cap, g_cap = (T_cap - T_sa) / (T_cap - T_zone) at the block's heating conditions
   (flow-weighted T_sa and T_zone of the steps where the zone was heated; the mixed-air estimate where it never was).
   coil - sum(need * g_cap) is the delivery excess: forced minimum air later bought back, heat below the cap.
3. Instantaneous delivery bound under the same handler run times (inst_excess_*): see the code comment.
   (The trajectory bound is lp_bound_r9.py: the exact linear building model and a perfect-foresight LP.)
4. Electricity: chiller delivery bound on the same blocks (net cooling at the coldest supply air, 285 K, with the
   block's mixed-air temperature), fan and pump reported as they are.

Usage: python bound_r9.py --dirs <r9 diag set dirs...> --out results/round9/bound_r9.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

T_CAP = 308.15
RHO_CP = 1.2 * 1006.0
SAT_MIN = 285.0
COMFORT_LO = 294.0
DT_H = 300.0 / 3600.0


def blocks_of(ts: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Block id per step: each workday 06-19 window is one block (kind 0); the stretch between is one (kind 1)."""
    t = pd.to_datetime(ts)
    hod = t.dt.hour.values + t.dt.minute.values / 60.0
    wd = t.dt.dayofweek.values < 5
    occw = wd & (hod >= 6.0) & (hod < 19.0)
    bid = np.zeros(len(t), dtype=int)
    k = 0
    for i in range(1, len(t)):
        if occw[i] != occw[i - 1]:
            k += 1
        bid[i] = k
    return bid, occw.astype(int)


def analyse(d: Path) -> dict | None:
    if not (d / "vav.npz").exists() or not (d / "diag.csv").exists():
        return None
    ts = pd.read_csv(d / "diag.csv")
    z = np.load(d / "zones.npz", allow_pickle=False)
    v = np.load(d / "vav.npz", allow_pickle=False)
    n = len(ts)
    T = z["zone_t"].astype(float)[:n]              # zone temperature after the step
    occ = z["zone_occ"].astype(float)[:n]
    F = v["flow_m3s"].astype(float)[:n]
    Tsa = v["tsa_k"].astype(float)[:n]
    RH = v["reheat_w"].astype(float)[:n]
    QA = v["q_air_w"].astype(float)[:n]
    Q = RH + QA                                     # net HVAC heat into the zone (W)
    area = v["zone_area_m2"].astype(float)
    aoz = v["ahu_of_zone"].astype(int)
    tout = ts.oat_k.values.astype(float)
    gas = ts.gas_w.values.astype(float)
    coil = RH.sum(axis=1)
    tank_w = v["tank_w"].astype(float)[:n]
    diss = v["dissip_w"].astype(float)[:n]
    resid = gas - coil - tank_w - diss
    over = np.where(tank_w >= 0.0, resid, 0.0)        # setpoint above the tank while water flows
    clipped = np.where(tank_w < 0.0, resid, 0.0)      # tank cooling credit clipped at zero billed gas
    # gas accounting (energy, kWh)
    kwh = lambda x: float(np.nansum(x) * DT_H / 1000.0)
    acct = {"gas_kwh": kwh(gas), "coil_kwh": kwh(coil), "tank_heat_kwh": kwh(np.maximum(tank_w, 0.0)),
            "tank_credit_kwh": kwh(np.minimum(tank_w, 0.0)), "dissip_kwh": kwh(diss),
            "warmup_overbill_kwh": kwh(over), "tank_credit_clipped_kwh": kwh(clipped)}
    sp = v["sp_k"].astype(float)[:n]
    acct["loop_rewarms"] = int(((sp[1:] > 340.0) & (sp[:-1] < 320.0)).sum())
    acct["loop_hot_share"] = float((sp > 340.0).mean())
    # previous-step temperature (the step's own conditions)
    Tp = np.vstack([T[:1], T[:-1]])
    bid, kind = blocks_of(ts.timestamp)
    nb = bid.max() + 1
    V = T.shape[1]
    # comfort-mode gains (the simulator's square wave) + occupants
    t = pd.to_datetime(ts.timestamp)
    hod = t.dt.hour.values + t.dt.minute.values / 60.0
    comfort_mode = (t.dt.dayofweek.values < 5) & (hod >= 6.0) & (hod < 19.0)
    G = (10.0 * np.where(comfort_mode, 1.0, 0.2))[:, None] * area[None, :] + 70.0 * occ
    # ---- delivery bound ----
    heated = RH > 1.0
    lb = 0.0
    lb_occ = lb_unocc = 0.0
    coil_by_kind = {0: 0.0, 1: 0.0}
    need_by_kind = {0: 0.0, 1: 0.0}
    lb_by_kind = {0: 0.0, 1: 0.0}
    g_used = []
    for b in range(nb):
        s = bid == b
        kd = 0 if kind[s][0] == 1 else 1           # 0 = occupied window, 1 = unoccupied stretch
        for j in range(V):
            qn = Q[s, j].sum()
            ch = RH[s, j].sum()
            coil_by_kind[kd] += ch
            if qn <= 0.0:
                continue
            h = heated[s, j]
            if h.any():
                w = F[s, j][h]
                tsa = float(np.average(Tsa[s, j][h], weights=w)) if w.sum() > 0 else float(Tsa[s, j][h].mean())
                tz = float(np.average(Tp[s, j][h], weights=RH[s, j][h]))
            else:
                tz = float(Tp[s, j].mean())
                tsa = 0.7 * tz + 0.3 * float(tout[s].mean())
            g = max((T_CAP - tsa) / max(T_CAP - tz, 0.5), 1.0)
            g_used.append(g)
            need_by_kind[kd] += qn
            lb_by_kind[kd] += qn * g
    deliv = {"coil_kwh_occ": coil_by_kind[0] * DT_H / 1e3, "coil_kwh_unocc": coil_by_kind[1] * DT_H / 1e3,
             "need_kwh_occ": need_by_kind[0] * DT_H / 1e3, "need_kwh_unocc": need_by_kind[1] * DT_H / 1e3,
             "lb_kwh_occ": lb_by_kind[0] * DT_H / 1e3, "lb_kwh_unocc": lb_by_kind[1] * DT_H / 1e3}
    deliv["excess_share_of_gas"] = (sum(coil_by_kind.values()) - sum(lb_by_kind.values())) * DT_H / 1e3 / max(acct["gas_kwh"], 1e-9)
    deliv["excess_occ_share_of_gas"] = (coil_by_kind[0] - lb_by_kind[0]) * DT_H / 1e3 / max(acct["gas_kwh"], 1e-9)
    deliv["excess_unocc_share_of_gas"] = (coil_by_kind[1] - lb_by_kind[1]) * DT_H / 1e3 / max(acct["gas_kwh"], 1e-9)
    deliv["g_median"] = float(np.median(g_used)) if g_used else None
    # instantaneous bound under the same handler run times: a heated box must carry at least its forced minimum
    # flow at the coil-entering air temperature (its outside-air share is paid whatever the box does), so the least
    # coil duty that delivers q > 0 is q + F_min rho cp (T - T_sa) while q fits in the forced flow at the cap, else
    # q * g_cap; v10's actual duty minus this is what better delivery alone (no change of run times) could save
    fmin = 2.0 * 0.1 * np.sqrt(200.0 / 2000.0)
    fm = np.minimum(F, fmin)
    qpos = np.maximum(Q, 0.0)
    tax = fm * RHO_CP * np.maximum(Tp - Tsa, 0.0)
    capf = fm * RHO_CP * np.maximum(T_CAP - Tp, 0.5)
    gi = (T_CAP - Tsa) / np.maximum(T_CAP - Tp, 0.5)
    lbi = np.where(RH > 1.0, np.where(qpos <= capf, qpos + tax, qpos * gi), 0.0)
    occ_step = (kind == 1)[:, None]
    deliv["inst_excess_occ_share_of_gas"] = float(np.where(occ_step, RH - lbi, 0.0).sum() * DT_H / 1e3 / max(acct["gas_kwh"], 1e-9))
    deliv["inst_excess_unocc_share_of_gas"] = float(np.where(~occ_step, RH - lbi, 0.0).sum() * DT_H / 1e3 / max(acct["gas_kwh"], 1e-9))
    deliv["heated_box_steps_below_cap_occ"] = None
    # (round 9: a first-order per-zone trajectory estimate was tried here and gave implausible results -- the zone
    # air is nearly algebraic on the 5-minute step and the slow modes are the slab and walls; the trajectory bound is
    # computed with the exact linear building model instead, in lp_bound_r9.py)
    out = {"acct": acct, "delivery": deliv, "steps": n}
    # ---- chiller delivery bound ----
    cool_w = np.abs(ts.cool_w.values.astype(float))
    cooled = (QA < -1.0) & (RH <= 1.0) & (Tsa < Tp - 0.5)
    qc = np.where(cooled, -QA, 0.0).sum()          # net cooling delivered by unreheated air (W-steps)
    out["cooling"] = {"chiller_elec_kwh": kwh(cool_w), "net_cooling_kwh": float(qc * DT_H / 1e3)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for dd in a.dirs:
        for s in sorted(Path(dd).glob("building_*/*/transfer")):
            r = analyse(s)
            if r is not None:
                res[f"{Path(dd).name}/{s.parts[-3]}/{s.parts[-2]}"] = r
                print(s.parts[-3], s.parts[-2], json.dumps({k: (round(x, 4) if isinstance(x, float) else x)
                                                            for k, x in {**r["acct"], **{"dx": r["delivery"]["excess_share_of_gas"],
                                                                         "dx_occ": r["delivery"]["excess_occ_share_of_gas"],
                                                                         "ix_occ": r["delivery"]["inst_excess_occ_share_of_gas"],
                                                                         "ix_unocc": r["delivery"]["inst_excess_unocc_share_of_gas"]}}.items()}))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
