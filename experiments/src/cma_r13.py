"""Round 13: CMA-ES over 12 of SADR's constants, setback depths fixed at v12, started at r12var (plan: results/round13/PLAN.md).
Derived from cma_r12.py; same commands below (round12 -> round13).

    python cma_r12.py init      # state + generation 0 (v12 reference windows and the first 10 candidates), enqueued
    python cma_r12.py step      # one pass: score the current generation if complete, update, enqueue the next
    python cma_r12.py loop      # step every 5 min until 15 generations or sigma < 0.02 (run in the background)
    python cma_r12.py report    # progress, best candidates, current mean in parameter units
    python cma_r12.py final     # write results/round12/candidate_mean.json (the CMA mean, for confirmation)

The Kaggle dispatcher (kaggle_sim.py dispatch --loop --forever) must run alongside. Runs are 7-day windows (2,016
steps) of 24 fixed scenarios; results land in results/round6/runs/<variant>/<set>/<b>/<w>/transfer/summary.json.
Deterministic: the simulator reproduces bit for bit, and the sampler is seeded per generation.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R12 = RES / "round13"   # name kept from cma_r12.py; this is round 13's directory
RUNS = RES / "round6" / "runs"
JOBDIR = RES / "round6" / "kaggle_jobs"
KB = ROOT / "kit" / "smart_buildings"
POLICY_SRC = ROOT / "submission" / "transfer_policy.py"
POLICY = RES / "round12" / "policies" / "v12.py"   # round 12's frozen v12 copy, reused unchanged
STATE = R12 / "cma_state.json"
LOG = R12 / "cma_log.txt"
STEPS = 2016
SEED = 20261108
LAMBDA, MU, SIGMA0, GENS, SIGMA_STOP = 10, 5, 0.15, 12, 0.02
TIMEOUT_H = 4.0                            # a generation not complete after this is requeued once, then penalised
# Optional Mac share (results/round12/MAC_ON holds the number of candidates per generation, e.g. 5). A generation
# uses the Mac only if, when it is enqueued, the GPU lock is free, no speech-session job or queue waiter runs, and
# memory_pressure reports at least 50% free (weekend board rules). Mac candidates that do not finish within TIMEOUT_H
# are requeued on Kaggle. The Mac runner (mac_runner_r9.py) caps itself at 4 workers and pauses under the GPU lock.
MAC_FLAG = R12 / "MAC_ON"
MAC_ROOT = "/Users/neel.sirivara/neurips/sb/r13"
MAC_PY = "/Users/neel.sirivara/neurips/sb/kit/.venv/bin/python"
MAC_SRC = "/Users/neel.sirivara/neurips/sb/r9/src"
MAC_KIT = "/Users/neel.sirivara/neurips/sb/r6/sb/kit/smart_buildings"

# name, v12 value, low, high, scale
PARAMS = [
    ("wk_ext_lo", 12.0, 6.0, 14.0, "lin"),
    ("sb_boost_floor_k", 2.0, 0.0, 4.0, "lin"),
    ("sb_boost_h", 8.0, 4.0, 12.0, "lin"),
    ("lead_safety", 1.15, 0.9, 1.5, "lin"),
    ("lead_base_h", 0.5, 0.0, 1.5, "lin"),
    ("margin_pre", 0.8, 0.3, 1.5, "lin"),
    ("margin_occ", 0.3, 0.1, 0.8, "lin"),
    ("q_sb_w", 4000.0, 1500.0, 10000.0, "log"),
    ("kq_w_per_k", 400.0, 150.0, 1000.0, "log"),
    ("ki_w_per_k_step", 120.0, 40.0, 300.0, "log"),
    ("valve_target", 0.9, 0.7, 0.98, "lin"),
    ("sat_mix_floor", 292.0, 289.0, 294.0, "lin"),
]
N = len(PARAMS)
FIXED = {"night_low_ext": 10.0, "night_high_ext": 6.0}
START = json.loads((RES / "round12" / "candidate_v12setback.json").read_text())
SET_DIRS = {"r6hs": "heldout_scenarios_r6hs", "r10dev": "heldout_scenarios_r10dev"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now()} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def scenario_list():
    def keys(d):
        base = KB / d
        return sorted(f"{b.name}/{w.name}" for b in base.iterdir() if b.is_dir()
                      for w in b.iterdir() if (w / "config.gin").exists())
    harsh, public = [], []
    hs = keys(SET_DIRS["r6hs"])
    for b in sorted({k.split("/")[0] for k in hs}):
        harsh += [("r6hs", k) for k in [k for k in hs if k.startswith(b + "/")][:2]]
    dev = keys(SET_DIRS["r10dev"])
    for i, b in enumerate(sorted({k.split("/")[0] for k in dev})):
        want = ("atlanta", "phoenix") if i % 2 == 0 else ("denver", "singapore")
        public += [("r10dev", k) for k in dev if k.startswith(b + "/") and k.split("/")[1].split("_")[0] in want]
    assert len(harsh) == 12 and len(public) == 12, (len(harsh), len(public))
    return harsh, public


def to_params(x: np.ndarray) -> dict:
    out = {}
    for xi, (name, _v, lo, hi, sc) in zip(x, PARAMS):
        if sc == "log":
            out[name] = float(math.exp(math.log(lo) + xi * (math.log(hi) - math.log(lo))))
        else:
            out[name] = float(lo + xi * (hi - lo))
    out.update(FIXED)
    return out


def to_unit(vals: dict) -> np.ndarray:
    x = []
    for name, _v, lo, hi, sc in PARAMS:
        v = vals[name]
        x.append((math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) if sc == "log" else (v - lo) / (hi - lo))
    return np.array(x)


def mirror(x: np.ndarray) -> np.ndarray:
    x = np.mod(x, 2.0)
    return np.where(x > 1.0, 2.0 - x, x)


def summary_path(variant: str, set_name: str, key: str) -> Path:
    return RUNS / variant / set_name / key / "transfer" / "summary.json"


def write_jobs(variant: str, params: dict | None) -> Path:
    harsh, public = scenario_list()
    jobs = []
    for set_name, key in harsh + public:
        b, w = key.split("/")
        jobs.append({"id": f"{variant}/{set_name}/{key}", "tag": f"{variant}/{set_name}", "policy": "transfer",
                     "policy_path": str(POLICY), "set_dir": SET_DIRS[set_name], "building": b, "weather": w,
                     "steps": STEPS, "params": json.dumps(params, indent=1) if params else None, "save_ts": False,
                     "script": "run_scenario.py"})
    JOBDIR.mkdir(parents=True, exist_ok=True)
    f = JOBDIR / f"{variant}.json"
    f.write_text(json.dumps(jobs, indent=1))
    return f


def enqueue(files: list[Path]) -> None:
    r = subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                       capture_output=True, text=True, cwd=str(HERE / "kaggle_sim"))
    log(f"enqueue {len(files)} -> {r.stdout.strip()[-80:]} {r.stderr.strip()[-200:]}")


def losses(variant: str) -> dict | None:
    harsh, public = scenario_list()
    out = {}
    for set_name, key in harsh + public:
        p = summary_path(variant, set_name, key)
        if not p.exists():
            return None
        s = json.loads(p.read_text())
        if int(s.get("total_steps", 0)) != STEPS:
            return None
        out[f"{set_name}/{key}"] = abs(float(s["avg_reward"]))
    return out


def fitness(cand: dict, ref: dict) -> float:
    harsh, public = scenario_list()
    rh = np.mean([cand[f"{s}/{k}"] / ref[f"{s}/{k}"] for s, k in harsh])
    rp = np.mean([cand[f"{s}/{k}"] / ref[f"{s}/{k}"] for s, k in public])
    return float(rh / 3.0 + 2.0 * rp / 3.0)


class CMA:
    def __init__(self, st: dict):
        self.st = st
        n = N
        w = np.log(MU + 0.5) - np.log(np.arange(1, MU + 1))
        self.w = w / w.sum()
        self.mueff = 1.0 / np.sum(self.w ** 2)
        self.cs = (self.mueff + 2) / (n + self.mueff + 5)
        self.ds = 1 + 2 * max(0.0, math.sqrt((self.mueff - 1) / (n + 1)) - 1) + self.cs
        self.cc = (4 + self.mueff / n) / (n + 4 + 2 * self.mueff / n)
        self.c1 = 2 / ((n + 1.3) ** 2 + self.mueff)
        self.cmu = min(1 - self.c1, 2 * (self.mueff - 2 + 1 / self.mueff) / ((n + 2) ** 2 + self.mueff))
        self.chin = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))

    def sample(self, gen: int) -> list[np.ndarray]:
        m, sigma, C = np.array(self.st["mean"]), self.st["sigma"], np.array(self.st["C"])
        D2, B = np.linalg.eigh(C)
        D = np.sqrt(np.maximum(D2, 1e-20))
        rng = np.random.default_rng(SEED + gen)
        return [mirror(m + sigma * (B @ (D * rng.standard_normal(N)))) for _ in range(LAMBDA)]

    def update(self, xs: list[np.ndarray], fs: list[float]) -> None:
        st = self.st
        m, sigma, C = np.array(st["mean"]), st["sigma"], np.array(st["C"])
        ps, pc = np.array(st["ps"]), np.array(st["pc"])
        order = np.argsort(fs)
        sel = np.array([xs[i] for i in order[:MU]])
        y = (sel - m) / sigma
        yw = self.w @ y
        D2, B = np.linalg.eigh(C)
        Cinvsqrt = B @ np.diag(1 / np.sqrt(np.maximum(D2, 1e-20))) @ B.T
        ps = (1 - self.cs) * ps + math.sqrt(self.cs * (2 - self.cs) * self.mueff) * (Cinvsqrt @ yw)
        g = st["gen"] + 1
        hs = np.linalg.norm(ps) / math.sqrt(1 - (1 - self.cs) ** (2 * g)) < (1.4 + 2 / (N + 1)) * self.chin
        pc = (1 - self.cc) * pc + (math.sqrt(self.cc * (2 - self.cc) * self.mueff) * yw if hs else 0.0)
        rank_mu = sum(wi * np.outer(yi, yi) for wi, yi in zip(self.w, y))
        C = ((1 - self.c1 - self.cmu) * C + self.c1 * (np.outer(pc, pc) + (0 if hs else self.cc * (2 - self.cc)) * C)
             + self.cmu * rank_mu)
        sigma = sigma * math.exp((self.cs / self.ds) * (np.linalg.norm(ps) / self.chin - 1))
        st.update({"mean": mirror(m + sigma * 0 + (self.w @ sel - m)).tolist(), "sigma": float(sigma),
                   "C": ((C + C.T) / 2).tolist(), "ps": ps.tolist(), "pc": pc.tolist()})


def load() -> dict:
    return json.loads(STATE.read_text())


def save(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1))


def ssh(cmd: str, timeout: int = 60, inp: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "mac", cmd], input=inp,
                          capture_output=True, timeout=timeout)


def mac_share() -> int:
    if not MAC_FLAG.exists():
        return 0
    try:
        n = int(MAC_FLAG.read_text().strip() or "0")
        r = ssh("test -e ~/neurips/GPU_LOCK && echo LOCK; test -e ~/neurips/sb/r12/HOLD && echo HOLD; test -e ~/neurips/sb/r13/HOLD && echo HOLD; tail -1 ~/neurips/logs/weekend_check.log 2>/dev/null | grep -q ALERT && echo ALERT; "
                "pgrep -f 'speech/queue|speechenv' >/dev/null && echo SPEECH; "
                "memory_pressure | awk -F: '/free percentage/ {gsub(/[ %]/,\"\",$2); print \"FREE \" $2}'")
        out = r.stdout.decode(errors="replace")
        free = int(out.split("FREE ")[1].split()[0]) if "FREE " in out else 0
        if r.returncode not in (0, 1) or "LOCK" in out or "HOLD" in out or "ALERT" in out or "SPEECH" in out or free < 50:
            log(f"Mac not used this generation ({' '.join(out.split()) or 'no answer'})")
            return 0
        return max(0, min(n, LAMBDA))
    except Exception as e:  # noqa: BLE001
        log(f"Mac check failed: {e!r}")
        return 0


def mac_jobs(variant: str, params: dict) -> list[dict]:
    harsh, public = scenario_list()
    jobs = []
    for set_name, key in harsh + public:
        b, w = key.split("/")
        jobs.append({"id": f"{variant}__{set_name}__{b}__{w}", "cwd": MAC_ROOT,
                     "argv": [MAC_PY, f"{MAC_SRC}/run_scenario.py", "--policy", "transfer",
                              "--policy-file", f"{MAC_ROOT}/policies/v12.py", "--params-json",
                              f"{MAC_ROOT}/params/{variant}.json", "--building", b, "--weather", w,
                              "--steps", str(STEPS), "--results-dir", f"{MAC_ROOT}/out/runs/{variant}/{set_name}",
                              "--scenarios-dir", f"{MAC_KIT}/{SET_DIRS[set_name]}"]})
    return jobs


def start_mac(g: int, cands: list[dict]) -> bool:
    import base64
    files = {"policies/v12.py": POLICY.read_bytes()}
    jobs = []
    for c in cands:
        files[f"params/{c['variant']}.json"] = json.dumps(c["params"], indent=1).encode()
        jobs += mac_jobs(c["variant"], c["params"])
    files[f"jobs/g{g:02d}.json"] = json.dumps(jobs, indent=1).encode()
    script = [f"mkdir -p {MAC_ROOT}/policies {MAC_ROOT}/params {MAC_ROOT}/jobs {MAC_ROOT}/state {MAC_ROOT}/out ~/neurips/logs"]
    for rel, data in files.items():
        script.append(f"echo {base64.b64encode(data).decode()} | base64 -D > {MAC_ROOT}/{rel}")
    script.append(f"( cd {MAC_ROOT} && nohup {MAC_PY} {MAC_SRC}/mac_runner_r9.py --jobs jobs/g{g:02d}.json "
                  f"--state state/g{g:02d} --workers 4 > ~/neurips/logs/r13_g{g:02d}.log 2>&1 < /dev/null & ) "
                  f"> /dev/null 2>&1")
    script.append("echo STARTED")
    probe = f"pgrep -f 'jobs/g{g:02d}.json' >/dev/null && echo RUNNING"
    if b"RUNNING" in ssh(probe).stdout:
        log(f"gen {g}: a Mac runner for this generation is already running; not starting another")
        return True
    try:
        r = ssh("bash -s", timeout=60, inp="\n".join(script).encode())
        ok, err = b"STARTED" in r.stdout, r.stderr.decode()[-200:]
    except subprocess.TimeoutExpired:
        ok, err = False, "launch ssh timed out"
    if not ok:
        time.sleep(5)
        ok = b"RUNNING" in ssh(probe).stdout
    log(f"gen {g}: Mac runner for {len(cands)} candidates {'started' if ok else 'FAILED: ' + err}")
    return ok


def fetch_mac(variants: list[str]) -> None:
    """Copy the Mac's summary.json files of these variants into RUNS (tar over ssh, unpacked here)."""
    import io
    import tarfile
    if not variants:
        return
    pats = " ".join(f"./{v}" for v in variants)
    try:
        r = ssh(f"cd {MAC_ROOT}/out/runs 2>/dev/null && find {pats} -name summary.json 2>/dev/null | "
                f"tar cf - -T - 2>/dev/null", timeout=300)
    except subprocess.TimeoutExpired:
        log("Mac fetch timed out")
        return
    if not r.stdout:
        return
    n = 0
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            parts = Path(name).parts
            if not m.isfile() or ".." in parts or not name.endswith("summary.json") or parts[0] not in variants:
                continue
            dst = RUNS / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(tf.extractfile(m).read())
            n += 1
    if n:
        log(f"Mac fetch: {n} summaries")


def enqueue_generation(st: dict) -> None:
    cma = CMA(st)
    g = st["gen"]
    files, cands = [], []
    n_mac = mac_share()
    xs = cma.sample(g)
    for c, x in enumerate(xs):
        var = f"r13g{g:02d}c{c:02d}"
        p = to_params(x)
        where = "mac" if c >= LAMBDA - n_mac else "kaggle"
        if where == "kaggle":
            files.append(write_jobs(var, p))
        cands.append({"variant": var, "x": x.tolist(), "params": p, "where": where})
    mac_c = [c for c in cands if c["where"] == "mac"]
    if mac_c and not start_mac(g, mac_c):
        for c in mac_c:
            c["where"] = "kaggle"
            files.append(write_jobs(c["variant"], c["params"]))
    enqueue(files)
    st["pending"] = {"gen": g, "candidates": cands, "enqueued": now(), "requeued": False}
    save(st)
    log(f"gen {g}: enqueued {len(cands)} candidates ({sum(c['where'] == 'mac' for c in cands)} on the Mac), "
        f"sigma {st['sigma']:.4f}")


def cmd_init() -> int:
    R12.mkdir(parents=True, exist_ok=True)
    (R12 / "policies").mkdir(exist_ok=True)
    if STATE.exists():
        print("state exists; use step/loop")
        return 1
    harsh, public = scenario_list()
    assert all(START[k] == v for k, v in FIXED.items()), "start must carry v12's setback depths"
    x0 = to_unit(START)
    st = {"created": now(), "plan_sha256": hashlib.sha256((R12 / "PLAN.md").read_bytes()).hexdigest(),
          "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(), "scenarios": {"harsh": harsh, "public": public},
          "gen": 0, "mean": x0.tolist(), "sigma": SIGMA0, "C": np.eye(N).tolist(), "ps": [0.0] * N, "pc": [0.0] * N,
          "ref_variant": "r12ref", "history": [], "start": START, "fixed": FIXED}
    assert losses("r12ref") is not None, "round 12's v12 reference windows are missing"
    save(st)
    enqueue_generation(st)
    return 0


def cmd_step() -> str:
    st = load()
    if st["gen"] >= GENS or st["sigma"] < SIGMA_STOP:
        return "done"
    pend = st.get("pending")
    if not pend:
        enqueue_generation(st)
        return "enqueued"
    fetch_mac([c["variant"] for c in pend["candidates"] if c.get("where") == "mac" and losses(c["variant"]) is None])
    ref = losses(st["ref_variant"])
    got = {c["variant"]: losses(c["variant"]) for c in pend["candidates"]}
    missing = [v for v, l in got.items() if l is None]
    if ref is None or missing:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(pend["enqueued"].replace("Z", "+00:00"))).total_seconds() / 3600
        if age_h > TIMEOUT_H and not pend["requeued"]:
            for c in pend["candidates"]:
                if c["variant"] in missing and c.get("where") == "mac":
                    write_jobs(c["variant"], c["params"])
                    c["where"] = "kaggle (requeued from the Mac)"
            files = [JOBDIR / f"{v}.json" for v in missing]
            r = subprocess.run([sys.executable, str(HERE / "kaggle_sim" / "kaggle_sim.py"), "enqueue", *map(str, files)],
                               capture_output=True, text=True, cwd=str(HERE / "kaggle_sim"))
            pend["requeued"] = True
            pend["enqueued"] = now()
            save(st)
            log(f"gen {st['gen']}: requeued {len(missing)} after {age_h:.1f} h ({r.stdout.strip()[-60:]})")
            return "requeued"
        if age_h > 2 * TIMEOUT_H and ref is not None:
            log(f"gen {st['gen']}: penalising {len(missing)} candidates that never completed")
        else:
            return f"waiting ({len(missing)} of {len(got)} missing{', ref missing' if ref is None else ''})"
    fs = []
    for c in pend["candidates"]:
        l = got[c["variant"]]
        c["fitness"] = fitness(l, ref) if l else None
        fs.append(c["fitness"])
    worst = max(f for f in fs if f is not None)
    fs = [f if f is not None else worst + 0.05 for f in fs]
    xs = [np.array(c["x"]) for c in pend["candidates"]]
    st["history"].append({"gen": st["gen"], "mean_before": st["mean"], "sigma_before": st["sigma"],
                          "candidates": pend["candidates"], "best": float(min(fs)), "median": float(np.median(fs))})
    CMA(st).update(xs, fs)
    st["gen"] += 1
    st["pending"] = None
    save(st)
    log(f"gen {st['gen'] - 1} scored: best {min(fs):.4f}, median {np.median(fs):.4f}; sigma -> {st['sigma']:.4f}")
    if st["gen"] < GENS and st["sigma"] >= SIGMA_STOP:
        enqueue_generation(st)
    return "advanced"


def cmd_loop() -> int:
    while True:
        r = cmd_step()
        if r == "done":
            log("done: generations or sigma limit reached")
            return 0
        time.sleep(300)


def cmd_report() -> int:
    st = load()
    print(f"gen {st['gen']}, sigma {st['sigma']:.4f}, pending {bool(st.get('pending'))}")
    for h in st["history"]:
        print(f"  gen {h['gen']}: best {h['best']:.4f}, median {h['median']:.4f}, sigma {h['sigma_before']:.4f}")
    mean = to_params(np.array(st["mean"]))
    for name, v12, *_ in PARAMS:
        print(f"  {name:18s} v12 {v12:>9.3f}  mean {mean[name]:>9.3f}")
    return 0


def cmd_final() -> int:
    st = load()
    p = to_params(np.array(st["mean"]))
    (R12 / "candidate_mean.json").write_text(json.dumps(p, indent=1))
    print(json.dumps(p, indent=1))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    sys.exit({"init": cmd_init, "loop": cmd_loop, "report": cmd_report, "final": cmd_final}.get(cmd, lambda: print(cmd_step()) or 0)())
