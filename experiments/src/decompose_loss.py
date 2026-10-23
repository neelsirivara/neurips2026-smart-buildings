"""Loss decomposition from run_diag.py outputs (round 3, goal 1).

For every <results-dir>/<building>/<weather>/<policy>/diag.csv the per-step loss (minus the
reward, in leaderboard units) is split into

    comfort      0.6 * (-normalized_productivity_regret)
    fan          the blower's share of 0.2 * energy_n + 0.2 * carbon_n
    cooling      the chiller's share
    pump         the hot-water pump's share
    gas          the boiler's share (energy by $ share, carbon by kg share)

using the plant energy rates logged in diag.csv (electricity $ and kg are split between the
three electric loads in proportion to their W; the gas kg rate is the kit's 53.12 kg/MMBtu).
Aggregates: per scenario, per station, per building, by hour of day, by policy mode
(0 occupied, 1 precondition, 2 setback; -1 when the policy does not expose it), occupied vs
unoccupied steps, weekday vs weekend. Also, from zones.npz: occupied zone-steps out of band,
the forced minimum-flow share of the supply air while heating, and per-zone recovery
statistics (time after 06:00 until the zone is inside the band, by zone area).

Usage:
    python decompose_loss.py --dirs ../results/round3/diag_v5_public ../results/round3/diag_v5_heldout \
        --policy transfer --out ../results/round3/loss_decomposition.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
W_COMFORT, W_ENERGY, W_CARBON = 0.6, 0.2, 0.2
STEPS = 8640
GAS_KG_PER_J = 53.12 / 293.07107 / 3.6e6          # kit constants: GAS_CO2 / KWH_PER_KFT3_GAS / JOULES_PER_KWH
CARBON_BY_HOUR = np.array([
    88.19666493, 87.79190866, 87.87607686, 87.83054163, 88.00279618, 88.19648183, 89.70663283, 93.97947901,
    98.85868291, 100.7853521, 101.3866866, 101.7795612, 102.5919168, 103.4403736, 104.1380294, 104.7359292,
    102.0714466, 97.04226176, 93.57895651, 92.46355045, 91.72914657, 90.69209747, 89.76552213, 88.99950995,
]) / 1.0e6 / 3600.0                                 # kg per W s
COMPONENTS = ("comfort", "fan", "cooling", "pump", "gas")
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore", "minneapolis")


def decompose(d: Path) -> dict | None:
    f = d / "diag.csv"
    if not f.exists():
        return None
    ts = pd.read_csv(f, parse_dates=["timestamp"])
    n = len(ts)
    if n == 0:
        return None
    dt = 300.0
    comfort = W_COMFORT * (-ts.regret_n.values)
    energy = W_ENERGY * ts.energy_n.values
    carbon = W_CARBON * ts.carbon_n.values
    cool_w = np.abs(ts.cool_w.values)                 # the kit bills |air_conditioning_electrical_energy_rate|
    elec_w = ts.blower_w.values + cool_w + ts.pump_w.values
    gas_w = ts.gas_w.values
    ec, gc = ts.elec_cost_usd.values, ts.gas_cost_usd.values
    tot_cost = np.where(ec + gc > 0, ec + gc, 1.0)
    e_elec = energy * ec / tot_cost
    e_gas = energy * gc / tot_cost
    hour = ts.timestamp.dt.hour.values
    kg_elec = elec_w * dt * CARBON_BY_HOUR[hour]
    kg_gas = gas_w * dt * GAS_KG_PER_J
    tot_kg = np.where(kg_elec + kg_gas > 0, kg_elec + kg_gas, 1.0)
    c_elec = carbon * kg_elec / tot_kg
    c_gas = carbon * kg_gas / tot_kg
    share = np.where(elec_w > 0, 1.0 / np.where(elec_w > 0, elec_w, 1.0), 0.0)
    comp = {
        "comfort": comfort,
        "fan": (e_elec + c_elec) * ts.blower_w.values * share,
        "cooling": (e_elec + c_elec) * cool_w * share,
        "pump": (e_elec + c_elec) * ts.pump_w.values * share,
        "gas": e_gas + c_gas,
    }
    total = comfort + energy + carbon
    kg_check = float(np.abs((kg_elec + kg_gas) - ts.carbon_kg.values).sum() / max(ts.carbon_kg.values.sum(), 1e-9))
    occ = ts.occupancy.values > 0
    mode = ts["mode"].values if "mode" in ts.columns else np.full(n, -1)
    wd = ts.timestamp.dt.dayofweek.values < 5
    out = {
        "steps": int(n),
        "metric": float(total.sum() / n),
        "components": {k: float(v.sum() / n) for k, v in comp.items()},
        "energy_term": float(energy.sum() / n), "carbon_term": float(carbon.sum() / n),
        "elec_components_energy_only": {
            "fan": float((e_elec * ts.blower_w.values * share).sum() / n),
            "cooling": float((e_elec * cool_w * share).sum() / n),
            "pump": float((e_elec * ts.pump_w.values * share).sum() / n),
            "gas": float(e_gas.sum() / n)},
        "carbon_components_only": {
            "fan": float((c_elec * ts.blower_w.values * share).sum() / n),
            "cooling": float((c_elec * cool_w * share).sum() / n),
            "pump": float((c_elec * ts.pump_w.values * share).sum() / n),
            "gas": float(c_gas.sum() / n)},
        "carbon_kg_split_check_relerr": kg_check,
        "by_hour": {k: [float(v[hour == h].sum() / n) for h in range(24)] for k, v in comp.items()},
        "by_mode": {str(m): {k: float(v[mode == m].sum() / n) for k, v in comp.items()}
                    for m in sorted(set(mode.tolist()))},
        "mode_step_share": {str(m): float((mode == m).mean()) for m in sorted(set(mode.tolist()))},
        "occupied_steps_share": float(occ.mean()),
        "by_occupancy": {"occupied": {k: float(v[occ].sum() / n) for k, v in comp.items()},
                         "unoccupied": {k: float(v[~occ].sum() / n) for k, v in comp.items()}},
        "by_daytype": {"weekday": {k: float(v[wd].sum() / n) for k, v in comp.items()},
                       "weekend": {k: float(v[~wd].sum() / n) for k, v in comp.items()}},
        "mean_w": {"blower": float(ts.blower_w.mean()), "cooling": float(cool_w.mean()),
                   "pump": float(ts.pump_w.mean()), "gas": float(gas_w.mean())},
        "ahu_on_share": float((ts.n_ahu_on.values > 0).mean()),
        "max_p_mean_when_on": float(ts.max_p_pa.values[ts.n_ahu_on.values > 0].mean()) if (ts.n_ahu_on.values > 0).any() else None,
    }
    z = d / "zones.npz"
    if z.exists():
        zz = np.load(z, allow_pickle=False)
        zt, zocc = zz["zone_t"], zz["zone_occ"]
        area = zz["zone_area_m2"]
        dev = np.maximum(0.0, np.maximum(294.0 - zt, zt - 297.0))
        occ_z = zocc > 0
        out["occupied_zone_steps_out_of_band"] = float((dev[occ_z] > 0).mean()) if occ_z.any() else None
        out["occupied_zone_steps_out_gt1k"] = float((dev[occ_z] > 1.0).mean()) if occ_z.any() else None
        # per-zone comfort loss proxy: occupancy-weighted deviation sum
        wdev = (dev * zocc).sum(axis=0)
        out["zone_area_m2"] = [float(a) for a in area]
        out["zone_weighted_deviation"] = [float(x) for x in wdev]
        # recovery: steps after 06:00 on workdays until the zone is >= 294 (heating) / <= 297
        ts_h = ts.timestamp.dt.hour.values + ts.timestamp.dt.minute.values / 60.0
        day = (ts.timestamp.dt.normalize() - ts.timestamp.dt.normalize().iloc[0]).dt.days.values
        rec = []
        for dd in np.unique(day):
            m = (day == dd) & wd & (ts_h >= 6.0) & (ts_h < 19.0)
            if not m.any() or not occ[m].any():
                continue
            sub = dev[m]                                    # steps x V
            first_in = np.array([int(np.argmax(sub[:, j] == 0)) if (sub[:, j] == 0).any() else sub.shape[0]
                                 for j in range(sub.shape[1])])
            rec.append(first_in * 5.0 / 60.0)                # hours after 06:00
        if rec:
            rec = np.array(rec)                              # days x V
            out["recovery_hours_after_6_mean_by_zone"] = [float(x) for x in rec.mean(axis=0)]
            big = area >= np.nanpercentile(area, 75) if np.isfinite(area).all() else np.zeros(len(area), bool)
            out["recovery_hours_mean_largest_quartile"] = float(rec[:, big].mean()) if big.any() else None
            out["recovery_hours_mean_rest"] = float(rec[:, ~big].mean()) if (~big).any() else None
        # forced minimum-flow share of supply air while the handler heats (dampers at the floor)
        dmp = zz["damper"]; run = zz["ahu_run"]; aoz = zz["ahu_of_zone"]; ahu_p = zz["ahu_p"]
        gas_on = gas_w > 1.0
        if gas_on.any() and (aoz >= 0).all():
            on_z = run[:, aoz] > 0
            f_real = np.sqrt(np.clip(ahu_p[:, aoz], 200.0, 2000.0) / 2000.0)
            flow_z = np.where(on_z, np.clip(dmp, 0.1, 1.0) * 2.0 * f_real, 0.0)
            idle = on_z & (dmp <= 0.1001)
            tot_flow = flow_z[gas_on].sum()
            out["minflow_idle_share_of_supply_air_while_heating"] = float(flow_z[gas_on][idle[gas_on]].sum() / tot_flow) if tot_flow > 0 else None
            out["idle_zone_share_while_heating"] = float(idle[gas_on].mean())
    return out


def agg(rows: dict[str, dict], keyfn) -> dict:
    groups = defaultdict(list)
    for k, r in rows.items():
        groups[keyfn(k, r)].append(r)
    out = {}
    for g, rs in sorted(groups.items()):
        out[g] = {"n": len(rs), "metric": float(np.mean([r["metric"] for r in rs])),
                  "components": {c: float(np.mean([r["components"][c] for r in rs])) for c in COMPONENTS},
                  "shares": {}}
        tot = out[g]["metric"]
        out[g]["shares"] = {c: (out[g]["components"][c] / tot if tot > 0 else None) for c in COMPONENTS}
        out[g]["by_hour"] = {c: [float(np.mean([r["by_hour"][c][h] for r in rs])) for h in range(24)] for c in COMPONENTS}
        modes = sorted({m for r in rs for m in r["by_mode"]})
        out[g]["by_mode"] = {m: {c: float(np.mean([r["by_mode"].get(m, {}).get(c, 0.0) for r in rs])) for c in COMPONENTS} for m in modes}
        out[g]["by_occupancy"] = {o: {c: float(np.mean([r["by_occupancy"][o][c] for r in rs])) for c in COMPONENTS} for o in ("occupied", "unoccupied")}
        for key in ("occupied_zone_steps_out_of_band", "recovery_hours_mean_largest_quartile", "recovery_hours_mean_rest",
                    "minflow_idle_share_of_supply_air_while_heating", "idle_zone_share_while_heating", "ahu_on_share"):
            vals = [r[key] for r in rs if r.get(key) is not None]
            out[g][key] = float(np.mean(vals)) if vals else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--policy", default="transfer")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--steps", type=int, default=STEPS, help="only runs of this length are used")
    a = ap.parse_args()
    rows: dict[str, dict] = {}
    for d in a.dirs:
        dp = Path(d)
        if not dp.is_absolute():
            dp = (HERE / d).resolve()
        for s in sorted(dp.glob(f"building_*/*/{a.policy}")):
            r = decompose(s)
            if r is None or r["steps"] != a.steps:
                continue
            key = f"{s.parts[-3]}/{s.parts[-2]}"
            r["set"] = dp.name
            rows[key] = r
            print(f"{key:36s} metric {r['metric']:.5f}  " + "  ".join(f"{c} {r['components'][c]:.5f}" for c in COMPONENTS), flush=True)
    if not rows:
        print("no complete diag runs found")
        return 1
    out = {
        "label": a.label, "policy": a.policy, "n_scenarios": len(rows),
        "components_doc": "leaderboard units (loss per step), comfort = 0.6*regret, fan/cooling/pump/gas = their share of 0.2*energy + 0.2*carbon",
        "overall": agg(rows, lambda k, r: "all")["all"],
        "by_set": agg(rows, lambda k, r: r["set"]),
        "by_station": agg(rows, lambda k, r: k.split("/")[1].rsplit("_", 1)[0]),
        "by_building": agg(rows, lambda k, r: k.split("/")[0]),
        "per_scenario": {k: {kk: vv for kk, vv in r.items() if kk not in ("zone_area_m2", "zone_weighted_deviation", "recovery_hours_after_6_mean_by_zone")}
                         for k, r in rows.items()},
        "per_scenario_zones": {k: {kk: r.get(kk) for kk in ("zone_area_m2", "zone_weighted_deviation", "recovery_hours_after_6_mean_by_zone")}
                               for k, r in rows.items()},
    }
    op = Path(a.out)
    if not op.is_absolute():
        op = (HERE / a.out).resolve()
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1))
    o = out["overall"]
    print(f"\n== {a.label} n={len(rows)} metric={o['metric']:.5f}")
    print("   components: " + "  ".join(f"{c} {o['components'][c]:.5f} ({100*o['shares'][c]:.1f}%)" for c in COMPONENTS))
    for st, g in out["by_station"].items():
        print(f"   {st:10s} n={g['n']:2d} metric={g['metric']:.5f} " + " ".join(f"{c}={100*(g['shares'][c] or 0):.0f}%" for c in COMPONENTS)
              + f"  out-of-band={g['occupied_zone_steps_out_of_band']}")
    print("   by mode (mean over scenarios, loss per step):")
    for m, v in o["by_mode"].items():
        print(f"     mode {m}: " + " ".join(f"{c}={v[c]:.5f}" for c in COMPONENTS))
    print("   by hour (total): " + " ".join(f"{h}:{sum(o['by_hour'][c][h] for c in COMPONENTS):.4f}" for h in range(24)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
