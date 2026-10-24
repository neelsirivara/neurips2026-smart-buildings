"""Round-4 screening and confirmation runner (one global job queue, longest jobs first).

Sets (PREREG.md, results/round4/PREREG.md):
    public   public-10: the 6 public screening scenarios of rounds 2-3 + the other 4 Fairbanks scenarios
    held     held-26: the 6 held-out screening scenarios of round 3 + 20 new scenarios (heldout_scenarios_r4s)
    pub30    all 30 public scenarios                       (confirmation)
    old40    the 40 old held-out scenarios (r2 + r3)        (confirmation; 34 of them never screened)
    fresh40  heldout_scenarios_r4c, 8 new buildings x 5     (confirmation, never screened)

Candidates are policy_candidates/<name>.json run with policy_candidates/transfer_policy_v7.py.

    python screen_round4.py run --sets held --steps 2880 --workers 14 --candidates r4_c00_v6 r4_c01_fcap_floor ...
    python screen_round4.py run --sets fresh40 --steps 8640 --runner diag --workers 12 --candidates r4_c00_v6 --tag full
    python screen_round4.py summarize --steps 2880 [--ref r4_c00_v6]
Results: results/round4/<tag>/<candidate>/<set>/<building>/<weather>/transfer/summary.json (resumable).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "kit"
KS = KIT / "smart_buildings"
R4 = ROOT / "experiments" / "results" / "round4"
MAC_R4 = ROOT / "experiments" / "results" / "mac" / "round4"
sys.path.insert(0, str(HERE))
from run_eval_parallel import ALL_SCENARIOS, discover, run_job  # noqa: E402

TR, H2, H3, H4S, H4C = "training_scenarios", "heldout_scenarios", "heldout_scenarios_r3", "heldout_scenarios_r4s", "heldout_scenarios_r4c"
PUBLIC6 = ["building_train_8/fairbanks_8", "building_train_1/denver_7", "building_train_2/atlanta_3",
           "building_train_8/phoenix_4", "building_train_1/singapore_8", "building_train_5/fairbanks_5"]
FAIRBANKS4 = ["building_train_1/fairbanks_1", "building_train_2/fairbanks_2", "building_train_4/fairbanks_4",
              "building_train_7/fairbanks_7"]
HELD6 = [(H2, "building_0502/denver_1"), (H2, "building_0502/fairbanks_3"), (H3, "building_0507/fairbanks_2"),
         (H3, "building_0500/phoenix_2"), (H3, "building_0509/denver_5"), (H3, "building_0505/singapore_4")]


def _set(name):
    if name == "public":
        return [(TR, s) for s in PUBLIC6 + FAIRBANKS4]
    if name == "held":
        return HELD6 + [(H4S, s) for s in discover(KS / H4S)]
    if name == "pub30":
        return [(TR, s) for s in ALL_SCENARIOS]
    if name == "old40":
        old = [(H2, s) for s in discover(KS / H2) if not s.startswith("building_0500/")]
        return old + [(H3, s) for s in discover(KS / H3)]
    if name == "fresh40":
        return [(H4C, s) for s in discover(KS / H4C)]
    raise KeyError(name)


SET_NAMES = ("public", "held", "pub30", "old40", "fresh40")
SCREEN_HELD6_KEYS = {s for _, s in HELD6}


def cost(sdir, scen):
    f = KS / sdir / scen / "config.gin"
    return f.stat().st_size if f.exists() else 0


def run(a) -> int:
    jobs = []
    pairs = [(c, s) for c in (a.candidates or []) for s in (a.sets or [])] + [tuple(x.split(":")) for x in (a.pairs or [])]
    for name, set_name in pairs:
        for sdir, scen in _set(set_name):
            if a.only_buildings and scen.split("/")[0] not in a.only_buildings:
                continue
            if a.skip_buildings and scen.split("/")[0] in a.skip_buildings:
                continue
            jobs.append((name, set_name, sdir, scen))
    # longest first within the call, in candidate order otherwise stable
    jobs.sort(key=lambda j: cost(j[2], j[3]) if a.ascending else -cost(j[2], j[3]))
    print(f"{len(jobs)} jobs at {a.steps} steps, {a.workers} workers, runner={a.runner}, tag={a.tag}", flush=True)
    t0 = time.time()
    fails = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {}
        for name, set_name, sdir, scen in jobs:
            out = R4 / a.tag / name / set_name
            pj = HERE / "policy_candidates" / f"{name}.json"
            pf = HERE / "policy_candidates" / "transfer_policy_v7.py"
            futs[ex.submit(run_job, "transfer", scen, a.steps, out, pj, False, KS / sdir, pf, False, 2, a.runner)] = (name, set_name)
        for i, fut in enumerate(as_completed(futs), 1):
            name, set_name = futs[fut]
            _, scen, rc, dt, last, err = fut.result()
            if rc != 0:
                fails += 1
                print(f"[{i}/{len(jobs)}] FAIL {name}/{set_name} {scen} rc={rc} ({dt:.0f}s)\n   " + "\n   ".join(err), flush=True)
            else:
                print(f"[{i}/{len(jobs)}] {name}/{set_name} {last} ({dt:.0f}s, elapsed {(time.time() - t0) / 60:.1f} min)", flush=True)
    print(f"done: {len(jobs)} jobs, {fails} failures, wall {(time.time() - t0) / 60:.1f} min", flush=True)
    return 1 if fails else 0


def load(tag, name, set_name, steps):
    out = {}
    for _sdir, s in _set(set_name):
        b, w = s.split("/")
        for base in (R4, MAC_R4):
            f = base / tag / name / set_name / b / w / "transfer" / "summary.json"
            if f.exists():
                d = json.loads(f.read_text())
                if d.get("total_steps") == steps:
                    out[s] = abs(d["total_reward"]) / steps
                    break
    return out


def paired(sc, ref, keys, rng, n_boot):
    A = np.array([sc[k] for k in keys])
    B = np.array([ref[k] for k in keys])
    d = A - B
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    boots = d[idx].mean(axis=1)
    return {"n_paired": len(keys), "metric": float(A.mean()), "ref_metric": float(B.mean()), "diff": float(d.mean()),
            "ratio": float(A.mean() / B.mean()), "ci_lo": float(np.percentile(boots, 2.5)),
            "ci_hi": float(np.percentile(boots, 97.5)), "wins": int((d < 0).sum()), "losses": int((d > 0).sum())}


def classify(pub, held):
    if pub is None or held is None:
        return "incomplete"
    if pub["ci_lo"] > 0 or held["ci_lo"] > 0:
        return "worse"
    if held["ci_hi"] < 0 and pub["ci_lo"] <= 0:
        return "helps"
    if pub["ci_hi"] < 0 and held["ci_lo"] <= 0:
        return "public only"
    return "n.s."


def summarize(a) -> int:
    names = sorted({p.name for base in (R4, MAC_R4) if (base / a.tag).exists() for p in (base / a.tag).iterdir() if p.is_dir()})
    rows = []
    for name in names:
        row = {"name": name}
        for set_name in ("public", "held"):
            rng = np.random.default_rng(0)
            sc = load(a.tag, name, set_name, a.steps)
            ref = load(a.tag, a.ref, set_name, a.steps)
            keys = sorted(set(sc) & set(ref))
            row[set_name] = {"n": len(sc), "metric": float(np.mean(list(sc.values()))) if sc else None, "per_scenario": sc}
            if keys and name != a.ref:
                row[set_name].update(paired(sc, ref, keys, rng, 4000))
                # subsets of held-26: the 6 old screening scenarios and the 20 new ones
                if set_name == "held":
                    for sub, filt in (("held_old6", lambda k: k in SCREEN_HELD6_KEYS), ("held_new20", lambda k: k not in SCREEN_HELD6_KEYS)):
                        kk = [k for k in keys if filt(k)]
                        if kk:
                            row[sub] = paired(sc, ref, kk, np.random.default_rng(0), 4000)
        full = all(row[s]["n"] == len(_set(s)) for s in ("public", "held"))
        row["complete"] = full
        row["class"] = classify(row["public"] if "diff" in row["public"] else None,
                                row["held"] if "diff" in row["held"] else None) if name != a.ref else "reference"
        rows.append(row)
    rows.sort(key=lambda r: (r["held"]["metric"] if r["held"]["metric"] is not None else 9.0))
    print(f"== round-4 screen at {a.steps} steps (lower is better; diff vs {a.ref}, paired 95% CI)")
    for r in rows:
        line = f"  {r['name']:<24} {r['class']:<11}"
        for s in ("public", "held"):
            d = r[s]
            if d["metric"] is None:
                line += f" | {s}: -"
                continue
            line += f" | {s} {d['metric']:.5f} n={d['n']}"
            if "diff" in d:
                line += f" d={d['diff']:+.6f} [{d['ci_lo']:+.6f},{d['ci_hi']:+.6f}] w={d['wins']}/{d['n_paired']}"
        print(line)
    out = R4 / f"screen_summary_{a.tag}_vs_{a.ref}.json"
    out.write_text(json.dumps({"steps": a.steps, "ref": a.ref, "tag": a.tag,
                               "sets": {s: [x for _, x in _set(s)] for s in ("public", "held")}, "rows": rows}, indent=1))
    print(f"-> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sets", nargs="+", choices=SET_NAMES, default=None)
    r.add_argument("--pairs", nargs="+", default=None, help="candidate:set pairs (in addition to candidates x sets)")
    r.add_argument("--steps", type=int, default=2880)
    r.add_argument("--workers", type=int, default=3)
    r.add_argument("--runner", choices=["scenario", "diag"], default="scenario")
    r.add_argument("--tag", default="screen")
    r.add_argument("--candidates", nargs="+", default=None)
    r.add_argument("--only-buildings", nargs="+", default=None)
    r.add_argument("--skip-buildings", nargs="+", default=None)
    r.add_argument("--ascending", action="store_true", help="shortest jobs first")
    s = sub.add_parser("summarize")
    s.add_argument("--steps", type=int, default=2880)
    s.add_argument("--ref", default="r4_c00_v6")
    s.add_argument("--tag", default="screen")
    a = ap.parse_args()
    return run(a) if a.cmd == "run" else summarize(a)


if __name__ == "__main__":
    sys.exit(main())
