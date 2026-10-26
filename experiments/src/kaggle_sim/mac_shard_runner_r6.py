"""Round 6: run Kaggle-format job files (kaggle_jobs/*.json) on the Mac, with the same kit copy and runner as the
Kaggle shards (the private dataset's tarball sb26sim.tar.gz, extracted under ~/neurips/sb/r6/x).

    ~/neurips/sb/kit/.venv/bin/python mac_shard_runner_r6.py --batch NAME --jobs a.json b.json [--workers 8]

Layout on the Mac (mirrors /tmp/sb in the Kaggle runner, so run_scenario.py resolves the same paths):
    ~/neurips/sb/r6/sb/kit/smart_buildings/...      kit code + scenario sets (from the tarball)
    ~/neurips/sb/r6/sb/experiments/src/run_*.py     runner (from the tarball)
    ~/neurips/sb/r6/policies/<file>.py              policy files, by the basename of each job's policy_path
    ~/neurips/sb/r6/out/<batch>/results/<tag>/<building>/<weather>/<policy>/summary.json, progress.jsonl, logs/
Memory guard (user request after the Mac's memory-overload crash): at most 8 workers, and before every job launch
`memory_pressure | tail -1` must report a system-wide free percentage >= 30%; otherwise no new job starts until it
does (checked every 60 s). Running jobs are never killed.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

R6 = Path.home() / "neurips" / "sb" / "r6"
SB = R6 / "sb"
KIT = SB / "kit"
RDIR = SB / "experiments" / "src"
PDIR = R6 / "policies"
MAX_WORKERS = 8
MEM_MIN = 30


def free_pct() -> int | None:
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"free percentage:\s*(\d+)%", out.strip().splitlines()[-1])
        return int(m.group(1)) if m else None
    except Exception:  # noqa: BLE001
        return None


def n_sim_running() -> int:
    """Simulator processes on the whole machine (every batch), so several runners share one cap of 8."""
    try:
        out = subprocess.run(["pgrep", "-f", r"r6/sb/experiments/src/run_(scenario|diag)\.py"], capture_output=True,
                             text=True, timeout=30).stdout
        return len([x for x in out.split() if x.strip()])
    except Exception:  # noqa: BLE001
        return 0


def wait_batch_drained(batch: str) -> None:
    """Block until the named batch's runner has started its last job (its log shows '0 pending)')."""
    lf = R6 / "out" / batch / "runner_log.txt"
    while True:
        try:
            lines = [x for x in lf.read_text().splitlines() if " start " in x or "all done" in x]
        except OSError:
            lines = []
        if lines and ("0 pending)" in lines[-1] or "all done" in lines[-1]):
            return
        time.sleep(30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--jobs", nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--after-batch", default=None, help="start only once this batch has no pending jobs")
    a = ap.parse_args()
    workers = min(a.workers, MAX_WORKERS)
    if a.after_batch:
        wait_batch_drained(a.after_batch)
    work = R6 / "out" / a.batch
    logs = work / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    def log(msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())}Z +{time.time() - t0:7.0f}s] {msg}"
        print(line, flush=True)
        with open(work / "runner_log.txt", "a") as f:
            f.write(line + "\n")

    jobs = []
    for jf in a.jobs:
        jobs += json.loads(Path(jf).read_text())
    done_ids = set()
    prog = work / "progress.jsonl"
    if prog.exists():                       # resumable: skip jobs with a finished summary
        for line in prog.read_text().splitlines():
            r = json.loads(line)
            if r.get("ok"):
                done_ids.add(r["id"])
    pending = [j for j in jobs if j["id"] not in done_ids]
    log(f"batch {a.batch}: {len(jobs)} jobs, {len(pending)} to run, {workers} workers, mem guard {MEM_MIN}%")
    running: dict[str, tuple] = {}
    done = 0
    while pending or running:
        while pending and len(running) < workers and n_sim_running() < MAX_WORKERS:
            fp = free_pct()
            if fp is not None and fp < MEM_MIN:
                log(f"memory free {fp}% < {MEM_MIN}%: holding {len(pending)} jobs ({len(running)} running)")
                break
            j = pending.pop(0)
            res = work / "results" / j["tag"]
            script = j.get("script") or "run_scenario.py"
            cmd = [sys.executable, str(RDIR / script), "--policy", j["policy"], "--building", j["building"],
                   "--weather", j["weather"], "--steps", str(j["steps"]), "--results-dir", str(res),
                   "--scenarios-dir", str(KIT / "smart_buildings" / j["set_dir"])]
            if j.get("policy_path"):
                pname = re.split(r"[\\/]", j["policy_path"])[-1]
                cmd += ["--policy-file", str(PDIR / pname)]
            if j.get("params"):
                pp = work / "params" / (j["id"].replace("/", "__") + ".params.json")
                pp.parent.mkdir(exist_ok=True)
                pp.write_text(j["params"])
                cmd += ["--params-json", str(pp)]
            if j.get("save_ts"):
                cmd.append("--save-ts")
            env = dict(os.environ)
            for k in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                      "VECLIB_MAXIMUM_THREADS"):
                env[k] = "1"
            env["SB_KIT_DIR"] = str(KIT)
            fh = open(logs / (j["id"].replace("/", "__") + ".log"), "w")
            p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=str(KIT))
            running[j["id"]] = (p, time.time(), j, fh)
            log(f"start {j['id']} (mem free {fp}%, {len(running)} running, {len(pending)} pending)")
        if not running and pending:
            time.sleep(60)
            continue
        if not running:
            break
        time.sleep(10)
        for jid in list(running):
            p, t, j, fh = running[jid]
            if p.poll() is None:
                continue
            fh.close()
            del running[jid]
            done += 1
            summ = work / "results" / j["tag"] / j["building"] / j["weather"] / j["policy"] / "summary.json"
            rec = {"id": jid, "rc": p.returncode, "wall_s": round(time.time() - t, 1), "ok": summ.exists()}
            if summ.exists():
                d = json.loads(summ.read_text())
                rec.update({"total_reward": d["total_reward"], "steps": d["total_steps"],
                            "sec_per_step": d["seconds_per_step"]})
                for f in ("timeseries.csv", "ahu_log.csv", "diag.csv"):
                    fp2 = summ.parent / f
                    if fp2.exists():
                        with open(fp2, "rb") as fi, gzip.open(str(fp2) + ".gz", "wb", compresslevel=6) as fo:
                            shutil.copyfileobj(fi, fo)
                        fp2.unlink()
            with open(prog, "a") as f:
                f.write(json.dumps(rec) + "\n")
            log(f"done {jid} rc={p.returncode} {rec.get('total_reward')} ({done} done, {len(pending)} pending)")
        if not pending and not running:
            break
        if pending and len(running) < workers:
            fp = free_pct()
            if fp is not None and fp < MEM_MIN:
                time.sleep(50)
    log(f"all done: {done} jobs in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
