"""Round 5: v8 with no parameter file must reproduce the frozen v7 file bit for bit (PREREG part 2).

Compares results/round5/regress/<a>/pub30/<b>/<w>/transfer/summary.json totals between two tags.
    python regress_r5.py [v7] [v8def]
"""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results" / "round5" / "regress"
a, b = (sys.argv[1:3] + ["v7", "v8def"][len(sys.argv[1:3]):])[:2]
rows, ok = [], True
for f in sorted((R / a / "pub30").glob("*/*/transfer/summary.json")):
    g = R / b / "pub30" / f.relative_to(R / a / "pub30")
    sa = json.loads(f.read_text())
    sb = json.loads(g.read_text()) if g.exists() else None
    same = sb is not None and sa["total_reward"] == sb["total_reward"] and sa["total_steps"] == sb["total_steps"]
    ok &= same
    rows.append({"scenario": f"{f.parts[-4]}/{f.parts[-3]}", a: sa["total_reward"],
                 b: sb["total_reward"] if sb else None, "identical": same})
    print(rows[-1])
out = {"ref": a, "test": b, "steps": 576, "all_identical": ok, "rows": rows}
(R / f"regress_{a}_vs_{b}.json").write_text(json.dumps(out, indent=1))
print("ALL IDENTICAL" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
