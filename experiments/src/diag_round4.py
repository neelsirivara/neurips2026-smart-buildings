"""Round-4 diagnosis of SADR v6 (shipped) from the round-3 full-length diagnostic runs.

Per scenario (diag.csv + zones.npz of run_diag.py, Mac, 8,640 steps), on top of diag_cooling_r4.one():
  * fan: share of fan power above the 200 Pa floor, attributed to the handler's supply-air regime
    (mixed-handler floor 292 K / coldest 285 K / other = heating-only), and the corresponding loss
    (fan loss from the round-3 decomposition x that share)
  * gas: outside-air (ventilation) heat of running handlers / boiler gas, and the heat the forced minimum
    flow of idle zones (damper at the floor, valve shut) removes from them, by policy mode
Aggregates by set (public / heldout / r3) and by station; writes results/round4/diag_round4.json.

    python diag_round4.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from diag_cooling_r4 import one

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
RC = 1.2 * 1006.0
SETS = {"public": ("final_v6_public", "loss_decomposition_public_v6.json"),
        "heldout": ("final_v6_heldout", "loss_decomposition_heldout_v6.json"),
        "r3": ("final_v6_r3", "loss_decomposition_heldout_r3_v6.json")}


def extra(d: Path) -> dict:
    ts = pd.read_csv(d / "diag.csv")
    z = np.load(d / "zones.npz")
    A = z["zone_area_m2"].astype(float)
    T = z["zone_t"].astype(float)
    aoz = z["ahu_of_zone"].astype(int)
    run = z["ahu_run"] > 0
    K = run.shape[1]
    r = z["ahu_recirc"].astype(float)
    fl = z["ahu_flow"].astype(float)
    p = z["ahu_p"].astype(float)
    sat = z["ahu_sat"].astype(float)
    dm = z["damper"].astype(float)
    vl = z["valve"].astype(float)
    oat = ts.oat_k.values.astype(float)
    mode = ts["mode"].values
    gas = ts.gas_w.values.astype(float)
    fan = fl * np.maximum(p, 200.0) / 0.9 * (2.0 - r)        # supply + exhaust (exhaust carries 1 - r)
    extra_fan = fl * (np.maximum(p, 200.0) - 200.0) / 0.9 * (2.0 - r)
    o = {}
    ftot = fan[run].sum()
    if ftot > 0:
        hi = run & (p > 300.0)
        ex = extra_fan[run].sum()
        o["fan_above_floor_share"] = float(ex / ftot)
        o["fan_above_floor_regime"] = {
            "mixed_292": float(extra_fan[hi & (np.abs(sat - 292.0) < 0.05)].sum() / max(ex, 1e-9)),
            "cold_285": float(extra_fan[hi & (sat < 285.05)].sum() / max(ex, 1e-9)),
            "heating_or_other": float(extra_fan[hi & (np.abs(sat - 292.0) >= 0.05) & (sat >= 285.05)].sum() / max(ex, 1e-9))}
        o["fan_above_floor_by_mode"] = {str(m): float(extra_fan[mode == m].sum() / max(ex, 1e-9)) for m in (0, 1, 2)}
    if gas.sum() > 0:
        Tret = np.stack([(T[:, aoz == k] * A[aoz == k]).sum(1) / max(A[aoz == k].sum(), 1e-9) for k in range(K)], 1)
        mix = r * Tret + (1 - r) * oat[:, None]
        vent = np.where(run, fl * RC * (1 - r) * np.maximum(Tret - oat[:, None], 0.0), 0.0).sum(1)
        zf = dm * np.sqrt(np.maximum(p[:, aoz], 0.0) / 2000.0) * 2.0
        idle = (vl <= 1e-3) & (dm > 0) & run[:, aoz]
        idle_cool = np.where(idle, zf * RC * np.maximum(T - mix[:, aoz], 0.0), 0.0).sum(1)
        g = gas.sum()
        o["gas_kw_mean"] = float(gas.mean() / 1e3)
        o["vent_heat_over_gas"] = float(vent.sum() / g)
        o["idle_zone_cooling_over_gas_by_mode"] = {str(m): float(idle_cool[mode == m].sum() / g) for m in (0, 1, 2)}
        o["gas_share_by_mode"] = {str(m): float(gas[mode == m].sum() / g) for m in (0, 1, 2)}
        o["oat_mean_c"] = float(oat.mean() - 273.15)
    return o


def main() -> int:
    out = {"doc": __doc__.strip().splitlines()[0], "per_scenario": {}, "by_set": {}, "by_station": {}}
    for set_name, (dname, decf) in SETS.items():
        dec = json.loads((RES / "round3" / decf).read_text())["per_scenario"]
        for d in sorted((RES / "mac" / "round3" / dname).glob("*/*/transfer")):
            key = f"{d.parts[-3]}/{d.parts[-2]}"
            o = one(d) or {}
            o.update(extra(d))
            comp = dec[key]["components"]
            o["loss_components"] = comp
            o["metric"] = dec[key]["metric"]
            if "fan_above_floor_share" in o:
                o["fan_above_floor_loss"] = comp["fan"] * o["fan_above_floor_share"]
                o["fan_above_floor_loss_mixed_292"] = o["fan_above_floor_loss"] * o["fan_above_floor_regime"]["mixed_292"]
                o["fan_above_floor_loss_cold_285"] = o["fan_above_floor_loss"] * o["fan_above_floor_regime"]["cold_285"]
            o["set"] = set_name
            out["per_scenario"][key] = o
    ps = out["per_scenario"]

    def agg(keys):
        def m(f):
            v = [f(ps[k]) for k in keys]
            v = [x for x in v if x is not None]
            return float(np.mean(v)) if v else None
        return {"n": len(keys),
                "metric": m(lambda o: o["metric"]),
                "cooling_loss": m(lambda o: o["loss_components"]["cooling"]),
                "fan_loss": m(lambda o: o["loss_components"]["fan"]),
                "gas_loss": m(lambda o: o["loss_components"]["gas"]),
                "fan_above_floor_loss": m(lambda o: o.get("fan_above_floor_loss", 0.0)),
                "fan_above_floor_loss_mixed_292": m(lambda o: o.get("fan_above_floor_loss_mixed_292", 0.0)),
                "fan_above_floor_loss_cold_285": m(lambda o: o.get("fan_above_floor_loss_cold_285", 0.0)),
                "cool_elec_w_per_m2_hot": m(lambda o: o.get("cool_elec_w_per_m2") if any(s in o.get("start", "") for s in ()) else None),
                "area_per_ahu_m2": m(lambda o: o["area_per_ahu_m2"]),
                "median_zone_m2": m(lambda o: o["median_zone_m2"])}
    for set_name in SETS:
        keys = [k for k, o in ps.items() if o["set"] == set_name]
        out["by_set"][set_name] = agg(keys)
        for st in ("fairbanks", "denver", "atlanta", "phoenix", "singapore"):
            kk = [k for k in keys if k.split("/")[1].startswith(st)]
            a = agg(kk)
            a["cool_elec_w_per_m2"] = float(np.mean([ps[k]["cool_elec_w_per_m2"] for k in kk]))
            a["cool_elec_per_ahu_norm"] = float(np.mean([ps[k]["cool_elec_w_per_ahu_norm"] for k in kk]))
            a["vent_heat_over_gas"] = float(np.mean([ps[k]["vent_heat_over_gas"] for k in kk if "vent_heat_over_gas" in ps[k]] or [np.nan]))
            a["idle_cool_unocc_over_gas"] = float(np.mean([ps[k]["idle_zone_cooling_over_gas_by_mode"]["1"] + ps[k]["idle_zone_cooling_over_gas_by_mode"]["2"]
                                                           for k in kk if "idle_zone_cooling_over_gas_by_mode" in ps[k]] or [np.nan]))
            a["flush_share_unocc"] = float(np.mean([ps[k].get("unocc_steps_oat_le_Tzone_minus3_share", 0.0) for k in kk]))
            a["share_precond_of_cooling"] = float(np.mean([ps[k]["share_by_mode"]["1"] for k in kk if "share_by_mode" in ps[k]] or [np.nan]))
            a["share_setback_of_cooling"] = float(np.mean([ps[k]["share_by_mode"]["2"] for k in kk if "share_by_mode" in ps[k]] or [np.nan]))
            a["share_vent_of_cooling"] = float(np.mean([ps[k]["share_vent"] for k in kk if "share_vent" in ps[k] and ps[k]["share_vent"] > -1] or [np.nan]))
            out["by_station"][f"{set_name}/{st}"] = a
    (RES / "round4" / "diag_round4.json").write_text(json.dumps(out, indent=1))
    for k, v in out["by_set"].items():
        print(k, {a: (round(b, 6) if isinstance(b, float) else b) for a, b in v.items()})
    for k, v in out["by_station"].items():
        print(f"{k:<20} metric={v['metric']:.5f} cool={v['cooling_loss']:.5f} W/m2={v['cool_elec_w_per_m2']:.2f} "
              f"perAHU={v['cool_elec_per_ahu_norm']:.3f} fan_above={v['fan_above_floor_loss']:.5f} vent/gas={v['vent_heat_over_gas']:.2f} "
              f"idle/gas={v['idle_cool_unocc_over_gas']:.3f} flush={v['flush_share_unocc']:.2f} pre/cool={v['share_precond_of_cooling']:.2f} "
              f"sb/cool={v['share_setback_of_cooling']:.2f} vent/cool={v['share_vent_of_cooling']:.2f}")
    print("-> results/round4/diag_round4.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
