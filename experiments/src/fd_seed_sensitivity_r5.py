"""Round 5: how close the FD condition of the ship rule is -- the paired-bootstrap 97.5% bound of the candidate-minus-v7
difference on FD for the pre-registered seed 0 and seeds 1-9 (5,000 resamples each)."""
import json
from pathlib import Path

import numpy as np

R5 = Path(__file__).resolve().parent.parent / "results" / "round5"
cf = json.loads((R5 / "confirm_r5_c12_comp.json").read_text())
out = {}
for name in ("FD", "pub30", "r5m", "P+M"):
    per = cf["sets"][name]["per_scenario"]
    d = np.array([v["cand"] - v["v7"] for v in per.values()])
    his = {}
    for seed in range(10):
        rng = np.random.default_rng(seed)
        b = d[rng.integers(0, len(d), size=(5000, len(d)))].mean(axis=1)
        his[seed] = float(np.percentile(b, 97.5))
    out[name] = {"n": len(d), "upper_97_5_by_seed": his, "n_seeds_upper_below_zero": sum(v < 0 for v in his.values())}
(R5 / "fd_seed_sensitivity.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, v["n_seeds_upper_below_zero"], "/10 seeds with upper bound < 0; seed0", v["upper_97_5_by_seed"][0],
          "max", max(v["upper_97_5_by_seed"].values()))
