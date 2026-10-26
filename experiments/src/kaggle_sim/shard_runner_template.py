# Round 6: one shard of (policy, scenario) simulator jobs, run inside a PRIVATE Kaggle script kernel.
#
# Built by experiments/src/kaggle_sim/kaggle_sim.py, which replaces the three  __..._JSON__  lines below
# with the shard's jobs, the policy sources (base64) and the parameter files. The simulator is the
# starter kit (Apache-2.0) copied into the private dataset neelsiri/sb26-sim-r6 from the laptop's kit, so the
# code is byte-identical to the laptop's; run_scenario.py is the laptop's runner, unchanged.
# Outputs (fetched with `kaggle kernels output`):
#   /kaggle/working/results/<tag>/<building>/<weather>/<policy>/summary.json   (+ timeseries/ahu_log .csv.gz)
#   /kaggle/working/progress.jsonl, env.json, git_check.json, logs/<job>.log
import base64
import gzip
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

JOBS = json.loads(r'''__JOBS_JSON__''')
POLICIES = json.loads(r'''__POLICIES_JSON__''')
CONFIG = json.loads(r'''__CONFIG_JSON__''')

T0 = time.time()
WORK = Path("/kaggle/working")
SB = Path("/tmp/sb")
LOGS = WORK / "logs"
LOGS.mkdir(parents=True, exist_ok=True)


def log(msg):
    line = f"[{time.time() - T0:8.1f}s] {msg}"
    print(line, flush=True)
    with open(WORK / "runner_log.txt", "a") as f:
        f.write(line + "\n")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def find_kit():
    """Return the dataset's kit dir (extracted by Kaggle) or extract the archive into /tmp/sb."""
    roots = [Path("/kaggle/input")]
    for root in roots:
        for dp, dn, fn in os.walk(root):
            if "evaluate.py" in fn and dp.replace("\\", "/").endswith("kit/smart_buildings"):
                return Path(dp).parent, Path(dp).parent.parent
    for root in roots:
        for dp, dn, fn in os.walk(root):
            for f in fn:
                p = Path(dp) / f
                if f.startswith("sb26sim") and (f.endswith(".tar.gz") or f.endswith(".zip")):
                    log(f"extracting {p}")
                    (SB / "x").mkdir(parents=True, exist_ok=True)
                    if f.endswith(".zip"):
                        zipfile.ZipFile(p).extractall(SB / "x")
                    else:
                        tarfile.open(p).extractall(SB / "x")
                    for dp2, dn2, fn2 in os.walk(SB / "x"):
                        if "evaluate.py" in fn2 and dp2.replace("\\", "/").endswith("kit/smart_buildings"):
                            return Path(dp2).parent, Path(dp2).parent.parent
    raise SystemExit("kit not found under /kaggle/input")


def env_info(extra):
    info = {"python": sys.version, "platform": platform.platform(), "cpu_count": os.cpu_count()}
    for m in ("numpy", "numba", "pandas", "gin", "gymnasium", "scipy", "holidays"):
        try:
            mod = __import__(m)
            info[m] = getattr(mod, "__version__", "?")
        except Exception as e:  # noqa: BLE001
            info[m] = f"ERR {e}"
    try:
        info["mem_total_gb"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except Exception:  # noqa: BLE001
        pass
    info.update(extra)
    (WORK / "env.json").write_text(json.dumps(info, indent=1))
    log(f"env: {info}")


def git_check(kit_dir):
    """Internet test: clone the official starter kit and compare its simulator code with the dataset's copy."""
    out = {"attempted": True}
    gh = SB / "gh"
    try:
        r = subprocess.run(["git", "clone", "--depth", "1", CONFIG.get("git_url"), str(gh)],
                           capture_output=True, text=True, timeout=300)
        out["clone_rc"] = r.returncode
        out["clone_err"] = r.stderr[-2000:]
        if r.returncode == 0:
            hd = subprocess.run(["git", "-C", str(gh), "log", "-1", "--format=%H %cI %s"], capture_output=True,
                                text=True)
            out["head"] = hd.stdout.strip()
            same, differ, only_ds, only_gh = 0, [], [], []
            for sub in ("smart_control", "baselines", "evaluate.py", "__init__.py", "weather", "training_scenarios"):
                a, b = kit_dir / "smart_buildings" / sub, gh / "smart_buildings" / sub
                fa = {str(p.relative_to(a)): p for p in ([a] if a.is_file() else a.rglob("*")) if p.is_file()} \
                    if a.exists() else {}
                fb = {str(p.relative_to(b)): p for p in ([b] if b.is_file() else b.rglob("*")) if p.is_file()} \
                    if b.exists() else {}
                for k in sorted(set(fa) | set(fb)):
                    if "__pycache__" in k or k.endswith(".pyc"):
                        continue
                    if k not in fb:
                        only_ds.append(f"{sub}/{k}")
                    elif k not in fa:
                        only_gh.append(f"{sub}/{k}")
                    elif md5(fa[k]) == md5(fb[k]):
                        same += 1
                    else:
                        differ.append(f"{sub}/{k}")
            out.update({"same": same, "differ": differ, "only_dataset": only_ds[:200], "only_github": only_gh[:200]})
    except Exception as e:  # noqa: BLE001
        out["error"] = repr(e)
    (WORK / "git_check.json").write_text(json.dumps(out, indent=1))
    log(f"git check: rc={out.get('clone_rc')} same={out.get('same')} differ={out.get('differ')}")
    return out


def main():
    src_kit, ds_root = find_kit()
    kit = SB / "kit"
    if not kit.exists():
        shutil.copytree(src_kit, kit)
    rdir = SB / "experiments" / "src"          # run_scenario.py resolves ROOT = parents[1]
    rdir.mkdir(parents=True, exist_ok=True)
    for f in (ds_root / "runner").iterdir():
        shutil.copy(f, rdir / f.name)
    pdir = SB / "policies"
    pdir.mkdir(exist_ok=True)
    for name, b64 in POLICIES.items():
        (pdir / name).write_bytes(base64.b64decode(b64))
    env_info({"dataset_root": str(ds_root), "n_jobs": len(JOBS), "config": CONFIG,
              "runner_md5": {f.name: md5(f) for f in rdir.iterdir() if f.is_file()},
              "policy_md5": {n: md5(pdir / n) for n in POLICIES}})
    if CONFIG.get("git_url"):
        git_check(kit)

    workers = int(CONFIG.get("workers") or os.cpu_count() or 4)
    deadline = T0 + float(CONFIG.get("deadline_h", 11.0)) * 3600
    pending = list(JOBS)
    running = {}
    done = 0
    while pending or running:
        while pending and len(running) < workers and time.time() < deadline:
            j = pending.pop(0)
            res = WORK / "results" / j["tag"]
            script = j.get("script") or "run_scenario.py"
            cmd = [sys.executable, str(rdir / script), "--policy", j["policy"], "--building", j["building"],
                   "--weather", j["weather"], "--steps", str(j["steps"]), "--results-dir", str(res),
                   "--scenarios-dir", str(kit / "smart_buildings" / j["set_dir"])]
            if j.get("policy_file"):
                cmd += ["--policy-file", str(pdir / j["policy_file"])]
            if j.get("params"):
                pp = pdir / (j["id"].replace("/", "__") + ".params.json")
                pp.write_text(j["params"])
                cmd += ["--params-json", str(pp)]
            if j.get("save_ts"):
                cmd.append("--save-ts")
            env = dict(os.environ)
            for k in ("OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
                env[k] = "1"
            env["SB_KIT_DIR"] = str(kit)
            fh = open(LOGS / (j["id"].replace("/", "__") + ".log"), "w")
            p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=str(kit))
            running[j["id"]] = (p, time.time(), j, fh)
            log(f"start {j['id']} ({len(running)} running, {len(pending)} pending)")
        if not running:
            break
        time.sleep(5)
        for jid in list(running):
            p, t, j, fh = running[jid]
            if p.poll() is None:
                continue
            fh.close()
            del running[jid]
            done += 1
            summ = WORK / "results" / j["tag"] / j["building"] / j["weather"] / j["policy"] / "summary.json"
            rec = {"id": jid, "rc": p.returncode, "wall_s": round(time.time() - t, 1), "ok": summ.exists()}
            if summ.exists():
                d = json.loads(summ.read_text())
                rec.update({"total_reward": d["total_reward"], "steps": d["total_steps"],
                            "sec_per_step": d["seconds_per_step"]})
                for f in ("timeseries.csv", "ahu_log.csv", "diag.csv"):
                    fp = summ.parent / f
                    if fp.exists():
                        with open(fp, "rb") as fi, gzip.open(str(fp) + ".gz", "wb", compresslevel=6) as fo:
                            shutil.copyfileobj(fi, fo)
                        fp.unlink()
            with open(WORK / "progress.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")
            log(f"done {jid} rc={p.returncode} {rec.get('total_reward')} ({done} done)")
        if time.time() >= deadline and pending:
            log(f"deadline: {len(pending)} jobs not started")
            with open(WORK / "not_started.json", "w") as f:
                json.dump([j["id"] for j in pending], f)
            pending = []
    log(f"all done: {done} jobs in {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
