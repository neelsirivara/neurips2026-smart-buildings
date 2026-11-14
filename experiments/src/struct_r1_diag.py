"""struct_r1: diagnostics of the v13 reference on the 24 screen windows (time series + SADR debug log).

    python struct_r1_diag.py fetchdbg <variant>   # copy the Mac debug logs into results/struct_r1/dbg/
    python struct_r1_diag.py diag <variant>       # writes results/struct_r1/diag_<variant>.json
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cma_r12 as c  # noqa: E402
import struct_r1 as s1  # noqa: E402

DBG = s1.OUT / "dbg"


def fetchdbg(var: str) -> None:
    r = s1.ssh(f"cd {s1.MAC}/dbg && ls {var}__*.csv | tar cf - -T -", timeout=900)
    DBG.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for m in tf.getmembers():
            if m.isfile() and "/" not in m.name and m.name.startswith(var + "__"):
                (DBG / m.name).write_bytes(tf.extractfile(m).read())


def rows(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def diag(var: str) -> dict:
    harsh, public = c.scenario_list()
    out = {}
    for grp, lst in (("harsh", harsh), ("public", public)):
        # per hour of day x (workday, non-workday): mean per-step contribution of comfort / energy / carbon
        acc = defaultdict(lambda: np.zeros(4))
        mode_acc = defaultdict(lambda: np.zeros(5))
        empty_after13 = [0, 0]
        n_steps = 0
        for s, k in lst:
            ts = rows(s1.RUNS / var / s / k / "timeseries.csv")
            dbg = rows(DBG / f"{var}__{s}__{k.replace('/', '__')}.csv")
            sm = json.loads((s1.RUNS / var / s / k / "summary.json").read_text())
            wsum = sm["productivity_weight"] + sm["energy_weight"] + sm["carbon_weight"]
            wp, we, wc = (sm["productivity_weight"] / wsum, sm["energy_weight"] / wsum, sm["carbon_weight"] / wsum)
            for i, r in enumerate(ts):
                d = dbg[i] if i < len(dbg) else None
                hod = int(float(d["hod"])) if d else 0
                wd = d is not None and float(d["dow"]) < 5 - 1e-6
                key = f"{'wd' if wd else 'we'}{hod:02d}"
                acc[key] += [-float(r["productivity_regret"]) * wp, float(r["energy_cost"]) * we,
                             float(r["carbon"]) * wc, 1]
                if d:
                    mode_acc[key] += [int(d["mode"]) == 0, int(d["mode"]) == 1, int(d["mode"]) == 2,
                                      int(d["n_heat"]) > 0, int(d["n_cool"]) > 0]
                    if wd and 13 <= hod < 19 and int(d["now"]) == 1:
                        empty_after13[1] += 1
                        empty_after13[0] += int(d["occupied"]) == 0
                n_steps += 1
        tot = sum(v[:3].sum() for v in acc.values())
        out[grp] = {
            "n_steps": n_steps,
            "loss_share_by_slot": {k: {"comfort": v[0] / tot, "energy": v[1] / tot, "carbon": v[2] / tot,
                                       "steps": int(v[3]),
                                       "frac_occ_mode": mode_acc[k][0] / v[3], "frac_pre": mode_acc[k][1] / v[3],
                                       "frac_sb": mode_acc[k][2] / v[3], "frac_heat": mode_acc[k][3] / v[3],
                                       "frac_cool": mode_acc[k][4] / v[3]}
                                   for k, v in sorted(acc.items())},
            "share_comfort": sum(v[0] for v in acc.values()) / tot,
            "share_energy": sum(v[1] for v in acc.values()) / tot,
            "share_carbon": sum(v[2] for v in acc.values()) / tot,
            "weekday_13_19_steps_building_empty": empty_after13,
        }
    (s1.OUT / f"diag_{var}.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "fetchdbg":
        fetchdbg(sys.argv[2])
    else:
        o = diag(sys.argv[2])
        for g, d in o.items():
            print(g, {k: round(d[k], 4) for k in ("share_comfort", "share_energy", "share_carbon")},
                  "empty 13-19:", d["weekday_13_19_steps_building_empty"])
            for k, v in d["loss_share_by_slot"].items():
                tot = v["comfort"] + v["energy"] + v["carbon"]
                print(f"  {k}: loss {100 * tot:5.2f}% (comf {100 * v['comfort']:4.2f}) occ {v['frac_occ_mode']:.2f} "
                      f"pre {v['frac_pre']:.2f} sb {v['frac_sb']:.2f} heat {v['frac_heat']:.2f} cool {v['frac_cool']:.2f}")
