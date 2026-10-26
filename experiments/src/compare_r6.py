"""Round 6: Kaggle-match analysis of the harsh sets, candidate screen and full-length confirmation (PREREG round 6).

Metric per scenario: |total reward| / 8,640 (leaderboard units). Paired bootstrap of the mean per-scenario difference
(candidate - v8), 5,000 resamples, seed 0, 95% percentile CI. Trees:
  results/round6/runs/<variant>/<set>/<building>/<weather>/<policy>/summary.json      (Kaggle kernels)
  results/round5/full/r5_c12_comp/{pub30,r5m,r4c}/...                                 (laptop, v8 = r5_c12_comp)
  results/final_r4 (v7 pub30), results/round5/full/{v7,v7diag,v6,v5,pid_water}/r5m, results/[mac/]round3|4 (P, probes)

    python compare_r6.py match                 -> results/round6/set_match.json
    python compare_r6.py screen --cands r6_c01 r6_c02 ...   -> results/round6/screen_summary.json
    python compare_r6.py confirm --cand r6_cXX              -> results/round6/confirm_<cand>.json
    python compare_r6.py repro                 -> results/round6/kaggle_repro.json (Kaggle vs laptop, same policy/scenario)
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
R6 = RES / "round6"
RUNS = R6 / "runs"
STEPS = 8640
KAGGLE = {"v8": 0.01074, "v7": 0.01088, "v6": 0.01116, "v5": 0.01161, "pid_water": 0.06404}
FD_B = ("building_0604", "building_0607", "building_0610", "building_0639")
PUB12 = ["building_train_1/fairbanks_1", "building_train_2/fairbanks_2", "building_train_4/fairbanks_4",
         "building_train_5/fairbanks_5", "building_train_7/fairbanks_7", "building_train_8/fairbanks_8",
         "building_train_1/denver_7", "building_train_2/denver_8", "building_train_7/atlanta_8",
         "building_train_8/atlanta_1", "building_train_1/phoenix_5", "building_train_7/singapore_6"]


def tree(dirs, policy: str = "*") -> dict[str, float]:
    out = {}
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for f in sorted(d.glob(f"building*/*/{policy}/summary.json")):
            k = f"{f.parts[-4]}/{f.parts[-3]}"
            if k in out:
                continue
            s = json.loads(f.read_text())
            if s.get("total_steps") == STEPS:
                out[k] = abs(s["total_reward"]) / STEPS
    return out


def sync_comp() -> int:
    """Round-6 resume: the composite's runs were started speculatively under the name r6_compspec (identical parameters
    to the r6_comp.json that `decide --stage composite` wrote; PREREG resume notes). Mirror them into runs/r6_comp."""
    import filecmp
    import shutil
    src, dst = RUNS / "r6_compspec", RUNS / "r6_comp"
    a, b = HERE / "policy_candidates" / "r6_compspec.json", HERE / "policy_candidates" / "r6_comp.json"
    if not src.exists() or not b.exists() or json.loads(a.read_text()) != json.loads(b.read_text()):
        return 0
    n = 0
    for f in src.rglob("*"):
        if f.is_file():
            g = dst / f.relative_to(src)
            if not g.exists() or not filecmp.cmp(f, g, shallow=False):
                g.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, g)
                n += 1
    return n


def runs(variant: str, set_name: str) -> dict[str, float]:
    if variant == "r6_comp":
        sync_comp()
    return tree([RUNS / variant / set_name])


def ref_v8(set_name: str) -> dict[str, float]:
    """v8 reference per set; Kaggle runs first, laptop round-5 runs (r5_c12_comp) fill in."""
    k = runs("v8", set_name)
    lap = {"pub30": R5 / "full" / "r5_c12_comp" / "pub30", "r5m": R5 / "full" / "r5_c12_comp" / "r5m",
           "r4c": R5 / "full" / "r5_c12_comp" / "r4c"}.get(set_name)
    if lap is not None:
        for kk, v in tree([lap]).items():
            k.setdefault(kk, v)
    if set_name == "r4c":
        k = {kk: v for kk, v in k.items() if kk.split("/")[0] in FD_B}
    return k


def paired(ref: dict, cand: dict, n_boot: int = 5000, seed: int = 0, keys=None) -> dict | None:
    keys = sorted((set(ref) & set(cand)) if keys is None else (set(keys) & set(ref) & set(cand)))
    if not keys:
        return None
    A, B = np.array([cand[k] for k in keys]), np.array([ref[k] for k in keys])
    d = A - B
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, len(keys), size=(n_boot, len(keys)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": len(keys), "cand": float(A.mean()), "ref": float(B.mean()), "diff": float(d.mean()),
            "rel": float(d.mean() / B.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
            "rel_ci_lo": float(lo / B.mean()), "rel_ci_hi": float(hi / B.mean()),
            "wins": int((d < 0).sum()), "losses": int((d > 0).sum()),
            "worst": max(keys, key=lambda k: cand[k] / ref[k] - 1.0),
            "worst_rel": float(max(cand[k] / ref[k] - 1.0 for k in keys)),
            "per_scenario": {k: {"cand": cand[k], "ref": ref[k]} for k in keys}}


def fmt(r: dict | None) -> str:
    if not r:
        return "n/a"
    return (f"n={r['n']:2d} {r['ref']:.5f} -> {r['cand']:.5f}  {100 * r['rel']:+.2f}% "
            f"[{100 * r['rel_ci_lo']:+.2f}, {100 * r['rel_ci_hi']:+.2f}]  wins {r['wins']}/{r['n']}")


# ----------------------------------------------------------------------------------------------- match
def probe_trees() -> dict[str, dict[str, dict[str, float]]]:
    """policy -> set -> scenario -> metric, for every set with runs."""
    P = {}
    P["v8"] = {"P": ref_v8("pub30"), "M": ref_v8("r5m"), "HC": runs("v8", "r6hc"), "HS": runs("v8", "r6hs")}
    P["v7"] = {"P": tree([RES / "final_r4"], "transfer"),
               "M": tree([R5 / "full" / "v7" / "r5m", R5 / "full" / "v7diag" / "r5m"]),
               "HC": runs("v7", "r6hc"), "HS": runs("v7", "r6hs")}
    P["v6"] = {"P": tree([RES / "final"], "transfer"), "M": tree([R5 / "full" / "v6" / "r5m"]),
               "HC": runs("v6", "r6hc"), "HS": runs("v6", "r6hs")}
    P["v5"] = {"P": tree([RES / "final"], "transfer_v5"),
               "M": tree([R5 / "full" / "v5" / "r5m"]), "HC": runs("v5", "r6hc"), "HS": runs("v5", "r6hs")}
    P["pid_water"] = {"P": tree([RES / "final"], "pid_water"),
                      "M": tree([R5 / "full" / "pid_water" / "r5m"]),
                      "HC": runs("pid_water", "r6hc"), "HS": runs("pid_water", "r6hs")}
    for p in P:
        P[p]["P+M"] = {**P[p]["P"], **P[p]["M"]}
        P[p]["H"] = {**P[p]["HC"], **P[p]["HS"]}
        P[p]["P+HC"] = {**P[p]["P"], **P[p]["HC"]}
        P[p]["P+H"] = {**P[p]["P"], **P[p]["H"]}
        P[p]["P+M+H"] = {**P[p]["P"], **P[p]["M"], **P[p]["H"]}
    return P


def match() -> dict:
    P = probe_trees()
    sets = ["P", "M", "P+M", "HC", "HS", "H", "P+HC", "P+H", "P+M+H"]
    out = {"kaggle": KAGGLE, "kaggle_ratio_vs_v8": {p: KAGGLE[p] / KAGGLE["v8"] for p in KAGGLE}, "sets": {}}
    for s in sets:
        v8 = P["v8"][s]
        if not v8:
            continue
        row = {"n_v8": len(v8), "L_v8": float(np.mean(list(v8.values()))),
               "level": float(np.mean(list(v8.values())) / KAGGLE["v8"]), "ratios": {}}
        errs = []
        for p in ("v7", "v6", "v5", "pid_water"):
            t = P[p][s]
            keys = sorted(set(t) & set(v8))
            if len(keys) < 3:
                continue
            r = float(np.mean([t[k] for k in keys]) / np.mean([v8[k] for k in keys]))
            rk = KAGGLE[p] / KAGGLE["v8"]
            row["ratios"][p] = {"n": len(keys), "set": r, "kaggle": rk, "abs_log_err": abs(math.log(r) - math.log(rk))}
            errs.append(abs(math.log(r) - math.log(rk)))
        row["shape_err"] = float(np.mean(errs)) if errs else None
        row["shape_policies"] = sorted(row["ratios"])
        out["sets"][s] = row
    # mixture of public-like and harsh stations reproducing the Kaggle level
    LP, LH = out["sets"].get("P", {}).get("L_v8"), out["sets"].get("HC", {}).get("L_v8")
    if LP and LH and P["pid_water"]["HC"] and P["pid_water"]["P"]:
        w = (KAGGLE["v8"] - LP) / (LH - LP)
        # pid_water level on each part = its ratio to v8 on the shared scenarios x v8's level on the whole part
        # (pid_water may cover only part of HC)
        rP = out["sets"]["P"]["ratios"]["pid_water"]["set"]
        rH = out["sets"]["HC"]["ratios"].get("pid_water", {}).get("set")
        if rH is not None:
            mix_pid = w * rH * LH + (1 - w) * rP * LP
            out["mixture_P_HC"] = {"w_HC": float(w), "implied_pid_over_v8": float(mix_pid / KAGGLE["v8"]),
                                   "kaggle_pid_over_v8": KAGGLE["pid_water"] / KAGGLE["v8"],
                                   "pid_n_HC": out["sets"]["HC"]["ratios"]["pid_water"]["n"]}
    # per-station level of v8 (station = weather name before the last underscore)
    st = {}
    for s in ("P", "M", "HC", "HS"):
        for k, v in P["v8"][s].items():
            name = k.split("/")[1].rsplit("_", 1)[0]
            tag = name + ("_cold" if k.split("/")[1].rsplit("_", 1)[1].startswith("c") else "")
            st.setdefault(tag, []).append(v)
    out["v8_by_station"] = {k: {"n": len(v), "mean": float(np.mean(v))} for k, v in sorted(st.items())}
    (R6 / "set_match.json").write_text(json.dumps(out, indent=1))
    print(f"{'set':7s} {'n':>3s} {'L(v8)':>8s} {'level':>6s} {'shape':>6s}  ratios (set/kaggle)")
    for s, r in out["sets"].items():
        rat = " ".join(f"{p} {v['set']:.3f}/{v['kaggle']:.3f}(n{v['n']})" for p, v in r["ratios"].items())
        se = f"{r['shape_err']:.3f}" if r["shape_err"] is not None else "  -  "
        print(f"{s:7s} {r['n_v8']:3d} {r['L_v8']:.5f} {r['level']:6.3f} {se:>6s}  {rat}")
    if "mixture_P_HC" in out:
        print("mixture:", out["mixture_P_HC"])
    print("v8 by station:", {k: round(v["mean"], 5) for k, v in out["v8_by_station"].items()})
    return out


# ----------------------------------------------------------------------------------------------- screen
def classify(hs: dict | None, pub: dict | None) -> str:
    if not hs or not pub:
        return "incomplete"
    if hs["ci_lo"] > 0 or pub["ci_lo"] > 0:
        return "worse"
    if hs["ci_hi"] < 0 and pub["ci_lo"] <= 0:
        return "helps"
    if pub["ci_hi"] < 0:
        return "public only"
    return "n.s."


def screen(cands: list[str]) -> dict:
    ref_hs, ref_pub = runs("v8", "r6hs"), ref_v8("pub30")
    out = {"ref": "v8", "sets": {"HS": "r6hs (18)", "pub12": PUB12}, "cands": {}}
    for c in cands:
        hs = paired(ref_hs, runs(c, "r6hs"))
        pub = paired(ref_pub, runs(c, "pub30"), keys=PUB12)
        out["cands"][c] = {"HS": hs, "pub12": pub, "class": classify(hs, pub)}
        print(f"{c:22s} HS {fmt(hs)}\n{'':22s} P12 {fmt(pub)}   -> {out['cands'][c]['class']}")
    (R6 / "screen_summary.json").write_text(json.dumps(out, indent=1))
    return out


FAMILIES = {"boost": ["r6_c01_boost8", "r6_c02_boost4", "r6_c11_boost8cold"],
            "burst": ["r6_c03_sync08", "r6_c09_bfloor2"],
            "recovery": ["r6_c06_mpre05", "r6_c07_safe115"],
            "depth": ["r6_c08_night10"]}
NOT_ELIGIBLE = ["r6_c10_frost5"]


def decide(stage: str) -> dict:
    """PREREG part 2: composite = every 'helps' single, at most one per family (lower HS metric); C* = lowest HS
    metric among the composite and the helping singles, if classified helps."""
    sc = json.loads((R6 / "screen_summary.json").read_text())["cands"]
    out = {"utc": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "stage": stage,
           "classes": {k: v["class"] for k, v in sc.items()}}
    members, params = {}, {}
    for fam, cs in FAMILIES.items():
        helps = [c for c in cs if sc.get(c, {}).get("class") == "helps"]
        if helps:
            best = min(helps, key=lambda c: sc[c]["HS"]["cand"])
            members[fam] = best
            params.update(json.loads((HERE / "policy_candidates" / f"{best}.json").read_text()))
    out["composite_members"] = members
    out["composite_params"] = params
    if stage == "composite":
        (HERE / "policy_candidates" / "r6_comp.json").write_text(json.dumps(params, indent=1))
    else:
        pool = {c: sc[c]["HS"]["cand"] for c in sc if sc[c]["class"] == "helps" and c not in NOT_ELIGIBLE}
        if "r6_comp" in sc and sc["r6_comp"]["class"] == "helps":
            pool["r6_comp"] = sc["r6_comp"]["HS"]["cand"]
        out["pool_hs_metric"] = pool
        out["chosen"] = min(pool, key=pool.get) if pool else None
    (R6 / ("decision.json" if stage == "final" else "decision_composite.json")).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


# ----------------------------------------------------------------------------------------------- confirm
def confirm(cand: str) -> dict:
    sets = {
        "pub30": (ref_v8("pub30"), runs(cand, "pub30")),
        "HC": (runs("v8", "r6hc"), runs(cand, "r6hc")),
        "HS": (runs("v8", "r6hs"), runs(cand, "r6hs")),
        "M": (ref_v8("r5m"), runs(cand, "r5m")),
        "FD": (ref_v8("r4c"), {k: v for k, v in runs(cand, "r4c").items() if k.split("/")[0] in FD_B}),
    }
    sets["H"] = ({**sets["HC"][0], **sets["HS"][0]}, {**sets["HC"][1], **sets["HS"][1]})
    sets["P+M"] = ({**sets["pub30"][0], **sets["M"][0]}, {**sets["pub30"][1], **sets["M"][1]})
    res = {"cand": cand, "steps": STEPS, "sets": {}}
    for s, (r, c) in sets.items():
        res["sets"][s] = paired(r, c)
        print(f"{s:6s} {fmt(res['sets'][s])}")
    p, h = res["sets"]["pub30"], res["sets"]["HC"]
    if p and h and p["n"] == 30 and h["n"] == 48:
        res["rule"] = {"public_not_worse": p["ci_lo"] <= 0, "hc_better": h["ci_hi"] < 0}
        res["rule"]["met"] = res["rule"]["public_not_worse"] and res["rule"]["hc_better"]
        seeds = {}
        for s in ("pub30", "HC", "H", "P+M", "M", "FD"):
            r, c = sets[s]
            if not res["sets"].get(s):
                continue
            seeds[s] = [(lambda q: [q["ci_lo"], q["ci_hi"]])(paired(r, c, seed=sd)) for sd in range(10)]
        res["seed_ci"] = seeds
        print("rule:", res["rule"])
    else:
        res["rule"] = {"met": None, "note": "incomplete sets"}
        print("incomplete:", {s: (v["n"] if v else 0) for s, v in res["sets"].items()})
    (R6 / f"confirm_{cand}.json").write_text(json.dumps(res, indent=1))
    return res


# ----------------------------------------------------------------------------------------------- repro
def repro() -> dict:
    pairs = {
        "v8/pub30": (RUNS / "v8" / "pub30", R5 / "full" / "r5_c12_comp" / "pub30"),
        "v8code/pub30": (RUNS / "v8code" / "pub30", R5 / "full" / "r5_c12_comp" / "pub30"),
        "v7/r5m": (RUNS / "v7" / "r5m", R5 / "full" / "v7" / "r5m"),
    }
    out = {}
    for tag, (kd, ld) in pairs.items():
        for f in sorted(Path(kd).glob("building*/*/*/summary.json")):
            lf = Path(ld) / f.relative_to(kd)
            if not lf.exists():
                continue
            a, b = json.loads(f.read_text()), json.loads(lf.read_text())
            if a["total_steps"] != b["total_steps"]:
                continue
            out[f"{tag}/{f.parts[-4]}/{f.parts[-3]}"] = {
                "kaggle_total": a["total_reward"], "laptop_total": b["total_reward"],
                "rel_diff": (a["total_reward"] - b["total_reward"]) / abs(b["total_reward"]),
                "identical": a["total_reward"] == b["total_reward"],
                "kaggle_sec_per_step": a["seconds_per_step"], "laptop_sec_per_step": b["seconds_per_step"]}
    (R6 / "kaggle_repro.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(f"{k:55s} {v['kaggle_total']:.6f} {v['laptop_total']:.6f} {100 * v['rel_diff']:+.6f}% "
              f"{'identical' if v['identical'] else ''} {v['kaggle_sec_per_step']:.3f}s/step")
    if out:
        print("max |rel diff|:", max(abs(v["rel_diff"]) for v in out.values()), "n =", len(out))
    # Mac (Apple M5 Pro, mac_shard_runner_r6.py, same kit tarball and runner) against the Kaggle or laptop run of the
    # same (variant, set, scenario): runs/macrepro/<variant>/<set>/... vs runs/<variant>/<set>/... (or the laptop's
    # round-5 v8 runs for v8/pub30)
    mac = {}
    mroot = RUNS / "macrepro"
    for f in sorted(mroot.glob("*/*/building*/*/*/summary.json")) if mroot.exists() else []:
        rel = f.relative_to(mroot)
        variant, set_name = rel.parts[0], rel.parts[1]
        ref = RUNS / rel
        src = "kaggle"
        if not ref.exists() and variant == "v8" and set_name in ("pub30", "r5m", "r4c"):
            ref = R5 / "full" / "r5_c12_comp" / Path(*rel.parts[1:])
            src = "laptop"
        if not ref.exists():
            continue
        a, b = json.loads(f.read_text()), json.loads(ref.read_text())
        if a["total_steps"] != b["total_steps"]:
            continue
        mac[f"{variant}/{set_name}/{rel.parts[2]}/{rel.parts[3]}"] = {
            "mac_total": a["total_reward"], "ref_total": b["total_reward"], "ref_machine": src,
            "rel_diff": (a["total_reward"] - b["total_reward"]) / abs(b["total_reward"]),
            "identical": a["total_reward"] == b["total_reward"],
            "mac_sec_per_step": a["seconds_per_step"], "ref_sec_per_step": b["seconds_per_step"]}
    (R6 / "mac_repro.json").write_text(json.dumps(mac, indent=1))
    for k, v in mac.items():
        print(f"mac {k:50s} {v['mac_total']:.9f} {v['ref_total']:.9f} ({v['ref_machine']}) {v['rel_diff']:+.2e} "
              f"{v['mac_sec_per_step']:.3f} vs {v['ref_sec_per_step']:.3f} s/step")
    if mac:
        print("mac max |rel diff|:", max(abs(v["rel_diff"]) for v in mac.values()), "n =", len(mac))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("match")
    s = sub.add_parser("screen")
    s.add_argument("--cands", nargs="+", default=None)
    s.add_argument("--all", action="store_true", help="every r6_* variant with screen runs (not r6_c00_v8)")
    c = sub.add_parser("confirm")
    c.add_argument("--cand", required=True)
    sub.add_parser("repro")
    d = sub.add_parser("decide")
    d.add_argument("--stage", choices=["composite", "final"], required=True)
    a = ap.parse_args()
    if a.cmd == "decide":
        decide(a.stage)
        return 0
    if a.cmd == "match":
        match()
    elif a.cmd == "screen":
        cands = a.cands or []
        if a.all:
            order = [*FAMILIES["boost"], *FAMILIES["burst"], *FAMILIES["recovery"], *FAMILIES["depth"], *NOT_ELIGIBLE]
            have = sorted(d.name for d in RUNS.iterdir() if d.name.startswith("r6_") and d.name not in ("r6_c00_v8", "r6_compspec")
                          and (d / "r6hs").exists())
            cands = [c for c in order if c in have] + [c for c in have if c not in order]
        screen(cands)
    elif a.cmd == "confirm":
        confirm(a.cand)
    elif a.cmd == "repro":
        repro()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
