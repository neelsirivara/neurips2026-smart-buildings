"""Round 9: where v10's comfort loss comes from -- below the band (heating short) vs above it (cooling short), by hour.

Reads run_diag outputs (zones.npz: zone_t, zone_occ) under results/round9/v10diag/<set>/ and recomputes the score's
comfort term per step, 0.6 * sum_z occ_z * shortfall_z / sum_z occ_z with shortfall = deviation / 5 K (linear branch;
deviations above 5 K use the kit's quadratic branch), split by the side of the band.  Band: 294-297 K in comfort hours
(06-19 weekdays), which is when occupants are present.

    python comfort_split_r9.py -> results/round9/comfort_split.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
D = HERE.parent / "results" / "round9" / "v10diag"


def shortfall(dev: np.ndarray) -> np.ndarray:
    return np.where(dev <= 5.0, dev / 5.0, 1.0 + ((dev - 5.0) / 5.0) ** 2)


def main() -> int:
    out = {}
    for f in sorted(D.glob("*/building_*/*/transfer/zones.npz")):
        z = np.load(f)
        ts = pd.read_csv(f.parent / "diag.csv", usecols=["timestamp"]).timestamp
        hod = pd.to_datetime(ts).dt.hour.values
        T, occ = z["zone_t"].astype(float), z["zone_occ"].astype(float)
        n = min(len(T), len(hod))
        T, occ, hod = T[:n], occ[:n], hod[:n]
        tot = occ.sum(axis=1)
        w = np.where(tot[:, None] > 0, occ / np.maximum(tot[:, None], 1e-9), 0.0)
        lo = (w * shortfall(np.maximum(294.0 - T, 0.0))).sum(axis=1) * 0.6
        hi = (w * shortfall(np.maximum(T - 297.0, 0.0))).sum(axis=1) * 0.6
        key = f"{f.parts[-5]}/{f.parts[-4]}/{f.parts[-3]}"
        out[key] = {"below": float(lo.mean()), "above": float(hi.mean()),
                    "above_by_hour": [float(hi[hod == h].sum() / max(hi.sum(), 1e-12)) for h in range(24)],
                    "below_by_hour": [float(lo[hod == h].sum() / max(lo.sum(), 1e-12)) for h in range(24)]}
    for s in ("pub30", "r7hc"):
        ks = [k for k in out if k.startswith(s)]
        if ks:
            b = np.mean([out[k]["below"] for k in ks])
            a = np.mean([out[k]["above"] for k in ks])
            out[f"_mean_{s}"] = {"n": len(ks), "below": float(b), "above": float(a)}
            print(s, len(ks), f"comfort below band {b:.6f}  above band {a:.6f} per step")
    (HERE.parent / "results" / "round9" / "comfort_split.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
