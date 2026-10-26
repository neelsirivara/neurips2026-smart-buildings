"""Round 5 job queue: runs scenario jobs from JSON files in a queue directory with a RAM-aware worker limit.

Laptop rule (round 5): at most 3 simulator workers; before each launch the available RAM is read
(psutil): >= 1.0 GB -> up to --max-workers, 0.6-1.0 GB -> 2, < 0.6 GB -> 1 (running jobs always finish).
Jobs are read from <queue-dir>/*.json (sorted by name, re-scanned every poll, so jobs can be added while it
runs); each file holds a list of job objects:
    {"id": str, "policy": "transfer"|"pid_water"|..., "policy_file": str|null, "params_json": str|null,
     "scen_dir": str, "scenario": "building/weather", "steps": int, "results_dir": str,
     "runner": "scenario"|"diag", "kit_dir": str|null}
A job whose summary.json already exists at the same step count is skipped by run_scenario.py / run_diag.py,
so the queue is resumable. Writing <queue-dir>/STOP makes the runner exit after the running jobs finish;
with --exit-when-empty it exits once nothing is pending or running.

    python run_queue_r5.py --queue-dir ../results/round5/queue --max-workers 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / "kit"
PY = KIT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = KIT / ".venv" / "bin" / "python"


def allowed_workers(max_workers: int) -> tuple[int, float]:
    avail = psutil.virtual_memory().available / 1e9
    if avail < 0.6:
        return 1, avail
    if avail < 1.0:
        return min(2, max_workers), avail
    return max_workers, avail


def done(job: dict) -> bool:
    b, w = job["scenario"].split("/")
    f = Path(job["results_dir"]) / b / w / job["policy"] / "summary.json"
    if not f.exists():
        return False
    try:
        s = json.loads(f.read_text())
    except (OSError, ValueError):
        return False
    return s.get("total_steps") == job["steps"] or (s.get("total_steps", 0) > 0 and s.get("terminated_early"))


def command(job: dict) -> list[str]:
    b, w = job["scenario"].split("/")
    script = "run_diag.py" if job.get("runner") == "diag" else "run_scenario.py"
    cmd = [str(PY), str(HERE / script), "--policy", job["policy"], "--building", b, "--weather", w,
           "--steps", str(job["steps"]), "--results-dir", job["results_dir"], "--scenarios-dir", job["scen_dir"]]
    if job.get("params_json"):
        cmd += ["--params-json", job["params_json"]]
    if job.get("policy_file"):
        cmd += ["--policy-file", job["policy_file"]]
    return cmd


def log(path: Path, msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H%M%S ") + msg
    print(line, flush=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-dir", required=True)
    ap.add_argument("--max-workers", type=int, default=3)
    ap.add_argument("--poll", type=float, default=10.0)
    ap.add_argument("--exit-when-empty", action="store_true")
    a = ap.parse_args()
    qd = Path(a.queue_dir).resolve()
    qd.mkdir(parents=True, exist_ok=True)
    logf = qd / "queue_log.txt"
    running: dict[str, tuple[subprocess.Popen, float, dict, object]] = {}
    started: set[str] = set()
    failures: dict[str, int] = {}
    last_ram_log = 0.0
    log(logf, f"runner start pid={os.getpid()} max_workers={a.max_workers}")
    while True:
        # reap
        for jid in list(running):
            p, t0, job, fh = running[jid]
            rc = p.poll()
            if rc is None:
                continue
            fh.close()
            del running[jid]
            dt = time.time() - t0
            if rc == 0:
                tail = ""
                try:
                    lines = [ln for ln in Path(fh.name).read_text(errors="replace").splitlines()
                             if ln.strip() and not ln.startswith(("I0", "W0", "E0"))]
                    tail = lines[-1] if lines else ""
                except OSError:
                    pass
                log(logf, f"DONE {jid} ({dt/60:.1f} min) {tail}")
            else:
                failures[jid] = failures.get(jid, 0) + 1
                log(logf, f"FAIL {jid} rc={rc} ({dt/60:.1f} min) attempt {failures[jid]} log={fh.name}")
                if failures[jid] <= 2:
                    started.discard(jid)          # retry (transient cv2 start-up failures seen in round 3)
        # scan queue
        pending = []
        for qf in sorted(qd.glob("*.json")):
            try:
                jobs = json.loads(qf.read_text())
            except (OSError, ValueError):
                continue
            for job in jobs:
                if job["id"] in started or job["id"] in running:
                    continue
                if done(job):
                    started.add(job["id"])
                    continue
                pending.append(job)
        stop = (qd / "STOP").exists()
        if (stop or (a.exit_when_empty and not pending)) and not running:
            log(logf, f"runner exit (stop={stop}, pending={len(pending)})")
            return 0
        limit, avail = allowed_workers(a.max_workers)
        if time.time() - last_ram_log > 1800:
            log(logf, f"RAM available {avail:.2f} GB -> worker limit {limit}; running {len(running)}, "
                      f"pending {len(pending)}")
            last_ram_log = time.time()
        while not stop and pending and len(running) < limit:
            job = pending.pop(0)
            env = dict(os.environ)
            for k in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
                env.setdefault(k, "1")
            if job.get("kit_dir"):
                env["SB_KIT_DIR"] = job["kit_dir"]
            cwd = job.get("kit_dir") or str(KIT)
            logdir = qd / "logs"
            logdir.mkdir(exist_ok=True)
            fh = open(logdir / (job["id"].replace("/", "__") + ".log"), "w", encoding="utf-8")
            p = subprocess.Popen(command(job), stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=cwd)
            running[job["id"]] = (p, time.time(), job, fh)
            started.add(job["id"])
            log(logf, f"START {job['id']} (RAM {avail:.2f} GB, running {len(running)}/{limit})")
            time.sleep(3.0)                       # stagger start-up (cv2 preprocessing)
            limit, avail = allowed_workers(a.max_workers)
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
