"""Round 9: one numbers file for the write-up (DEEP_DIVE section R9, STATUS round 9).

Collects: the v10 decomposition (Kaggle diag runs: results/round9/decomp_v10_{pub30,hc2}.json; else the 12 Mac runs),
the delivery / loop bounds (bound_r9_v10.json), the LP trajectory bounds (lp_summary.json), the quirk measurement
(quirk_summary.json), the screen / confirmation of round-9 candidates (screen_summary.json, confirm_*.json) and the
leaderboard read (intel/lb_p*.csv).

    python summary_r9.py -> results/round9/summary_r9.json (and a printed digest)
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
R9 = HERE.parent / "results" / "round9"


def jl(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def lb() -> dict | None:
    rows = []
    for f in sorted((R9 / "intel").glob("lb_p*_*.csv")):
        txt = [l for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if not l.startswith("Next Page")]
        rows += list(csv.DictReader(io.StringIO("\n".join(txt))))
    sc = sorted(float(r["score"]) for r in rows if r.get("score") and r["score"].replace(".", "", 1).isdigit())
    if not sc:
        return None
    own = [float(r["score"]) for r in rows if r.get("teamName") == "NeelSiri"]
    return {"n": len(sc), **{f"#{i}": sc[i - 1] for i in (1, 3, 10, 20, 30, 50, 100) if len(sc) >= i},
            "own": own[0] if own else None, "teams_ahead_of_own": sum(1 for s in sc if own and s < own[0])}


def main() -> int:
    out = {}
    for tag in ("pub30", "hc2"):
        d = jl(R9 / f"decomp_v10_{tag}.json")
        if d:
            o = d["overall"]
            out[f"decomp_{tag}"] = {"n": d["n_scenarios"], "metric": o["metric"], "shares": o["shares"],
                                    "by_station": {k: {"n": v["n"], "metric": v["metric"], "shares": v["shares"]}
                                                   for k, v in d["by_station"].items()},
                                    "by_building": {k: {"n": v["n"], "metric": v["metric"], "shares": v["shares"]}
                                                    for k, v in d["by_building"].items()},
                                    "by_mode": o["by_mode"], "comfort_by_hour_share": None}
            ch = o["by_hour"]["comfort"]
            tot = sum(ch)
            out[f"decomp_{tag}"]["comfort_by_hour_share"] = [c / tot for c in ch] if tot > 0 else None
    b = jl(R9 / "bound_r9_v10.json")
    if b:
        rows = {}
        for k, v in b.items():
            a, dl = v["acct"], v["delivery"]
            if a["gas_kwh"] < 1000:
                continue
            g = a["gas_kwh"]
            rows[k] = {"inst_occ": dl["inst_excess_occ_share_of_gas"], "inst_unocc": dl["inst_excess_unocc_share_of_gas"],
                       "loop": (a["tank_heat_kwh"] + a["dissip_kwh"] + a["warmup_overbill_kwh"]) / g,
                       "rewarms": a["loop_rewarms"]}
        out["bounds_delivery_loop"] = rows
    out["lp"] = jl(R9 / "lp_summary.json")
    out["quirk"] = jl(R9 / "quirk_summary.json")
    out["screen"] = jl(R9 / "screen_summary.json")
    out["confirm"] = {p.stem: jl(p) for p in sorted(R9.glob("confirm_*.json"))}
    out["leaderboard"] = lb()
    (R9 / "summary_r9.json").write_text(json.dumps(out, indent=1, default=float))
    for k in ("decomp_pub30", "decomp_hc2"):
        if out.get(k):
            print(k, round(out[k]["metric"], 5), {c: round(v, 3) for c, v in out[k]["shares"].items()})
    if out.get("lp") and out["lp"].get("_mean"):
        print("LP mean", out["lp"]["_mean"])
    if out.get("quirk"):
        print("quirk", out["quirk"]["kaggle"], out["quirk"]["ratio_by_station"])
    print("leaderboard", out["leaderboard"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
