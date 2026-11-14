"""Round 9 (analysis only): what the boiler billing quirk would do to v10's score, and whether it explains the top.

Reads the Mac outputs of quirk_probe_r9.py (results/round9/mac/quirk_probe/<set>/<b>/<w>/{quirk,ref}/summary.json),
pairs each with v10's official run (results/round6/runs/r7L_mbr2/<set>/...), and extrapolates by station to the full
public 30 and HC2: each scenario's v10 loss is scaled by the probe ratio of its station (mean over the station's
probes).  Kaggle mixture: K = c (0.66 P + 0.34 H), with c calibrated on v10's own Kaggle score 0.01055 (round 6 fitted
the 66/34 shares with HC; HC2 is colder, hence c < 1).  Nothing here is a policy.

    python quirk_summary_r9.py -> results/round9/quirk_summary.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
Q = RES / "round9" / "mac" / "quirk_probe"
REF = RES / "round6" / "runs" / "r7L_mbr2"
SETS = {"P30": "pub30", "HC2": "r7hc"}
K_V10 = 0.01055


def loss(f: Path) -> float:
    d = json.loads(f.read_text())
    return -d["total_reward"] / d["total_steps"]


def main() -> int:
    out = {"probes": {}, "ratio_by_station": {}, "sets": {}}
    ratios = defaultdict(list)
    for sname, rname in SETS.items():
        for f in sorted((Q / sname).glob("building_*/*/quirk/summary.json")):
            b, w = f.parts[-4], f.parts[-3]
            r = REF / rname / b / w / "transfer" / "summary.json"
            lq, lv = loss(f), loss(r)
            st = w.rsplit("_", 1)[0]
            dq = json.loads(f.read_text())
            dv = json.loads(r.read_text())
            out["probes"][f"{sname}/{b}/{w}"] = {
                "v10": lv, "quirk": lq, "ratio": lq / lv,
                "comfort_v10": -0.6 * dv["total_normalized_productivity_regret"] / dv["total_steps"],
                "comfort_quirk": -0.6 * dq["total_normalized_productivity_regret"] / dq["total_steps"]}
            ratios[st].append(lq / lv)
    out["ratio_by_station"] = {s: float(np.mean(v)) for s, v in ratios.items()}
    ref_chk = Q / "P30" / "building_train_1" / "atlanta_2" / "ref" / "summary.json"
    if ref_chk.exists():
        out["harness_check_ref_vs_official"] = {
            "harness": json.loads(ref_chk.read_text())["total_reward"],
            "official": json.loads((REF / "pub30" / "building_train_1" / "atlanta_2" / "transfer" / "summary.json").read_text())["total_reward"]}
    for sname, rname in SETS.items():
        lv, lq, miss = [], [], []
        for f in sorted((REF / rname).glob("building_*/*/transfer/summary.json")):
            st = f.parts[-3].rsplit("_", 1)[0]
            v = loss(f)
            lv.append(v)
            if st in out["ratio_by_station"]:
                lq.append(v * out["ratio_by_station"][st])
            else:
                miss.append(f.parts[-3])
                lq.append(v)
        out["sets"][sname] = {"n": len(lv), "v10": float(np.mean(lv)), "quirk_est": float(np.mean(lq)),
                              "ratio": float(np.mean(lq) / np.mean(lv)), "stations_without_probe": sorted(set(miss))}
    P, H = out["sets"]["P30"], out["sets"]["HC2"]
    c = K_V10 / (0.66 * P["v10"] + 0.34 * H["v10"])
    out["kaggle"] = {"c": c, "v10_actual": K_V10, "v10_mixture": c * (0.66 * P["v10"] + 0.34 * H["v10"]),
                     "quirk_predicted": c * (0.66 * P["quirk_est"] + 0.34 * H["quirk_est"])}
    (RES / "round9" / "quirk_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "probes"}, indent=1))
    for k, v in out["probes"].items():
        print(f"  {k:36s} v10 {v['v10']:.5f} quirk {v['quirk']:.5f} ratio {v['ratio']:.3f} comfort {v['comfort_v10']:.5f}->{v['comfort_quirk']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
