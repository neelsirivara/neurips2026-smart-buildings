"""Round-5 screen summary (PREREG.md part 2): paired comparison of each candidate against r5_c00_v7.

Reads results/round5/screen/<cand>/<set>/<building>/<weather>/transfer/summary.json (2,880 steps).
held-11 = r5ms (6) + r4s (4) + r5x (1); public-4 = the four public screening scenarios.
Paired bootstrap 95% CI of the mean per-scenario metric difference (5,000 resamples, seed 0).
helps = held CI < 0 and public CI not > 0; public only = public CI < 0 and held CI not > 0;
worse = either CI > 0; else n.s.

    python screen_round5.py [--steps 2880] [--ref r5_c00_v7] [--out ../results/round5/screen_summary.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from jobs_r5 import SCREEN

HERE = Path(__file__).resolve().parent
R5 = HERE.parent / "results" / "round5"
HELD = [("r5ms", k) for k in SCREEN["r5ms"]] + [("r4s", k) for k in SCREEN["r4s"]] + [("r5x", k) for k in SCREEN["r5x"]]
PUB = [("pub30", k) for k in SCREEN["pub30"]]


def load(cand: str, keys, steps: int, kind: str = "screen") -> dict:
    out = {}
    for set_name, k in keys:
        b, w = k.split("/")
        f = R5 / kind / cand / set_name / b / w / "transfer" / "summary.json"
        if f.exists():
            s = json.loads(f.read_text())
            if s.get("total_steps") == steps:
                out[f"{set_name}:{k}"] = abs(s["total_reward"]) / steps
    return out


def paired(a: dict, b: dict, n_boot: int = 5000) -> dict | None:
    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    d = np.array([a[k] - b[k] for k in keys])
    rng = np.random.default_rng(0)
    boots = d[rng.integers(0, len(keys), size=(n_boot, len(keys)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    ref_mean = float(np.mean([b[k] for k in keys]))
    return {"n": len(keys), "cand": float(np.mean([a[k] for k in keys])), "ref": ref_mean,
            "diff": float(d.mean()), "ci_lo": float(lo), "ci_hi": float(hi), "rel": float(d.mean() / ref_mean),
            "wins": int((d < 0).sum()), "losses": int((d > 0).sum()),
            "per_scenario": {k: {"cand": a[k], "ref": b[k]} for k in keys}}


def classify(pub: dict | None, held: dict | None) -> str:
    if pub is None or held is None:
        return "incomplete"
    if pub["ci_lo"] > 0 or held["ci_lo"] > 0:
        return "worse"
    if held["ci_hi"] < 0 and pub["ci_lo"] <= 0:
        return "helps"
    if pub["ci_hi"] < 0 and held["ci_lo"] <= 0:
        return "public only"
    return "n.s."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=2880)
    ap.add_argument("--ref", default="r5_c00_v7")
    ap.add_argument("--kind", default="screen")
    ap.add_argument("--out", default=str(R5 / "screen_summary.json"))
    a = ap.parse_args()
    cands = sorted(p.name for p in (R5 / a.kind).iterdir() if p.is_dir())
    ref_h, ref_p = load(a.ref, HELD, a.steps, a.kind), load(a.ref, PUB, a.steps, a.kind)
    res = {"ref": a.ref, "steps": a.steps, "n_held": len(ref_h), "n_pub": len(ref_p),
           "ref_held_metric": float(np.mean(list(ref_h.values()))) if ref_h else None,
           "ref_pub_metric": float(np.mean(list(ref_p.values()))) if ref_p else None, "candidates": {}}
    print(f"ref {a.ref}: held-11 n={len(ref_h)} {res['ref_held_metric']}, public-4 n={len(ref_p)} {res['ref_pub_metric']}")
    print(f"{'candidate':22s} {'held-11 diff x1e-5 [CI]':>34s} {'wins':>6s} {'public-4 diff x1e-5 [CI]':>34s}  verdict")
    for c in cands:
        if c == a.ref:
            continue
        h = paired(load(c, HELD, a.steps, a.kind), ref_h)
        p = paired(load(c, PUB, a.steps, a.kind), ref_p)
        v = classify(p, h)
        if h and h["n"] < len(HELD) or p and p["n"] < len(PUB):
            v = "incomplete"
        res["candidates"][c] = {"held": h, "public": p, "verdict": v}
        fmt = lambda r: f"{r['diff']*1e5:+7.1f} [{r['ci_lo']*1e5:+7.1f}, {r['ci_hi']*1e5:+7.1f}] ({100*r['rel']:+.1f}%)" if r else "-"  # noqa: E731
        print(f"{c:22s} {fmt(h):>34s} {(str(h['wins'])+'/'+str(h['n'])) if h else '-':>6s} {fmt(p):>34s}  {v}")
    Path(a.out).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
