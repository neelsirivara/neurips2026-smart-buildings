"""Round 5 (intel idea S7): AHU starts per handler per day of v7, from existing diag runs."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

res = collections.defaultdict(list)
for tree, label in [("final_r4", "pub30"), ("mac/round4/full/r4_c14_comp_a/old40", "old40")]:
    for f in Path(tree).glob("*/*/transfer/zones.npz"):
        z = np.load(f)
        run = z["ahu_run"] > 0.5
        starts = (run[1:] & ~run[:-1]).sum(axis=0)
        station = f.parts[-3].rsplit("_", 1)[0]
        res[(label, station)].append(float(starts.mean() / 30.0))
out = {f"{k[0]}/{k[1]}": round(float(np.mean(v)), 2) for k, v in sorted(res.items())}
print("AHU starts per AHU per day:", out)
Path("round5/analysis/ahu_starts_per_day_v7.json").write_text(json.dumps(out, indent=1))
