"""Round-5 full-length confirmation (8,640 steps, PREREG part 2): candidate vs v7, paired bootstrap CIs.

v7 reference per set: pub30 = results/final_r4 (the shipped v7 tree); r5m = results/round5/full/v7/r5m (+ the
diag reruns in full/v7diag/r5m); old40 = results/mac/round4/full/r4_c14_comp_a/old40; r4c (fresh 40) =
results/[mac/]round4/full/r4_c14_comp_a/fresh40, split into FS (shipped ranges) and FD (default ranges).
Candidate: results/round5/full/<cand>/<set> (sets pub30, r5m, old10 + old30 = old40, r4c).
Ship rule: public-30 not worse (CI not entirely above zero) and the Kaggle-like set better (CI entirely below 0).

    python confirm_round5.py --cand r5_cXX --kaggle-like r5m [--out ../results/round5/confirm_<cand>.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
R5 = RES / "round5"
STEPS = 8640
SHIPPED_FRESH = ("building_0601", "building_0602", "building_0603", "building_0606")


def tree(dirs: list[Path]) -> dict[str, float]:
    out = {}
    for d in dirs:
        if not d.exists():
            continue
        for f in d.glob("building*/*/transfer/summary.json"):
            k = f"{f.parts[-4]}/{f.parts[-3]}"
            if k in out:
                continue
            s = json.loads(f.read_text())
            if s.get("total_steps") == STEPS:
                out[k] = abs(s["total_reward"]) / STEPS
    return out


def ref_and_cand(cand: str) -> dict[str, tuple[dict, dict]]:
    r4 = lambda c, s: [RES / "round4" / "full" / c / s, RES / "mac" / "round4" / "full" / c / s]  # noqa: E731
    c5 = lambda s: [R5 / "full" / cand / s]  # noqa: E731
    sets = {
        "pub30": (tree([RES / "final_r4"]), tree(c5("pub30"))),
        "r5m": (tree([R5 / "full" / "v7" / "r5m", R5 / "full" / "v7diag" / "r5m"]), tree(c5("r5m"))),
        "old40": (tree(r4("r4_c14_comp_a", "old40")), tree(c5("old10") + c5("old30"))),
    }
    sets["P+M"] = ({**sets["pub30"][0], **sets["r5m"][0]}, {**sets["pub30"][1], **sets["r5m"][1]})
    fr, fc = tree(r4("r4_c14_comp_a", "fresh40")), tree(c5("r4c"))
    sets["FS"] = ({k: v for k, v in fr.items() if k.split("/")[0] in SHIPPED_FRESH},
                  {k: v for k, v in fc.items() if k.split("/")[0] in SHIPPED_FRESH})
    sets["FD"] = ({k: v for k, v in fr.items() if k.split("/")[0] not in SHIPPED_FRESH},
                  {k: v for k, v in fc.items() if k.split("/")[0] not in SHIPPED_FRESH})
    return sets


def paired(ref: dict, cand: dict, n_boot: int = 5000) -> dict | None:
    keys = sorted(set(ref) & set(cand))
    if not keys:
        return None
    A, B = np.array([cand[k] for k in keys]), np.array([ref[k] for k in keys])
    d = A - B
    rng = np.random.default_rng(0)
    boots = d[rng.integers(0, len(keys), size=(n_boot, len(keys)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": len(keys), "n_ref": len(ref), "cand": float(A.mean()), "v7": float(B.mean()), "diff": float(d.mean()),
            "rel": float(d.mean() / B.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "rel_ci_lo": float(lo / B.mean()), "rel_ci_hi": float(hi / B.mean()),
            "wins": int((d < 0).sum()), "losses": int((d > 0).sum()),
            "per_scenario": {k: {"cand": cand[k], "v7": ref[k]} for k in keys}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--kaggle-like", required=True, help="set name: P+M, r5m, old40, FS, FD")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = {"cand": a.cand, "steps": STEPS, "kaggle_like": a.kaggle_like, "sets": {}}
    for name, (ref, cand) in ref_and_cand(a.cand).items():
        r = paired(ref, cand)
        if r:
            res["sets"][name] = r
            print(f"{name:6s} n={r['n']:2d}/{r['n_ref']:2d} v7={r['v7']:.5f} cand={r['cand']:.5f} "
                  f"diff={r['diff']*1e5:+.1f}e-5 [{r['ci_lo']*1e5:+.1f}, {r['ci_hi']*1e5:+.1f}] "
                  f"({100*r['rel']:+.2f}%) wins {r['wins']}/{r['n']}")
    # --kaggle-like may name several sets (comma-separated); all of them must be better (PREREG note 18:12)
    pub = res["sets"].get("pub30")
    kls = [res["sets"].get(k) for k in a.kaggle_like.split(",")]
    complete = bool(pub and pub["n"] == 30 and all(k and k["n"] == k["n_ref"] for k in kls))
    res["complete"] = complete
    res["ship_rule_met"] = bool(complete and pub["ci_lo"] <= 0 and all(k["ci_hi"] < 0 for k in kls))
    print(f"complete={complete} ship_rule_met={res['ship_rule_met']}")
    out = Path(a.out) if a.out else R5 / f"confirm_{a.cand}.json"
    out.write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
