"""Round 4, lead 2: where the chiller (and fan) electricity of SADR v6 goes.

Reads run_diag.py outputs (diag.csv + zones.npz) and, per scenario, reconstructs the chiller's
thermal load from the logged handler states (flow, supply-air setpoint, recirculation, area-weighted
return temperature, outside air) -- it matches the logged chiller power to < 0.1% -- and splits it:

    ventilation   flow * rho cp * (1 - r) * (OAT - T_ret)     outside-air share of the coil load
    return        flow * rho cp * (T_ret - SAT)               the zones' sensible cooling (+ overcooling)
    by mode       occupied / preconditioning / setback (the policy's building mode in diag.csv)
    by hour       0..23
    idle flow     supply air of handlers that cool, going to zones whose damper sits at the floor
                  (0.1) -- forced ventilation of zones that do not ask for cooling
    reheat-while-cooling   coil load on handlers that cool while some served zone's reheat valve is open
    economiser    coil load at maximum recirculation while OAT < T_ret - 1 K (missed free cooling)
    pressure      share of fan power spent above the 200 Pa floor; handler-steps at > 1000 Pa
    night flush   unoccupied steps with OAT <= mean zone T - 3 K (free-cooling potential)
    occupied T    mean zone temperature in occupied cooling steps vs the 297 K band top

    python diag_cooling_r4.py --dirs ../results/mac/round3/final_v6_public ../results/mac/round3/final_v6_heldout \
        ../results/mac/round3/final_v6_r3 --out ../results/round4/diag_cooling_v6.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RHO_CP = 1.2 * 1006.0
COP = 3.5


def one(d: Path) -> dict | None:
    f = d / "diag.csv"
    zf = d / "zones.npz"
    if not (f.exists() and zf.exists()):
        return None
    ts = pd.read_csv(f, parse_dates=["timestamp"])
    z = np.load(zf)
    A = z["zone_area_m2"].astype(float)
    T = z["zone_t"].astype(float)
    aoz = z["ahu_of_zone"].astype(int)
    run = z["ahu_run"] > 0
    K = run.shape[1]
    r = z["ahu_recirc"].astype(float)
    sat = z["ahu_sat"].astype(float)
    fl = z["ahu_flow"].astype(float)
    p = z["ahu_p"].astype(float)
    dmp = z["damper"].astype(float)
    vlv = z["valve"].astype(float)
    oat = ts.oat_k.values.astype(float)
    n = len(ts)
    served = [aoz == k for k in range(K)]
    Tret = np.stack([(T[:, m] * A[m]).sum(1) / max(A[m].sum(), 1e-9) if m.any() else T.mean(1)
                     for m in served], 1)
    mix = r * Tret + (1 - r) * oat[:, None]
    cooling = run & (mix > sat + 1e-6)
    q = np.where(cooling, fl * RHO_CP * (mix - sat), 0.0)               # W thermal per handler
    q_vent = np.where(cooling, fl * RHO_CP * (1 - r) * (oat[:, None] - Tret), 0.0)
    q_ret = q - q_vent
    cool_logged = np.abs(ts.cool_w.values)
    recon_err = (float(q.sum(1).mean() / COP / max(cool_logged.mean(), 1e-9) - 1.0)
                 if cool_logged.mean() > 0 else 0.0)
    # the reward uses the interval start; diag timestamps are interval ends
    hour = (ts.timestamp - pd.Timedelta(minutes=5)).dt.hour.values
    mode = ts["mode"].values
    tot = q.sum()
    out = {"steps": n, "n_zones": int(len(A)), "n_ahus": int(K), "area_m2": float(A.sum()),
           "area_per_ahu_m2": float(A.sum() / K), "median_zone_m2": float(np.median(A)),
           "recon_rel_err": recon_err,
           "cool_elec_kw_mean": float(cool_logged.mean() / 1e3),
           "cool_elec_w_per_m2": float(cool_logged.mean() / A.sum()),
           "cool_elec_w_per_ahu_norm": float(cool_logged.mean() / (80000.0 * K)),
           "fan_w_per_ahu_norm": float(ts.blower_w.mean() / (80000.0 * K)),
           "fan_w_per_m2": float(ts.blower_w.mean() / A.sum()),
           "oat_mean_k": float(oat.mean()), "start": str(ts.timestamp.iloc[0])}
    if tot <= 0:
        out["cooling_thermal_total"] = 0.0
        return out
    out["share_vent"] = float(q_vent.sum() / tot)
    out["share_return"] = float(q_ret.sum() / tot)
    out["share_by_mode"] = {str(m): float(q[mode == m].sum() / tot) for m in (0, 1, 2)}
    out["share_by_hour"] = [float(q[hour == h].sum() / tot) for h in range(24)]
    # idle (floor-damper) zones on cooling handlers: flow share of the cooled air
    zf_flow = dmp * np.sqrt(np.maximum(p[:, aoz], 0) / 2000.0) * 2.0      # m3/s per zone (design 2.0)
    zcool = cooling[:, aoz]
    idle = zcool & (dmp <= 0.1001) & (dmp > 0)
    cooled_flow = (zf_flow * zcool).sum()
    out["idle_flow_share_of_cooled_air"] = float((zf_flow * idle).sum() / max(cooled_flow, 1e-9))
    mix_z = mix[:, aoz]
    sat_z = sat[:, aoz]
    q_idle = np.where(idle, zf_flow * RHO_CP * (mix_z - sat_z), 0.0).sum()
    out["share_idle_air"] = float(q_idle / tot)
    out["idle_zone_mean_T_k"] = float(T[idle].mean()) if idle.any() else None
    # reheat while cooling
    any_valve = np.stack([(vlv[:, m] > 0.01).any(1) if m.any() else np.zeros(n, bool) for m in served], 1)
    out["share_reheat_while_cooling"] = float(q[cooling & any_valve].sum() / tot)
    # missed economiser: cooling at max recirculation with OAT well below the return air
    miss = cooling & (r >= 0.69) & (oat[:, None] < Tret - 1.0)
    out["share_econ_missed"] = float(q[miss].sum() / tot)
    out["share_econ_active"] = float(q[cooling & (r < 0.69)].sum() / tot)
    # pressure
    fan_floor = fl * 200.0
    fan_act = fl * np.maximum(p, 200.0)
    out["fan_share_above_floor"] = float(1 - fan_floor[run].sum() / max(fan_act[run].sum(), 1e-9))
    out["ahu_steps_p_gt_1000_share"] = float((run & (p > 1000)).sum() / max(run.sum(), 1))
    # zones at full damper while cooling (capacity-limited)
    full = zcool & (dmp >= 0.99)
    out["zone_cool_steps_full_damper_share"] = float(full.sum() / max(zcool.sum(), 1))
    # occupied (mode 0) cooling: zone temperatures of zones on cooling handlers
    occ = (mode == 0)[:, None] & zcool
    out["occ_cool_zone_T_mean_k"] = float(T[occ].mean()) if occ.any() else None
    out["occ_cool_zone_T_above_297_share"] = float((T[occ] > 297.0).mean()) if occ.any() else None
    # night flush potential: unoccupied steps with OAT <= mean zone T - 3
    Tm = (T * A).sum(1) / A.sum()
    unocc = mode != 0
    cool_enough = unocc & (oat <= Tm - 3.0)
    out["unocc_steps_oat_le_Tzone_minus3_share"] = float(cool_enough.sum() / max(unocc.sum(), 1))
    out["unocc_mean_dT_when_cool_enough"] = float((Tm - oat)[cool_enough].mean()) if cool_enough.any() else None
    out["mean_zone_T_occupied_k"] = float(Tm[mode == 0].mean()) if (mode == 0).any() else None
    out["mean_zone_T_unocc_k"] = float(Tm[unocc].mean()) if unocc.any() else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--policy", default="transfer")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for dd in a.dirs:
        base = Path(dd)
        for f in sorted(base.glob(f"*/*/{a.policy}/diag.csv")):
            key = f"{f.parents[2].name}/{f.parents[1].name}"
            o = one(f.parent)
            if o is not None:
                o["set"] = base.name
                res[key] = o
                bm = o.get("share_by_mode", {})
                print(f"{key:<30} {o.get('cool_elec_w_per_m2', 0):5.2f}W/m2 nrm={o['cool_elec_w_per_ahu_norm']:.3f} "
                      f"vent={o.get('share_vent', 0):.2f} idle={o.get('share_idle_air', 0):.2f} "
                      f"rhc={o.get('share_reheat_while_cooling', 0):.2f} emiss={o.get('share_econ_missed', 0):.2f} "
                      f"eact={o.get('share_econ_active', 0):.2f} pre={bm.get('1', 0):.2f} sb={bm.get('2', 0):.2f} "
                      f"full={o.get('zone_cool_steps_full_damper_share', 0):.2f} "
                      f"p>1k={o.get('ahu_steps_p_gt_1000_share', 0):.2f} fanP={o.get('fan_share_above_floor', 0):.2f} "
                      f"flush={o.get('unocc_steps_oat_le_Tzone_minus3_share', 0):.2f} err={o['recon_rel_err']:+.4f}",
                      flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"-> {a.out} ({len(res)} scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
