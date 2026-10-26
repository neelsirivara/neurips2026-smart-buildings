"""Round-5 decision under PREREG part 2 (composite, then C*), recorded with time stamps in results/round5/decision.json.

    python decide_round5.py composite     # after the single-change screen: build r5_c12_comp.json (or nothing)
    python decide_round5.py choose        # after the composite screen: C* = lowest held metric among helps
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R5 = HERE.parent / "results" / "round5"
CANDS = HERE / "policy_candidates"
FAMILIES = {"monday": ["r5_c01_mon15", "r5_c02_mon125"], "weekend": ["r5_c03_wk3", "r5_c04_wk6"],
            "lag": ["r5_c05_lag10", "r5_c06_lag05"], "fcapc": ["r5_c07_fcapc05"], "qsb": ["r5_c08_qsb8k"],
            "preburst": ["r5_c09_preburst"], "qcap": ["r5_c10_qcap20k", "r5_c11_qcap30k"]}
COMP = "r5_c12_comp"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    cmd = sys.argv[1]
    ss = json.loads((R5 / "screen_summary.json").read_text())
    dec_path = R5 / "decision.json"
    dec = json.loads(dec_path.read_text()) if dec_path.exists() else {"log": []}
    c = ss["candidates"]
    if cmd == "composite":
        incomplete = [k for k, v in c.items() if v["verdict"] == "incomplete"]
        if incomplete:
            print("incomplete:", incomplete)
            return 1
        members, params = [], {}
        for fam, names in FAMILIES.items():
            ok = [n for n in names if n in c and c[n]["verdict"] == "helps"]
            if not ok:
                continue
            best = min(ok, key=lambda n: c[n]["held"]["cand"])
            members.append(best)
            params.update(json.loads((CANDS / f"{best}.json").read_text()))
        dec["singles_verdicts"] = {k: v["verdict"] for k, v in c.items()}
        dec["composite_members"] = members
        if len(members) >= 2:
            (CANDS / f"{COMP}.json").write_text(json.dumps(params, indent=1))
            dec["composite"] = COMP
            dec["composite_params"] = params
        else:
            dec["composite"] = None
        dec["log"].append({"time": now(), "step": "composite", "members": members})
        print("composite members:", members, "->", dec["composite"])
    elif cmd == "choose":
        pool = [k for k, v in c.items() if v["verdict"] == "helps" and (k == dec.get("composite") or not k.endswith("comp"))]
        if dec.get("composite") and c.get(dec["composite"], {}).get("verdict") == "incomplete":
            print("composite screen incomplete")
            return 1
        chosen = min(pool, key=lambda n: c[n]["held"]["cand"]) if pool else None
        dec["pool"] = pool
        dec["chosen"] = chosen
        dec["log"].append({"time": now(), "step": "choose", "pool": pool, "chosen": chosen})
        print("pool:", pool, "-> chosen:", chosen)
    dec_path.write_text(json.dumps(dec, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
