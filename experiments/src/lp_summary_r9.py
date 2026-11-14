"""Round 9: summary of the perfect-foresight LP bounds (lp_bound_r9.py outputs fetched into results/round9/mac/lp_bound).

Per scenario: v10 loss, linear-model check (zone-temperature RMSE of the replay), and three bounds:
  hard   -- gas saved (share of v10 gas) with comfort held at min(294 K, v10) on every occupied check, zones
            optimised independently (others at their v10 trajectories): optimistic;
  score  -- leaderboard loss saved (share of v10 loss) with comfort priced at the score's weight, independent zones;
  gs     -- the same objective solved by Gauss-Seidel sweeps with the cross-zone responses and scored jointly:
            an achievable point of the linear model (lower estimate of the joint optimum).
Plus where the heat changes: the LP's net-heat change by hour of day (kWh, summed over zones and days).

    python lp_summary_r9.py -> results/round9/lp_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LPD = HERE.parent / "results" / "round9" / "mac" / "lp_bound"
OUT = HERE.parent / "results" / "round9" / "lp_summary.json"


def hour_profile(npz: Path) -> list[float] | None:
    if not npz.exists():
        return None
    z = np.load(npz, allow_pickle=False)
    dq = z["dq"]                                      # zones x blocks (W)
    blk = int(z["blk"])
    ts = z["ts"]
    hours = np.array([int(str(t)[11:13]) for t in ts[::blk][: dq.shape[1]]])
    prof = np.zeros(24)
    good = np.isfinite(dq)
    e = np.where(good, dq, 0.0).sum(axis=0) * blk * 300.0 / 3.6e6   # kWh per block, all zones
    np.add.at(prof, hours[: len(e)], e)
    return prof.round(1).tolist()


def main() -> int:
    out = {}
    for d in sorted(LPD.glob("*/building_*/*")):
        if d.name.endswith("_oldcode"):
            continue
        key = f"{d.parts[-3]}/{d.parts[-2]}/{d.parts[-1]}"
        r = {}
        for tag in ("lp_bound", "lp_bound_score", "lp_bound_score_gs2", "lp_bound_score_gs8", "lp_bound_score_gs16"):
            f = d / f"{tag}.json"
            if not f.exists():
                continue
            j = json.loads(f.read_text())
            r["v10_loss"] = j["v10_total_loss_per_step"]
            r["validation_rmse_k"] = j["validation_rmse_k"]
            if tag == "lp_bound":
                r["hard_gas_share"] = j["lp_save_gas_share"]
                r["hard_heat_kwh"] = j["lp_save_heat_kwh"]
                r["hard_profile_kwh_by_hour"] = hour_profile(d / "lp_bound_profiles.npz")
            elif tag == "lp_bound_score":
                r["score_loss_share"] = j["lp_save_loss_share"]
                r["score_profile_kwh_by_hour"] = hour_profile(d / "lp_bound_score_profiles.npz")
            else:
                r["gs_loss_share"] = j["lp_save_loss_share"]
                r["gs_detail"] = j.get("gs")
        out[key] = r
        print(f"{key:40s} " + " ".join(f"{k}={v:.4f}" for k, v in r.items() if isinstance(v, float)))
    keys = [k for k, v in out.items() if "gs_loss_share" in v]
    if keys:
        out["_mean"] = {m: float(np.mean([out[k][m] for k in keys if m in out[k]]))
                        for m in ("hard_gas_share", "score_loss_share", "gs_loss_share", "validation_rmse_k")}
        print("mean", out["_mean"])
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
