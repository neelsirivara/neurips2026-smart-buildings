"""Round 5: the cold-capacity case in r5m (v7 on building_train_7/minneapolis_1), from its diag run.

For each zone with occupied steps below the 294 K band edge: count, mean deficit, damper, valve, handler pressure,
outside air; plus the zone's request cap (q_cap_w x area scale) against the water-side limit of its box
(valve open at 20 bar, 350 K water, mixed air at 0.7 x return + 0.3 x outside), from the v7 DEFAULT_PARAMS.
Writes results/round5/analysis/capacity_b7m1.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

R5 = Path(__file__).resolve().parent.parent / "results" / "round5"
d = R5 / "full" / "v7" / "r5m" / "building_train_7" / "minneapolis_1" / "transfer"
z = np.load(d / "zones.npz")
df = pd.read_csv(d / "diag.csv")
T, occ, dam, val = z["zone_t"], z["zone_occ"], z["damper"], z["valve"]
ahu, P, area = z["ahu_of_zone"], z["ahu_p"], z["zone_area_m2"]
oat = df["oat_k"].to_numpy()
cold = (T < 294.0) & (occ > 0)
occ_steps = (occ > 0).sum(axis=0)
rows = []
cap1 = 1000.0 * 4180.0 * 0.108 / 3600.0
for i in np.argsort(-cold.sum(axis=0)):
    m = cold[:, i]
    if m.sum() < 100:
        break
    t_sa = 0.7 * T[m, i].mean() + 0.3 * oat[m].mean()
    c_w = cap1 * np.sqrt(20.0)
    water_net = c_w * (350.0 - t_sa) * (308.15 - T[m, i].mean()) / (308.15 - t_sa)
    req_cap = 12000.0 * float(np.clip(area[i] / 100.0, 1.0, 6.0))
    rows.append({"zone": int(i), "area_m2": float(area[i]), "cold_occupied_steps": int(m.sum()),
                 "occupied_steps": int(occ_steps[i]), "mean_deficit_k": float(294.0 - T[m, i].mean()),
                 "mean_damper": float(dam[m, i].mean()), "mean_valve": float(val[m, i].mean()),
                 "mean_handler_pa": float(P[m, ahu[i]].mean()), "mean_oat_c": float(oat[m].mean() - 273.15),
                 "request_cap_w": req_cap, "water_side_net_heat_w": float(water_net)})
comfort = -0.6 * df["regret_n"].to_numpy()
res = {"scenario": "building_train_7/minneapolis_1", "metric": float(abs(df["reward"].sum()) / len(df)),
       "comfort_per_step": float(comfort.sum() / len(df)), "zones": rows}
(R5 / "analysis" / "capacity_b7m1.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
