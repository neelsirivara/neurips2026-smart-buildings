"""Round 13 PLAN.md ship choice, applied mechanically: among {r12var, r13cand} those passing Primary, Guard 1 and
Guard 2 (HS below-5 C share <= v12 + 0.25 pp and HS coldest >= v12 - 1.0 C); lowest mixture wins; else v12."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1] / "results"
cands = {"r12var": json.loads((R / "round12" / "decision_r12var.json").read_text()),
         "r13cand": json.loads((R / "round13" / "decision.json").read_text())}
out = {}
for k, d in cands.items():
    f = d["frost"]
    g2 = f["below5_cand"] <= f["below5_v12"] + 0.0025 and f["coldest_c_cand"] >= f["coldest_c_v12"] - 1.0
    out[k] = {"mixture": d["mixture"], "mixture_ci": d["mixture_ci"], "pub30": d["pub30"], "primary": d["primary_pass"],
              "guard1": d["guard_pass"], "guard2_frost": g2, "below5": f["below5_cand"], "coldest_c": f["coldest_c_cand"],
              "eligible": bool(d["complete"] and d["primary_pass"] and d["guard_pass"] and g2)}
ok = [k for k in out if out[k]["eligible"]]
out["choice"] = min(ok, key=lambda k: out[k]["mixture"]) if ok else "v12"
(R / "round13" / "choice.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
