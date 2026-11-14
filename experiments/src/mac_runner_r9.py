"""Round-9 Mac job runner (stdlib only): at most 4 simulator workers, OMP_NUM_THREADS=1, GPU_LOCK-aware.

Reads a job file (JSON list of {"id", "argv"}), runs each job as a subprocess with at most --workers at once, and
keeps one done-marker per job (<state>/<id>.done, holding the return code) so a restart skips finished units.

COMPUTE_POLICY (2026-10-29/31): simulator workers run only while ~/neurips/GPU_LOCK does not exist. The runner checks
the lock before every launch and every 10 s; while the lock exists it launches nothing and SIGSTOPs its own running
workers (SIGCONT when the lock is gone), so no simulator process of ours computes beside a GPU job. It also pauses
launches while `memory_pressure` reports < 30% free. It never signals any process it did not start.

Usage (on the Mac):
    nohup ~/neurips/sb/kit/.venv/bin/python src/mac_runner_r9.py --jobs jobs/<name>.json --state state/<name> \
        --workers 4 > ~/neurips/logs/r9_<name>.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

LOCK = Path.home() / "neurips" / "GPU_LOCK"


def mem_free_pct() -> int:
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=20).stdout
        for line in out.splitlines():
            if "free percentage" in line:
                return int(line.rsplit(":", 1)[1].strip().rstrip("%"))
    except Exception:  # noqa: BLE001
        pass
    return 100


def log(msg: str) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    workers = min(max(1, a.workers), 4)
    jobs = json.loads(Path(a.jobs).read_text())
    state = Path(a.state)
    state.mkdir(parents=True, exist_ok=True)
    todo = [j for j in jobs if not (state / f"{j['id']}.done").exists()]
    log(f"runner start: {len(jobs)} jobs, {len(todo)} to do, workers {workers}, pid {os.getpid()}")
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    # the laptop / Kaggle kit copy (r6 tarball); ~/neurips/sb/kit is an older clone and must not be used
    env.setdefault("SB_KIT_DIR", str(Path.home() / "neurips" / "sb" / "r6" / "sb" / "kit"))
    if not (Path(env["SB_KIT_DIR"]) / "smart_buildings" / "heldout_scenarios_r7hc").exists():
        raise SystemExit(f"SB_KIT_DIR {env['SB_KIT_DIR']} lacks the round-7 sets")
    running: dict[str, tuple[subprocess.Popen, object]] = {}
    tries: dict[str, int] = {}
    by_id = {j["id"]: j for j in jobs}
    paused = False
    last_mem = 0.0
    mem_ok = True
    while todo or running:
        locked = LOCK.exists()
        if locked and not paused and running:
            for jid, (p, _) in running.items():
                try:
                    os.kill(p.pid, signal.SIGSTOP)
                except ProcessLookupError:
                    pass
            paused = True
            log(f"GPU_LOCK present: paused {len(running)} workers")
        elif not locked and paused:
            for jid, (p, _) in running.items():
                try:
                    os.kill(p.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
            paused = False
            log("GPU_LOCK gone: resumed workers")
        for jid in list(running):
            p, fh = running[jid]
            rc = p.poll()
            if rc is not None:
                fh.close()
                del running[jid]
                if rc != 0 and tries.get(jid, 0) < 2:
                    tries[jid] = tries.get(jid, 0) + 1
                    todo.append(by_id[jid])
                    log(f"FAILED {jid} rc={rc}; requeued (try {tries[jid]})")
                    continue
                (state / f"{jid}.done").write_text(str(rc))
                log(f"done {jid} rc={rc} ({len(todo)} queued, {len(running)} running)")
        if time.time() - last_mem > 60:
            mem_ok = mem_free_pct() >= 30
            last_mem = time.time()
        if not locked and mem_ok:
            while todo and len(running) < workers:
                j = todo.pop(0)
                fh = open(state / f"{j['id']}.log", "w")
                p = subprocess.Popen(j["argv"], stdout=fh, stderr=subprocess.STDOUT, env={**env, **j.get("env", {})},
                                     cwd=j.get("cwd") or None)
                running[j["id"]] = (p, fh)
                log(f"start {j['id']} pid={p.pid}")
        time.sleep(10)
    log("runner finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
