"""Round-3 candidate screening: v6 parameter sets against the shipped v5, on two screening sets.

    public   6 public scenarios (the same six as the v4/v5 screens)
    held     6 held-out scenarios from the generated buildings (the two large zones of
             building_0502 and four of the new buildings), where the size weakness lives

Each candidate is <policy_candidates/<name>.json> run with policy_candidates/transfer_policy_v6.py;
the reference "ref_v5" is submission/transfer_policy.py.  Runs go through run_eval_parallel.py
(resumable, per-scenario summary.json) into results/round3/screen/<name>/<set>/.

    python screen_round3.py run --set public --steps 2880 --workers 3 --candidates ref_v5 r3_c00_v6_default ...
    python screen_round3.py summarize --steps 2880        # table + results/round3/screen_summary.json
    python screen_round3.py summarize --ref r3_c00_v6_default   # variants vs the v6 default -> screen_summary_vs_<ref>.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "kit"
RES = ROOT / "experiments" / "results" / "round3" / "screen"
PY = KIT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = KIT / ".venv" / "bin" / "python"

SETS = {
    "public": [("training_scenarios", s) for s in (
        "building_train_8/fairbanks_8", "building_train_1/denver_7", "building_train_2/atlanta_3",
        "building_train_8/phoenix_4", "building_train_1/singapore_8", "building_train_5/fairbanks_5")],
    "held": [("heldout_scenarios", "building_0502/denver_1"), ("heldout_scenarios", "building_0502/fairbanks_3"),
             ("heldout_scenarios_r3", "building_0507/fairbanks_2"), ("heldout_scenarios_r3", "building_0500/phoenix_2"),
             ("heldout_scenarios_r3", "building_0509/denver_5"), ("heldout_scenarios_r3", "building_0505/singapore_4")],
}


def run(a) -> int:
    rc_all = 0
    for name in a.candidates:
        for sdir, scens in _group(SETS[a.set]):
            out = RES / name / a.set
            cmd = [str(PY), str(HERE / "run_eval_parallel.py"), "--policies", "transfer", "--steps", str(a.steps),
                   "--results-dir", str(out), "--scenarios-dir", str(KIT / "smart_buildings" / sdir),
                   "--scenarios", *scens, "--workers", str(a.workers)]
            if name != "ref_v5":
                cmd += ["--policy-file", str(HERE / "policy_candidates" / "transfer_policy_v6.py"),
                        "--params-json", str(HERE / "policy_candidates" / f"{name}.json")]
            print(f"== {name} / {a.set} / {sdir}: {len(scens)} scenarios", flush=True)
            rc = subprocess.run(cmd, cwd=str(HERE)).returncode
            rc_all |= rc
    return rc_all


def _group(items):
    by = {}
    for sdir, s in items:
        by.setdefault(sdir, []).append(s)
    return by.items()


MAC_RES = ROOT / "experiments" / "results" / "mac" / "round3" / "screen"   # fetched Mac copies


def load(name, set_name, steps):
    out = {}
    for sdir, s in SETS[set_name]:
        b, w = s.split("/")
        f = RES / name / set_name / b / w / "transfer" / "summary.json"
        if not f.exists():
            f = MAC_RES / name / set_name / b / w / "transfer" / "summary.json"
        if f.exists():
            d = json.loads(f.read_text())
            if d.get("total_steps") == steps:
                out[s] = abs(d["total_reward"]) / steps
    return out


def summarize(a) -> int:
    names = sorted({p.name for d in (RES, MAC_RES) if d.exists() for p in d.iterdir() if p.is_dir()})
    rng = np.random.default_rng(0)
    rows = []
    for name in names:
        row = {"name": name}
        for set_name in SETS:
            sc = load(name, set_name, a.steps)
            ref = load(a.ref, set_name, a.steps)
            keys = sorted(set(sc) & set(ref))
            row[set_name] = {"n": len(sc), "metric": float(np.mean(list(sc.values()))) if sc else None,
                             "per_scenario": sc}
            if keys and name != a.ref:
                A = np.array([sc[k] for k in keys]); B = np.array([ref[k] for k in keys])
                d = A - B
                idx = rng.integers(0, len(keys), size=(4000, len(keys)))
                boots = d[idx].mean(axis=1)
                row[set_name].update({"n_paired": len(keys), "ref_metric": float(B.mean()),
                                      "diff": float(d.mean()), "ratio": float(A.mean() / B.mean()),
                                      "ci_lo": float(np.percentile(boots, 2.5)), "ci_hi": float(np.percentile(boots, 97.5)),
                                      "wins": int((d < 0).sum()), "losses": int((d > 0).sum())})
        rows.append(row)

    def key(r):
        vals = [r[s]["metric"] for s in SETS if r[s]["metric"] is not None]
        return np.mean(vals) if vals else 9.0
    rows.sort(key=key)
    print(f"== round-3 screen at {a.steps} steps (lower is better; diff/ratio vs {a.ref} on the same scenarios)")
    for r in rows:
        line = f"  {r['name']:<28}"
        for s in SETS:
            d = r[s]
            if d["metric"] is None:
                line += f" | {s}: -"
                continue
            line += f" | {s}: {d['metric']:.5f} (n={d['n']})"
            if "ratio" in d:
                line += f" ratio={d['ratio']:.3f} [{d['ci_lo']:+.5f},{d['ci_hi']:+.5f}] w={d['wins']}/{d['n_paired']}"
        print(line)
    out = RES.parent / ("screen_summary.json" if a.ref == "ref_v5" else f"screen_summary_vs_{a.ref}.json")
    out.write_text(json.dumps({"steps": a.steps, "ref": a.ref, "sets": {k: [s for _, s in v] for k, v in SETS.items()}, "rows": rows}, indent=1))
    print(f"-> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", choices=list(SETS), required=True)
    r.add_argument("--steps", type=int, default=2880)
    r.add_argument("--workers", type=int, default=3)
    r.add_argument("--candidates", nargs="+", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("--steps", type=int, default=2880)
    s.add_argument("--ref", default="ref_v5", help="paired reference (default the shipped v5; r3_c00_v6_default for v6 variants)")
    a = ap.parse_args()
    return run(a) if a.cmd == "run" else summarize(a)


if __name__ == "__main__":
    sys.exit(main())
