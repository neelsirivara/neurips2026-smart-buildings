"""Round 10 dev table: Mac dev runs (results/round10/dev/<variant>/<b>/<w>/transfer/summary.json) against v11's
runs of the same scenarios (results/round6/runs/r9_dow/<set>/..., Kaggle, bit-identical to the Mac kit).

Per variant and scenario: loss change (%), and the components (comfort regret, energy, carbon) in per-step units.

    python dev_r10.py [--set r7hc] [--dev dev]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
W = {"productivity_weight": 0.6, "energy_weight": 0.2, "carbon_weight": 0.2}


def comp(j: dict) -> dict:
    n = j["total_steps"]
    return {"loss": -j["total_reward"] / n,
            "comfort": -0.6 * j["total_normalized_productivity_regret"] / n,
            "energy": 0.2 * j["total_normalized_energy_cost"] / n,
            "carbon": 0.2 * j["total_normalized_carbon_emission"] / n,
            "tz": j.get("avg_zone_temp")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="r7hc")
    ap.add_argument("--dev", default="dev")
    ap.add_argument("--base", default="r9_dow")
    a = ap.parse_args()
    dev = RES / "round10" / a.dev
    out = {}
    for vd in sorted(p for p in dev.iterdir() if p.is_dir()):
        rows = []
        for f in sorted(vd.glob("*/*/transfer/summary.json")):
            b, w = f.parts[-4], f.parts[-3]
            bf = RES / "round6" / "runs" / a.base / a.set / b / w / "transfer" / "summary.json"
            if not bf.exists():
                continue
            c, c0 = comp(json.loads(f.read_text())), comp(json.loads(bf.read_text()))
            d = {k: (c[k] - c0[k]) / c0["loss"] * 100 for k in ("loss", "comfort", "energy", "carbon")}
            rows.append({"scen": f"{b}/{w}", "base": c0["loss"], "new": c["loss"], **{f"d_{k}": v for k, v in d.items()},
                         "tz": c["tz"], "tz0": c0["tz"]})
        if not rows:
            continue
        mean_d = sum(r["d_loss"] for r in rows) / len(rows)
        tot = (sum(r["new"] for r in rows) / sum(r["base"] for r in rows) - 1) * 100
        out[vd.name] = {"n": len(rows), "mean_pct": mean_d, "pooled_pct": tot, "rows": rows}
        print(f"\n{vd.name}: n={len(rows)} mean {mean_d:+.2f}%  pooled {tot:+.2f}%")
        for r in rows:
            print(f"  {r['scen']:34s} {r['base']:.5f} -> {r['new']:.5f} {r['d_loss']:+6.2f}%  comfort {r['d_comfort']:+6.2f}"
                  f"  energy {r['d_energy']:+6.2f}  carbon {r['d_carbon']:+6.2f}  Tz {r['tz0']:.2f}->{r['tz']:.2f}")
    (dev / "dev_table.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
