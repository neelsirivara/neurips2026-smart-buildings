"""P2: parameter search for the SADR controller on a screening set of scenarios.

Two stages, both resumable (every evaluation is cached under
results/tune/<params-hash>/ with one summary.json per scenario):

  random   N random configurations from SPACE (seeded), each scored on the
           screening scenarios at --steps (default 1440 = 5 days)
  coord    coordinate descent from the best configuration found so far: for
           each parameter, try its neighbouring grid values, keep improvements

Score = leaderboard metric on the screening set: mean over scenarios of
|total_reward| / steps (lower is better). The log (tune_log.json) records
every configuration and its per-scenario totals.

Usage:
    python tune.py random --n 24 --steps 1440 --workers 4
    python tune.py coord --rounds 2 --steps 1440 --workers 4
    python tune.py best            # print the best config and write best_params.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "kit"
PY = KIT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = KIT / ".venv" / "bin" / "python"
TUNE_DIR = ROOT / "experiments" / "results" / "tune"
LOG = TUNE_DIR / "tune_log.json"
POLICY_FILE = ROOT / "submission" / "transfer_policy.py"   # overridden by --policy-file (candidate code)

# Buildings held out from tuning (transfer check): never appear in SCREEN.
HELDOUT_BUILDINGS = ("building_train_4", "building_train_7")

# Screening set: one scenario per station, drawn from the four tuning
# buildings, mixing building sizes (b8: 30 zones, b1: 39, b5: 79, b2: 85).
SCREEN = [
    "building_train_8/fairbanks_8",
    "building_train_1/denver_7",
    "building_train_2/atlanta_3",
    "building_train_8/phoenix_4",
    "building_train_1/singapore_8",
    "building_train_5/fairbanks_5",
]

# Search space: grid values per parameter (the default is always included).
SPACE: dict[str, list] = {
    "margin_occ": [0.2, 0.3, 0.5, 0.7],
    "margin_pre": [0.3, 0.5, 0.8],
    "night_low_ext": [1.0, 2.0, 4.0, 8.0],
    "night_high_ext": [1.0, 2.0, 4.0],
    "sb_hyst_k": [1.0, 1.5, 3.0],
    "q_sb_w": [2000.0, 4000.0, 8000.0],
    "lead_max_h": [5.0, 8.0],
    "kq_w_per_k": [200.0, 400.0, 800.0],
    "ki_w_per_k_step": [30.0, 60.0, 120.0],
    "sat_cool_hi": [291.0, 293.0, 295.0],
    "sat_mix_floor": [288.0, 290.0, 292.0],
    "lead_safety": [1.0, 1.3, 1.8],
    "rate0_kph": [1.5, 2.0, 3.0],
    "holiday_check_h": [6.5, 7.0, 8.0],
    "heat_season_steps": [12, 288],
    "min_on_steps": [3, 12],
    "disch_margin_k": [0.5, 1.0, 3.0],
}


def phash(params: dict) -> str:
    return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:10]


def load_log() -> dict:
    if LOG.exists():
        return json.loads(LOG.read_text())
    return {"evals": {}}


def save_log(log: dict) -> None:
    TUNE_DIR.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=1))


def run_one(params_path: Path, scen: str, steps: int, out_dir: Path) -> tuple[str, float | None, str]:
    b, w = scen.split("/")
    cmd = [str(PY), str(HERE / "run_scenario.py"), "--policy", "transfer", "--policy-file", str(POLICY_FILE),
           "--building", b, "--weather", w, "--steps", str(steps), "--results-dir", str(out_dir),
           "--params-json", str(params_path)]
    import os
    env = dict(os.environ)
    for k in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env[k] = "1"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(KIT))
    summ = out_dir / b / w / "transfer" / "summary.json"
    if r.returncode != 0 or not summ.exists():
        err = "\n".join([ln for ln in (r.stderr or "").splitlines() if not ln.startswith(("I0", "W0"))][-6:])
        return scen, None, err
    s = json.loads(summ.read_text())
    return scen, float(s["total_reward"]), ""


def evaluate(params: dict, steps: int, workers: int, log: dict, scenarios: list[str] | None = None) -> float | None:
    scenarios = scenarios or SCREEN
    h = phash(params)
    out_dir = TUNE_DIR / h
    out_dir.mkdir(parents=True, exist_ok=True)
    params_path = out_dir / "params.json"
    params_path.write_text(json.dumps(params, indent=1, sort_keys=True))
    rec = log["evals"].setdefault(h, {"params": params, "steps": steps, "totals": {}})
    if params == default_params():
        rec["is_default"] = True
    todo = [s for s in scenarios if s not in rec["totals"]]
    t0 = time.time()
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(run_one, params_path, s, steps, out_dir) for s in todo]
            for f in as_completed(futs):
                scen, tot, err = f.result()
                if tot is None:
                    print(f"   FAIL {scen}: {err}", flush=True)
                else:
                    rec["totals"][scen] = tot
        save_log(log)
    done = [s for s in scenarios if s in rec["totals"]]
    if len(done) < len(scenarios):
        return None
    score = sum(abs(rec["totals"][s]) / steps for s in scenarios) / len(scenarios)
    rec["score"] = score
    save_log(log)
    print(f"[{h}] score={score:.5f} ({time.time() - t0:.0f}s) "
          + " ".join(f"{s.split('/')[1]}={rec['totals'][s]:.0f}" for s in scenarios), flush=True)
    return score


def default_params() -> dict:
    sys.path.insert(0, str(POLICY_FILE.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("sadr_policy_for_tuning", POLICY_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.DEFAULT_PARAMS)


def full_params(overrides: dict) -> dict:
    p = default_params()
    p.update(overrides)
    return p


def best_in_log(log: dict, steps: int, scenarios: list[str]) -> tuple[str | None, float]:
    best_h, best_s = None, float("inf")
    for h, rec in log["evals"].items():
        if rec.get("steps") != steps or not all(s in rec["totals"] for s in scenarios):
            continue
        sc = sum(abs(rec["totals"][s]) / steps for s in scenarios) / len(scenarios)
        if sc < best_s:
            best_h, best_s = h, sc
    return best_h, best_s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["random", "coord", "best", "default", "eval"])
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--steps", type=int, default=1440)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--params-json", default=None, help="for 'eval': a params file to score")
    ap.add_argument("--policy-file", default=None, help="candidate policy source (default: submission/transfer_policy.py)")
    ap.add_argument("--tag", default=None, help="for 'eval': label of the candidate code, stored as params['_policy']")
    a = ap.parse_args()
    global POLICY_FILE
    if a.policy_file:
        POLICY_FILE = Path(a.policy_file).resolve()
    scenarios = a.scenarios or SCREEN
    log = load_log()

    if a.stage == "default":
        evaluate(default_params(), a.steps, a.workers, log, scenarios)
        return 0
    if a.stage == "eval":
        p = full_params(json.loads(Path(a.params_json).read_text()))
        if a.tag:
            p["_policy"] = a.tag        # part of the hash: the same numbers with other code is another eval
        evaluate(p, a.steps, a.workers, log, scenarios)
        return 0
    if a.stage == "random":
        rng = random.Random(a.seed)
        base = default_params()
        evaluate(base, a.steps, a.workers, log, scenarios)
        for i in range(a.n):
            p = dict(base)
            # perturb a random subset (2..5) of parameters
            keys = rng.sample(sorted(SPACE), k=rng.randint(2, 5))
            for k in keys:
                p[k] = rng.choice(SPACE[k])
            print(f"-- random {i + 1}/{a.n}: " + ", ".join(f"{k}={p[k]}" for k in keys), flush=True)
            evaluate(p, a.steps, a.workers, log, scenarios)
            log["evals"].setdefault(phash(p), {})["stage"] = "random"
            save_log(log)
        return 0
    if a.stage == "coord":
        h, s = best_in_log(log, a.steps, scenarios)
        if h is None:
            print("no complete evaluation in log; run 'default' or 'random' first")
            return 1
        cur = dict(log["evals"][h]["params"])
        cur_s = s
        print(f"start from [{h}] score={cur_s:.5f}")
        for r in range(a.rounds):
            improved = False
            for k in sorted(SPACE):
                vals = sorted(set(SPACE[k]))
                if cur[k] not in vals:
                    vals = sorted(set(vals + [cur[k]]))
                i = vals.index(cur[k])
                for j in (i - 1, i + 1):
                    if 0 <= j < len(vals):
                        p = dict(cur)
                        p[k] = vals[j]
                        print(f"-- round {r + 1} try {k}={vals[j]} (from {cur[k]})", flush=True)
                        sc = evaluate(p, a.steps, a.workers, log, scenarios)
                        if sc is not None and sc < cur_s - 1e-6:
                            cur, cur_s, improved = p, sc, True
                            print(f"   improved -> {cur_s:.5f}", flush=True)
            if not improved:
                break
        (TUNE_DIR / "best_params.json").write_text(json.dumps(cur, indent=1, sort_keys=True))
        print(f"best score={cur_s:.5f} -> {TUNE_DIR / 'best_params.json'}")
        return 0
    if a.stage == "best":
        h, s = best_in_log(log, a.steps, scenarios)
        if h is None:
            print("nothing complete")
            return 1
        base = default_params()
        best = log["evals"][h]["params"]
        diff = {k: v for k, v in best.items() if base.get(k) != v}
        print(f"best [{h}] score={s:.5f}; differs from defaults in: {json.dumps(diff, indent=1)}")
        (TUNE_DIR / "best_params.json").write_text(json.dumps(best, indent=1, sort_keys=True))
        ranked = sorted(
            ((sum(abs(rec["totals"][sc]) / a.steps for sc in scenarios) / len(scenarios), hh)
             for hh, rec in log["evals"].items()
             if rec.get("steps") == a.steps and all(sc in rec["totals"] for sc in scenarios)))
        for sc_, hh in ranked[:10]:
            d = {k: v for k, v in log["evals"][hh]["params"].items() if base.get(k) != v}
            print(f"  {sc_:.5f} [{hh}] {d}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
