"""Round-4 full-length comparison (8,640 steps): candidate vs the shipped v6, paired bootstrap CIs.

Reference v6 per set:
    pub30, old40   round-3 Mac runs of the shipped v6 (results/mac/round3/final_v6_{public,heldout,r3});
                   valid because r4_c00_v6 (v7 code, no overrides) reproduces v6 bit for bit
    fresh40        round-4 run of r4_c00_v6 (results/[mac/]round4/full/r4_c00_v6/fresh40)
Candidate: results/[mac/]round4/full/<cand>/<set>.

Subsets: old34 = old40 minus the 6 round-3/round-4 screening scenarios; pooled74 = old34 + fresh40;
fresh_shipped20 / fresh_default20 = the fresh buildings in the shipped six's / the kit's default ranges.
Ship rule (PREREG.md): public not worse (CI not entirely above 0), pooled74 better (CI entirely below 0),
neither old34 nor fresh40 worse.

    python confirm_round4.py --cand r4_cXX [--out ../results/round4/confirm_<cand>.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from screen_round4 import HELD6, _set

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
STEPS = 8640
SHIPPED_FRESH = ("building_0601", "building_0602", "building_0603", "building_0606")
SCREEN6 = {s for _, s in HELD6}


def read_tree(dirs, keys):
    out = {}
    for k in keys:
        b, w = k.split("/")
        for d in dirs:
            f = d / b / w / "transfer" / "summary.json"
            if f.exists():
                s = json.loads(f.read_text())
                if s.get("total_steps") == STEPS:
                    out[k] = abs(s["total_reward"]) / STEPS
                    break
    return out


def full_dirs(cand, set_name):
    return [RES / "round4" / "full" / cand / set_name, RES / "mac" / "round4" / "full" / cand / set_name]


def ref_scores(set_name, keys):
    if set_name == "pub30":
        return read_tree([RES / "mac" / "round3" / "final_v6_public"], keys)
    if set_name == "old40":
        return read_tree([RES / "mac" / "round3" / "final_v6_heldout", RES / "mac" / "round3" / "final_v6_r3"], keys)
    return read_tree(full_dirs("r4_c00_v6", set_name), keys)


def paired(a, b, keys, n_boot=5000):
    A = np.array([a[k] for k in keys])
    B = np.array([b[k] for k in keys])
    d = A - B
    rng = np.random.default_rng(0)
    boots = d[rng.integers(0, len(keys), size=(n_boot, len(keys)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": len(keys), "cand": float(A.mean()), "v6": float(B.mean()), "diff": float(d.mean()),
            "rel": float(d.mean() / B.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "rel_ci_lo": float(lo / B.mean()), "rel_ci_hi": float(hi / B.mean()),
            "wins": int((d < 0).sum()), "losses": int((d > 0).sum()),
            "per_scenario": {k: {"cand": a[k], "v6": b[k]} for k in keys}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = {"cand": a.cand, "steps": STEPS, "sets": {}}
    data = {}
    for set_name in ("pub30", "old40", "fresh40"):
        keys = [s for _, s in _set(set_name)]
        c = read_tree(full_dirs(a.cand, set_name), keys)
        r = ref_scores(set_name, keys)
        data[set_name] = (c, r)
        kk = sorted(set(c) & set(r))
        res["sets"][set_name] = paired(c, r, kk) if kk else {"n": 0}
        res["sets"][set_name]["n_cand"], res["sets"][set_name]["n_ref"] = len(c), len(r)
    c_old, r_old = data["old40"]
    c_fr, r_fr = data["fresh40"]
    subsets = {
        "old34": (c_old, r_old, [k for k in c_old if k in r_old and k not in SCREEN6]),
        "old_screen6": (c_old, r_old, [k for k in c_old if k in r_old and k in SCREEN6]),
        "fresh_shipped20": (c_fr, r_fr, [k for k in c_fr if k in r_fr and k.split("/")[0] in SHIPPED_FRESH]),
        "fresh_default20": (c_fr, r_fr, [k for k in c_fr if k in r_fr and k.split("/")[0] not in SHIPPED_FRESH]),
    }
    for name, (c, r, kk) in subsets.items():
        res["sets"][name] = paired(c, r, sorted(kk)) if kk else {"n": 0}
    pc = {**{k: c_old[k] for k in subsets["old34"][2]}, **{k: c_fr[k] for k in c_fr if k in r_fr}}
    pr = {**{k: r_old[k] for k in subsets["old34"][2]}, **{k: r_fr[k] for k in c_fr if k in r_fr}}
    res["sets"]["pooled74"] = paired(pc, pr, sorted(pc)) if pc else {"n": 0}
    S = res["sets"]
    complete = S["pub30"]["n"] == 30 and S["old40"]["n"] == 40 and S["fresh40"]["n"] == 40
    if complete:
        ok = (S["pub30"]["ci_lo"] <= 0 and S["pooled74"]["ci_hi"] < 0 and S["old34"]["ci_lo"] <= 0 and S["fresh40"]["ci_lo"] <= 0)
        res["ship_rule_met"] = bool(ok)
    else:
        res["ship_rule_met"] = None
    res["complete"] = complete
    for name in ("pub30", "old40", "old34", "old_screen6", "fresh40", "fresh_shipped20", "fresh_default20", "pooled74"):
        s = S[name]
        if s.get("n"):
            print(f"{name:<16} n={s['n']:>2} cand={s['cand']:.5f} v6={s['v6']:.5f} diff={s['diff']:+.6f} "
                  f"[{s['ci_lo']:+.6f},{s['ci_hi']:+.6f}] ({100 * s['rel']:+.1f}%, CI {100 * s['rel_ci_lo']:+.1f}..{100 * s['rel_ci_hi']:+.1f}%) "
                  f"wins {s['wins']}/{s['n']}")
        else:
            print(f"{name:<16} n=0")
    print("complete:", complete, "ship rule met:", res["ship_rule_met"])
    out = Path(a.out) if a.out else RES / "round4" / f"confirm_{a.cand}.json"
    out.write_text(json.dumps(res, indent=1))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
