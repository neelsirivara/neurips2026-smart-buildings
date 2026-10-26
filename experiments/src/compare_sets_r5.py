"""Round 5, goal 1: which local scenario set predicts the Kaggle public score (PREREG.md part 1).

Collects the 8,640-step per-scenario metric |total_reward| / 8640 of v7, v6, v5 and pid_water on every local set,
and compares each set with the Kaggle public scores in results/kaggle_feedback.json ("scores_by_policy"):
    level  = L_S(v7) / K(v7)
    shape  = E_S = mean_p |ln(L_S(p)/L_S(v7)) - ln(K(p)/K(v7))| over the policies p != v7 with a Kaggle score
Also the PR #2 check (6 public Fairbanks scenarios, patched kit copy vs the unpatched runs).

    python compare_sets_r5.py [--out ../results/round5/set_comparison.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
R5 = RES / "round5"
STEPS = 8640
SHIPPED_FRESH = ("building_0601", "building_0602", "building_0603", "building_0606")
POLICIES = ("v7", "v6", "v5", "pid_water")


def scen_keys(tree: Path) -> list[str]:
    if not tree.exists():
        return []
    return sorted(f"{b.name}/{w.name}" for b in tree.iterdir() if b.is_dir() and b.name.startswith("building")
                  for w in b.iterdir() if w.is_dir())


def read(dirs: list[Path], pol_dir: str, keys: list[str]) -> dict[str, float]:
    out = {}
    for k in keys:
        b, w = k.split("/")
        for d in dirs:
            f = d / b / w / pol_dir / "summary.json"
            if f.exists():
                s = json.loads(f.read_text())
                if s.get("total_steps") == STEPS:
                    out[k] = abs(s["total_reward"]) / STEPS
                    break
    return out


def collect() -> dict[str, dict[str, dict[str, float]]]:
    sets: dict[str, dict[str, dict[str, float]]] = {}
    # P: public-30
    pk = scen_keys(RES / "final")
    sets["P"] = {"v7": read([RES / "final_r4"], "transfer", pk), "v6": read([RES / "final"], "transfer", pk),
                 "v5": read([RES / "final"], "transfer_v5", pk), "pid_water": read([RES / "final"], "pid_water", pk)}
    # O: old held-out 40 (default ranges)
    od = [RES / "final_heldout", RES / "final_heldout_r3"]
    ok = scen_keys(od[0]) + scen_keys(od[1])
    sets["O"] = {"v7": read([RES / "mac" / "round4" / "full" / "r4_c14_comp_a" / "old40"], "transfer", ok),
                 "v6": read(od, "transfer", ok), "v5": read(od, "transfer_v5", ok), "pid_water": read(od, "pid_water", ok)}
    # FS / FD: fresh 40 of round 4
    fdirs = lambda c: [RES / "round4" / "full" / c / "fresh40", RES / "mac" / "round4" / "full" / c / "fresh40"]  # noqa: E731
    fk = sorted(set(scen_keys(fdirs("r4_c14_comp_a")[0]) + scen_keys(fdirs("r4_c14_comp_a")[1])))
    fv7, fv6 = read(fdirs("r4_c14_comp_a"), "transfer", fk), read(fdirs("r4_c00_v6"), "transfer", fk)
    r5f = {p: read([R5 / "full" / p / "r4c"], "pid_water" if p == "pid_water" else "transfer", fk)
           for p in ("v5", "pid_water")}
    for name, keep in (("FS", lambda k: k.split("/")[0] in SHIPPED_FRESH),
                       ("FD", lambda k: k.split("/")[0] not in SHIPPED_FRESH)):
        sets[name] = {"v7": {k: v for k, v in fv7.items() if keep(k)}, "v6": {k: v for k, v in fv6.items() if keep(k)},
                      "v5": {k: v for k, v in r5f["v5"].items() if keep(k)},
                      "pid_water": {k: v for k, v in r5f["pid_water"].items() if keep(k)}}
    # M: shipped six x Minneapolis (round 5)
    mk = scen_keys(RES.parent.parent / "kit" / "smart_buildings" / "heldout_scenarios_r5m")
    sets["M"] = {p: read([R5 / "full" / p / "r5m"], "pid_water" if p == "pid_water" else "transfer", mk)
                 for p in POLICIES}
    # P+M
    sets["P+M"] = {p: {**sets["P"][p], **sets["M"][p]} for p in POLICIES}
    return sets


def summarize(sets, kaggle: dict[str, float]) -> dict:
    out = {}
    for name, pols in sets.items():
        row: dict = {"n": {p: len(v) for p, v in pols.items()}, "mean": {}, "ratio_to_v7_paired": {}}
        for p, v in pols.items():
            row["mean"][p] = float(np.mean(list(v.values()))) if v else None
            common = sorted(set(v) & set(pols["v7"]))
            if p != "v7" and common:
                row["ratio_to_v7_paired"][p] = {
                    "n": len(common),
                    "ratio": float(np.mean([v[k] for k in common]) / np.mean([pols["v7"][k] for k in common]))}
        if row["mean"].get("v7"):
            row["level_v7_over_kaggle"] = row["mean"]["v7"] / kaggle["v7"] if "v7" in kaggle else None
            errs = {}
            for p, r in row["ratio_to_v7_paired"].items():
                if p in kaggle:
                    errs[p] = abs(math.log(r["ratio"]) - math.log(kaggle[p] / kaggle["v7"]))
            row["shape_err_by_policy"] = errs
            row["shape_err"] = float(np.mean(list(errs.values()))) if errs else None
        out[name] = row
    return out


def by_station(pols: dict[str, dict[str, float]]) -> dict:
    st: dict[str, dict[str, list[float]]] = {}
    for p, v in pols.items():
        for k, x in v.items():
            s = k.split("/")[1].rsplit("_", 1)[0]
            st.setdefault(s, {}).setdefault(p, []).append(x)
    return {s: {p: {"n": len(xs), "mean": float(np.mean(xs))} for p, xs in d.items()} for s, d in sorted(st.items())}


def pr2_check() -> dict:
    keys = [k for k in scen_keys(RES / "final") if "fairbanks" in k]
    out = {}
    for p, pol_dir, base in (("v7", "transfer", [RES / "final_r4"]), ("pid_water", "pid_water", [RES / "final"])):
        a = read([R5 / "full" / f"{p}_pr2" / "pubfair6"], pol_dir, keys)
        b = read(base, pol_dir, keys)
        common = sorted(set(a) & set(b))
        if not common:
            continue
        out[p] = {"n": len(common), "patched": float(np.mean([a[k] for k in common])),
                  "unpatched": float(np.mean([b[k] for k in common])),
                  "rel_change": float(np.mean([a[k] for k in common]) / np.mean([b[k] for k in common]) - 1.0),
                  "per_scenario": {k: {"patched": a[k], "unpatched": b[k], "rel": a[k] / b[k] - 1.0} for k in common}}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(R5 / "set_comparison.json"))
    a = ap.parse_args()
    fb = json.loads((RES / "kaggle_feedback.json").read_text())
    kaggle = {k: v for k, v in fb.get("scores_by_policy", {}).items() if v is not None}
    sets = collect()
    res = {"kaggle_public": kaggle, "sets": summarize(sets, kaggle),
           "by_station": {n: by_station(sets[n]) for n in ("P", "M", "O")}, "pr2_check": pr2_check(),
           "per_scenario": {n: sets[n] for n in ("M",)}}
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"Kaggle public: {kaggle}")
    print(f"{'set':5s} " + " ".join(f"{p:>16s}" for p in POLICIES) + "   v7/K   shape_err")
    for n, r in res["sets"].items():
        cells = []
        for p in POLICIES:
            m = r["mean"][p]
            cells.append(f"{m:.5f} (n={r['n'][p]:2d})" if m else f"{'-':>16s}")
        lv = r.get("level_v7_over_kaggle")
        se = r.get("shape_err")
        print(f"{n:5s} " + " ".join(f"{c:>16s}" for c in cells) +
              (f"   {lv:.3f}" if lv is not None else "") + (f"   {se:.3f}" if se is not None else ""))
        for p, rr in r["ratio_to_v7_paired"].items():
            print(f"        {p}/v7 (paired n={rr['n']}): {rr['ratio']:.3f}"
                  + (f"   Kaggle {kaggle[p] / kaggle['v7']:.3f}" if p in kaggle else ""))
    if res["pr2_check"]:
        print("PR #2:", {p: (v["n"], round(v["rel_change"], 4)) for p, v in res["pr2_check"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
