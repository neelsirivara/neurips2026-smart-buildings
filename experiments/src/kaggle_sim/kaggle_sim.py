"""Round 6: run simulator sweeps as PRIVATE Kaggle script kernels instead of on the laptop.

The laptop only builds files and calls the Kaggle CLI; each kernel gets ~4 CPU cores and runs a shard of
(policy, scenario) jobs with the laptop's own runner (run_scenario.py) and the laptop's own kit copy, uploaded
as the private dataset neelsiri/sb26-sim-r6 (kit code + weather + scenario sets + runner, one tar.gz).
Never public: datasets are created without --public, kernels carry is_private true.

    python kaggle_sim.py build-dataset --sets r5m,r6hc,...      # stage + create/version the private dataset
    python kaggle_sim.py push --name t01 --jobs jobs.json [--internet] [--workers 4]
    python kaggle_sim.py status                                  # kernels status for every pushed shard
    python kaggle_sim.py fetch [--name t01]                      # kernels output -> results/round6/kaggle_out/<name>,
                                                                 # merged into results/round6/runs/<tag>/...
Job fields: id, tag (<variant>/<set>), policy ('transfer' | 'pid_water' ...), policy_path (local file, embedded),
set_dir (kit-relative scenario dir), building, weather, steps, params (JSON text or null), save_ts (bool).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
ROOT = SRC.parents[1]
KIT = ROOT / "kit"
KB = KIT / "smart_buildings"
R6 = ROOT / "experiments" / "results" / "round6"
REG = R6 / "kaggle_registry.json"
OUT = R6 / "kaggle_out"
RUNS = R6 / "runs"
KAGGLE = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".kaggle-cli-venv" / "Scripts" / "kaggle.exe"
STAGE = Path(os.environ.get("SB_KAGGLE_STAGE", str(Path(tempfile.gettempdir()) / "sb26_kaggle_stage")))
DATASET = "neelsiri/sb26-sim-r6"
USER = "neelsiri"
GIT_URL = "https://github.com/smart-buildings-2026/starter-kit"
RUNNERS = ["run_scenario.py", "run_diag.py"]
KIT_PARTS = ["__init__.py", "evaluate.py", "baselines", "smart_control", "weather", "training_scenarios"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kag(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run([str(KAGGLE), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"kaggle {' '.join(args)} failed: {r.stdout}\n{r.stderr}")
    return r


def load_reg() -> dict:
    return json.loads(REG.read_text()) if REG.exists() else {"dataset_versions": [], "kernels": {}}


def save_reg(reg: dict) -> None:
    REG.parent.mkdir(parents=True, exist_ok=True)
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1))
    os.replace(tmp, REG)


def _filter(ti: tarfile.TarInfo):
    n = ti.name
    if "__pycache__" in n or n.endswith(".pyc") or "/metrics" in n:
        return None
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    ti.mtime = 0
    return ti


def build_dataset(sets: list[str], message: str) -> int:
    ds = STAGE / "dataset"
    if ds.exists():
        shutil.rmtree(ds)
    ds.mkdir(parents=True)
    tgz = ds / "sb26sim.tar.gz"
    manifest = {}
    with tarfile.open(tgz, "w:gz", compresslevel=6) as tf:
        for part in KIT_PARTS + sets:
            p = KB / part
            if not p.exists():
                raise SystemExit(f"missing {p}")
            tf.add(p, arcname=f"kit/smart_buildings/{part}", filter=_filter)
            for f in ([p] if p.is_file() else sorted(p.rglob("*"))):
                if f.is_file() and "__pycache__" not in str(f) and not f.name.endswith(".pyc"):
                    manifest[f"kit/smart_buildings/{f.relative_to(KB).as_posix()}"] = \
                        hashlib.md5(f.read_bytes()).hexdigest()
        for rs in RUNNERS:
            tf.add(SRC / rs, arcname=f"runner/{rs}", filter=_filter)
            manifest[f"runner/{rs}"] = hashlib.md5((SRC / rs).read_bytes()).hexdigest()
    (ds / "dataset-metadata.json").write_text(json.dumps(
        {"title": "sb26 sim r6", "id": DATASET, "licenses": [{"name": "other"}],
         "description": "Private working copy of the Smart Buildings starter kit (Apache-2.0) and scenario "
                        "configs for simulator sweeps. Not for redistribution."}, indent=1))
    reg = load_reg()
    if any(v.get("rc") == 0 for v in reg["dataset_versions"]):
        r = kag("datasets", "version", "-p", str(ds), "-m", message, "--dir-mode", "skip")
    else:
        r = kag("datasets", "create", "-p", str(ds), "--dir-mode", "skip")
    print(r.stdout, r.stderr)
    entry = {"utc": now(), "sets": sets, "message": message, "rc": r.returncode, "tgz_bytes": tgz.stat().st_size,
             "tgz_md5": hashlib.md5(tgz.read_bytes()).hexdigest(), "n_files": len(manifest),
             "stdout": r.stdout[-500:]}
    reg["dataset_versions"].append(entry)
    save_reg(reg)
    (R6 / "kaggle_dataset_manifest.json").write_text(json.dumps(manifest, indent=0, sort_keys=True))
    print(json.dumps({k: v for k, v in entry.items() if k != "stdout"}, indent=1))
    return r.returncode


def push(name: str, jobs_file: Path, internet: bool, workers: int, deadline_h: float) -> int:
    jobs = json.loads(Path(jobs_file).read_text())
    policies: dict[str, str] = {}
    pmd5: dict[str, str] = {}
    kjobs = []
    for j in jobs:
        kj = {k: v for k, v in j.items() if k != "policy_path"}
        if j.get("policy_path"):
            src = Path(j["policy_path"])
            data = src.read_bytes()
            h = hashlib.md5(data).hexdigest()[:10]
            pname = f"{src.stem}_{h}.py"
            policies[pname] = base64.b64encode(data).decode()
            pmd5[pname] = hashlib.md5(data).hexdigest()
            kj["policy_file"] = pname
        kjobs.append(kj)
    tpl = (HERE / "shard_runner_template.py").read_text(encoding="utf-8")
    cfg = {"workers": workers, "deadline_h": deadline_h, "name": name, "pushed_utc": now()}
    if internet:
        cfg["git_url"] = GIT_URL
    for key, val in (("__JOBS_JSON__", kjobs), ("__POLICIES_JSON__", policies), ("__CONFIG_JSON__", cfg)):
        txt = json.dumps(val)
        if "'''" in txt:
            raise SystemExit("triple quote in payload")
        tpl = tpl.replace(key, txt, 1)
    slug = f"sb26-r6-{name}"
    kd = STAGE / "kernels" / name
    if kd.exists():
        shutil.rmtree(kd)
    kd.mkdir(parents=True)
    (kd / "run.py").write_text(tpl, encoding="utf-8", newline="\n")
    meta = {"id": f"{USER}/{slug}", "title": f"sb26 r6 {name}", "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": bool(internet), "dataset_sources": [DATASET], "competition_sources": [],
            "kernel_sources": [], "model_sources": []}
    (kd / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    r = kag("kernels", "push", "-p", str(kd))
    print(r.stdout, r.stderr)
    reg = load_reg()
    reg["kernels"].setdefault(name, {"pushes": []})
    reg["kernels"][name].update({"slug": f"{USER}/{slug}", "jobs_file": str(jobs_file), "n_jobs": len(jobs),
                                 "internet": internet, "workers": workers, "fetched": False,
                                 "policy_md5": pmd5, "run_py_md5": hashlib.md5(tpl.encode()).hexdigest()})
    reg["kernels"][name]["pushes"].append({"utc": now(), "rc": r.returncode, "out": (r.stdout + r.stderr)[-600:]})
    ok = r.returncode == 0 and "error" not in (r.stdout + r.stderr).lower()
    reg["kernels"][name]["state"] = "running" if ok else "push_failed"
    save_reg(reg)
    if not ok and "session count" in (r.stdout + r.stderr):
        return 2
    return 0 if ok else 1


def status(names: list[str] | None = None) -> dict:
    reg = load_reg()
    out = {}
    for name, k in reg["kernels"].items():
        if names and name not in names:
            continue
        if k.get("fetched") and not names:
            continue
        r = kag("kernels", "status", k["slug"])
        s = (r.stdout + r.stderr).strip().replace("\n", " ")
        out[name] = s
        print(f"{name:14s} {s[-160:]}")
    return out


def fetch(names: list[str] | None, force: bool = False) -> int:
    reg = load_reg()
    for name, k in reg["kernels"].items():
        if names and name not in names:
            continue
        if k.get("fetched") and not force:
            continue
        st = kag("kernels", "status", k["slug"]).stdout.lower()
        if "complete" not in st and not force:
            print(f"{name}: not complete ({st.strip()[-80:]})")
            continue
        od = OUT / name
        od.mkdir(parents=True, exist_ok=True)
        r = kag("kernels", "output", k["slug"], "-p", str(od), "-o")
        print(name, r.returncode, (r.stdout + r.stderr)[-300:])
        res = od / "results"
        n = 0
        if res.exists():
            for f in res.rglob("*"):
                if f.is_file():
                    dst = RUNS / f.relative_to(res)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f, dst)
                    n += f.name == "summary.json"
        prog = od / "progress.jsonl"
        nprog = len(prog.read_text().splitlines()) if prog.exists() else 0
        # round 6 fix (2026-10-26 ~22:35Z): a failed output download ("a problem on Kaggle's side") used to mark the
        # kernel fetched with 0 summaries; now it stays 'running' so the dispatcher retries the fetch next loop
        ok_dl = r.returncode == 0 and (n > 0 or nprog > 0)
        k.update({"fetched": "complete" in st and ok_dl, "fetched_utc": now(), "n_summaries": n, "n_progress": nprog})
        if "complete" in st and ok_dl:
            k["state"] = "fetched"
        elif "complete" in st:
            k["fetch_failures"] = int(k.get("fetch_failures", 0)) + 1
            print(f"{name}: output download failed (rc={r.returncode}, {n} summaries); will retry")
        print(f"{name}: merged {n} summaries ({nprog} progress lines, {k['n_jobs']} jobs)")
    save_reg(reg)
    return 0


QUEUE = R6 / "kaggle_queue.json"
DLOG = R6 / "kaggle_dispatch_log.txt"


def _rw_queue(fn):
    q = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    q2, ret = fn(q)
    tmp = QUEUE.with_suffix(".tmp")
    tmp.write_text(json.dumps(q2, indent=1))
    os.replace(tmp, QUEUE)
    return ret


def enqueue(files: list[str], front: bool = False) -> int:
    items = [{"name": Path(f).stem, "jobs": str(Path(f).resolve())} for f in files]

    def fn(q):
        names = {x["name"] for x in q}
        new = [x for x in items if x["name"] not in names]
        return (new + q if front else q + new), len(new)
    n = _rw_queue(fn)
    print(f"enqueued {n}")
    return 0


def dlog(msg: str) -> None:
    line = f"{now()} {msg}"
    print(line, flush=True)
    with open(DLOG, "a", encoding="utf-8") as f:
        f.write(line + chr(10))


def dispatch(loop: bool, max_running: int, interval: int, forever: bool = False) -> int:
    while True:
        reg = load_reg()
        running = []
        for name, k in reg["kernels"].items():
            if k.get("state") != "running":
                continue
            st = kag("kernels", "status", k["slug"]).stdout.strip()
            low = st.lower()
            if "complete" in low:
                dlog(f"complete {name}")
                fetch([name])
            elif "error" in low or "cancel" in low:
                dlog(f"FAILED {name}: {st[-120:]}")
                fetch([name], force=True)
                reg2 = load_reg()
                reg2["kernels"][name]["state"] = "error"
                save_reg(reg2)
            else:
                running.append(name)
        cap = max_running
        mf = R6 / "kaggle_max_slots.txt"          # optional override, re-read every loop (e.g. 4 while a probe runs)
        if mf.exists():
            try:
                cap = int(mf.read_text().strip())
            except ValueError:
                pass
        free = cap - len(running)
        pushed = 0
        while free > 0:
            item = _rw_queue(lambda q: (q[1:], q[0]) if q else (q, None))
            if item is None:
                break
            try:
                rc = push(item["name"], Path(item["jobs"]), False, 4, 11.0)
            except Exception as e:  # noqa: BLE001  (bad job file: park it, keep dispatching)
                dlog(f"PUSH-EXCEPTION {item['name']}: {e!r}; parked in kaggle_queue_parked.json")
                pk = R6 / "kaggle_queue_parked.json"
                parked = json.loads(pk.read_text()) if pk.exists() else []
                pk.write_text(json.dumps(parked + [item], indent=1))
                continue
            if rc == 2:
                _rw_queue(lambda q: ([item] + q, None))
                dlog(f"slot limit on {item['name']}; requeued")
                break
            dlog(f"pushed {item['name']} rc={rc}")
            if rc != 0:
                # round 6 fix (2026-10-26 ~18:10Z): a failed push (network error, non-JSON reply) used to drop the
                # item from the queue; now it goes back to the front and is parked after 3 failures.
                reg3 = load_reg()
                kk = reg3["kernels"].get(item["name"], {})
                kk["push_failures"] = int(kk.get("push_failures", 0)) + 1
                reg3["kernels"][item["name"]] = kk
                save_reg(reg3)
                if kk["push_failures"] >= 3:
                    pk = R6 / "kaggle_queue_parked.json"
                    parked = json.loads(pk.read_text()) if pk.exists() else []
                    pk.write_text(json.dumps(parked + [item], indent=1))
                    dlog(f"PARKED {item['name']} after {kk['push_failures']} failed pushes")
                else:
                    _rw_queue(lambda q: ([item] + q, None))
                    dlog(f"requeued {item['name']} (failure {kk['push_failures']})")
                break
            free -= 1
            pushed += 1
        qlen = len(json.loads(QUEUE.read_text())) if QUEUE.exists() else 0
        dlog(f"running {len(running) + pushed}, queued {qlen}")
        if not loop or (qlen == 0 and len(running) + pushed == 0 and not forever):
            return 0
        time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-dataset")
    b.add_argument("--sets", default="")
    b.add_argument("--message", default="update")
    p = sub.add_parser("push")
    p.add_argument("--name", required=True)
    p.add_argument("--jobs", required=True)
    p.add_argument("--internet", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--deadline-h", type=float, default=11.0)
    s = sub.add_parser("status")
    s.add_argument("--name", nargs="*")
    f = sub.add_parser("fetch")
    f.add_argument("--name", nargs="*")
    f.add_argument("--force", action="store_true")
    e = sub.add_parser("enqueue")
    e.add_argument("files", nargs="+")
    e.add_argument("--front", action="store_true")
    d = sub.add_parser("dispatch")
    d.add_argument("--loop", action="store_true")
    d.add_argument("--max", type=int, default=5)
    d.add_argument("--interval", type=int, default=60)
    d.add_argument("--forever", action="store_true")
    a = ap.parse_args()
    if a.cmd == "enqueue":
        return enqueue(a.files, a.front)
    if a.cmd == "dispatch":
        return dispatch(a.loop, a.max, a.interval, a.forever)
    if a.cmd == "build-dataset":
        return build_dataset([x for x in a.sets.split(",") if x], a.message)
    if a.cmd == "push":
        return push(a.name, Path(a.jobs), a.internet, a.workers, a.deadline_h)
    if a.cmd == "status":
        status(a.name)
        return 0
    if a.cmd == "fetch":
        return fetch(a.name, a.force)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
