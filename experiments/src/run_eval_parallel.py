"""Evaluate policies on many scenarios in parallel (one subprocess per scenario).

Each job shells out to run_scenario.py, which writes a score_leaderboard-
compatible summary.json and skips scenarios already done at the same step
count / parameter hash, so interrupted runs resume for free.

Usage:
    python run_eval_parallel.py --policies transfer pid_water --steps 8640 \
        --results-dir ../results/full --workers 6
    python run_eval_parallel.py --policies transfer --steps 1440 --scenarios \
        building_train_1/atlanta_2 building_train_2/denver_8 --params-json p.json

At the end it writes <results-dir>/<policy>__agg.json with per-scenario totals
and the leaderboard metric (mean over scenarios of |total/steps|).
"""
from __future__ import annotations

import argparse
import json
import os
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

ALL_SCENARIOS = [
    "building_train_1/atlanta_2", "building_train_1/denver_7", "building_train_1/fairbanks_1",
    "building_train_1/phoenix_5", "building_train_1/singapore_8",
    "building_train_2/atlanta_3", "building_train_2/denver_8", "building_train_2/fairbanks_2",
    "building_train_2/phoenix_6", "building_train_2/singapore_1",
    "building_train_4/atlanta_5", "building_train_4/denver_2", "building_train_4/fairbanks_4",
    "building_train_4/phoenix_8", "building_train_4/singapore_3",
    "building_train_5/atlanta_6", "building_train_5/denver_3", "building_train_5/fairbanks_5",
    "building_train_5/phoenix_1", "building_train_5/singapore_4",
    "building_train_7/atlanta_8", "building_train_7/denver_5", "building_train_7/fairbanks_7",
    "building_train_7/phoenix_3", "building_train_7/singapore_6",
    "building_train_8/atlanta_1", "building_train_8/denver_6", "building_train_8/fairbanks_8",
    "building_train_8/phoenix_4", "building_train_8/singapore_7",
]


def discover(scen_dir: Path) -> list[str]:
    out = []
    for b in sorted(scen_dir.iterdir()):
        if b.is_dir():
            for w in sorted(b.iterdir()):
                if (w / "config.gin").exists():
                    out.append(f"{b.name}/{w.name}")
    return out


def run_job(policy, scen, steps, results_dir, params_json, save_ts, scen_dir, policy_file, force, retries=2):
    b, w = scen.split("/")
    cmd = [str(PY), str(HERE / "run_scenario.py"), "--policy", policy, "--building", b, "--weather", w,
           "--steps", str(steps), "--results-dir", str(results_dir), "--scenarios-dir", str(scen_dir)]
    if params_json:
        cmd += ["--params-json", str(params_json)]
    if policy_file:
        cmd += ["--policy-file", str(policy_file)]
    if save_ts:
        cmd.append("--save-ts")
    if force:
        cmd.append("--force")
    t0 = time.time()
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("NUMBA_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    # The simulator's floor-plan preprocessing (cv2.connectedComponentsWithStats) has
    # thrown a transient "Unknown C++ exception" when several workers start at once;
    # a failed job is retried after a short pause before it is reported as a failure.
    for attempt in range(retries + 1):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(KIT))
        if r.returncode == 0:
            break
        if attempt < retries:
            time.sleep(15.0 * (attempt + 1))
    out_lines = [ln for ln in (r.stdout or "").splitlines() if not ln.startswith(("I0", "W0", "E0"))]
    err_lines = [ln for ln in (r.stderr or "").splitlines() if not ln.startswith(("I0", "W0"))]
    return policy, scen, r.returncode, time.time() - t0, out_lines[-1] if out_lines else "", err_lines[-8:]


def aggregate(results_dir: Path, policy: str, steps: int, scenarios: list[str]) -> dict:
    rows = {}
    for scen in scenarios:
        b, w = scen.split("/")
        f = results_dir / b / w / policy / "summary.json"
        if f.exists():
            s = json.loads(f.read_text())
            if s.get("total_steps") == steps:
                rows[scen] = s
    metric = (sum(abs(s["total_reward"]) / steps for s in rows.values()) / len(rows)) if rows else None
    agg = {
        "policy": policy, "steps": steps, "n_scenarios": len(rows), "leaderboard_metric": metric,
        "per_scenario": {k: {
            "total_reward": v["total_reward"], "score": abs(v["total_reward"]) / steps,
            "regret": v.get("total_normalized_productivity_regret"),
            "energy": v.get("total_normalized_energy_cost"),
            "carbon": v.get("total_normalized_carbon_emission"),
            "seconds_per_step": v.get("seconds_per_step"),
        } for k, v in sorted(rows.items())},
    }
    (results_dir / f"{policy}__agg.json").write_text(json.dumps(agg, indent=2))
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", nargs="+", default=["transfer"])
    ap.add_argument("--steps", type=int, default=8640)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--scenarios", nargs="*", default=None, help="building/weather keys (default: all 30)")
    ap.add_argument("--scenarios-dir", default=str(KIT / "smart_buildings" / "training_scenarios"))
    ap.add_argument("--buildings", nargs="*", default=None)
    ap.add_argument("--weathers", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--params-json", default=None)
    ap.add_argument("--policy-file", default=None)
    ap.add_argument("--save-ts", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retries", type=int, default=2, help="re-run a failed scenario this many times")
    a = ap.parse_args()

    results_dir = Path(a.results_dir)
    if not results_dir.is_absolute():
        results_dir = (HERE / a.results_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    # the worker subprocess runs with cwd=kit, so relative paths must be resolved here
    if a.params_json and not Path(a.params_json).is_absolute():
        a.params_json = str((Path.cwd() / a.params_json).resolve())
    if a.policy_file and not Path(a.policy_file).is_absolute():
        a.policy_file = str((Path.cwd() / a.policy_file).resolve())
    scen_dir = Path(a.scenarios_dir)
    if not scen_dir.is_absolute():
        scen_dir = (Path.cwd() / scen_dir).resolve()
    scenarios = a.scenarios or (discover(scen_dir) if scen_dir != KIT / "smart_buildings" / "training_scenarios" else ALL_SCENARIOS)
    if a.buildings:
        scenarios = [s for s in scenarios if s.split("/")[0] in set(a.buildings)]
    if a.weathers:
        scenarios = [s for s in scenarios if s.split("/")[1] in set(a.weathers)]
    jobs = [(p, s) for p in a.policies for s in scenarios]
    print(f"{len(jobs)} jobs ({len(a.policies)} policies x {len(scenarios)} scenarios) at {a.steps} steps, "
          f"{a.workers} workers -> {results_dir}", flush=True)
    t0 = time.time()
    done = 0
    fails = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_job, p, s, a.steps, results_dir, a.params_json, a.save_ts, scen_dir,
                          a.policy_file, a.force, a.retries) for p, s in jobs]
        for fut in as_completed(futs):
            policy, scen, rc, dt, last, err = fut.result()
            done += 1
            if rc != 0:
                fails += 1
                print(f"[{done}/{len(jobs)}] FAIL {policy} {scen} rc={rc} ({dt:.0f}s)\n   " + "\n   ".join(err), flush=True)
            else:
                print(f"[{done}/{len(jobs)}] {last} ({dt:.0f}s, elapsed {(time.time()-t0)/60:.1f} min)", flush=True)
    for p in a.policies:
        agg = aggregate(results_dir, p, a.steps, scenarios)
        m = agg["leaderboard_metric"]
        print(f"== {p}: n={agg['n_scenarios']} metric={m:.5f}" if m is not None else f"== {p}: nothing scored")
    print(f"total wall {(time.time()-t0)/60:.1f} min, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
