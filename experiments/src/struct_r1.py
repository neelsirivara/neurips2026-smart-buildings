"""Structural screen round 1 (struct_r1): switches in policies_struct/sadr_struct.py, screened on the round-12
objective (24 seven-day windows of cma_r12.scenario_list(), 1/3 harsh + 2/3 public-like mean ratio vs v13).

All simulation runs on the Mac under ~/neurips/sb/struct (one runner at a time, at most 6 workers; GPU_LOCK and
memory gated). Results are copied back to experiments/results/struct_r1/runs/<variant>/<set>/<b>/<w>/.

    python struct_r1.py ship                       # copy policies + runner to the Mac
    python struct_r1.py launch <batch> <variant>=<policy>[:<params.json>] ...   (policy: v13 | struct)
    python struct_r1.py launch1 <batch> <variant>=<policy>[:<params.json>] <set>/<b>/<w> [steps]
    python struct_r1.py status <batch>
    python struct_r1.py fetch <variant> ...
    python struct_r1.py score <variant> ...        # writes results/struct_r1/screen_<variant>.json
"""
from __future__ import annotations

import base64
import csv
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cma_r12 as c  # noqa: E402  (scenario_list, SET_DIRS; nothing in round 12 is written)

ROOT = HERE.parents[1]
OUT = ROOT / "experiments" / "results" / "struct_r1"
RUNS = OUT / "runs"
POL_LOCAL = {"v13": ROOT / "submission" / "candidates" / "transfer_policy_v13.py",
             "struct": HERE / "policies_struct" / "sadr_struct.py"}
MAC = "/Users/neel.sirivara/neurips/sb/struct"
MAC_PY = c.MAC_PY
MAC_SRC = c.MAC_SRC
MAC_KIT = c.MAC_KIT
STEPS = 2016
REF = "v13ref"


def ssh(cmd: str, timeout: int = 120, inp: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "mac", cmd], input=inp,
                          capture_output=True, timeout=timeout)


def put_files(files: dict[str, bytes]) -> None:
    script = [f"mkdir -p {MAC}/policies {MAC}/params {MAC}/jobs {MAC}/state {MAC}/out {MAC}/src {MAC}/dbg"]
    for rel, data in files.items():
        script.append(f"echo {base64.b64encode(data).decode()} | base64 -D > {MAC}/{rel}")
    script.append("echo OK")
    r = ssh("bash -s", timeout=300, inp="\n".join(script).encode())
    assert b"OK" in r.stdout, r.stderr.decode()[-400:]


def cmd_ship() -> int:
    runner = ssh(f"cat {MAC_SRC}/mac_runner_r9.py").stdout.decode()
    runner = runner.replace("workers = min(max(1, a.workers), 4)", "workers = min(max(1, a.workers), 6)")
    files = {"policies/v13.py": POL_LOCAL["v13"].read_bytes(), "policies/sadr_struct.py": POL_LOCAL["struct"].read_bytes(),
             "src/mac_runner_struct.py": runner.encode()}
    put_files(files)
    r = ssh(f"shasum -a 256 {MAC}/policies/*.py")
    print(r.stdout.decode())
    return 0


def gate() -> None:
    r = ssh("test -e ~/neurips/GPU_LOCK && echo LOCK; pgrep -f mac_runner_struct >/dev/null && echo BUSY; "
            "memory_pressure | awk -F: '/free percentage/ {gsub(/[ %]/,\"\",$2); print \"FREE \" $2}'")
    out = r.stdout.decode()
    free = int(out.split("FREE ")[1].split()[0]) if "FREE " in out else 0
    if "LOCK" in out or "BUSY" in out or free < 50:
        raise SystemExit(f"gate closed: {' '.join(out.split())}")


def parse_variant(spec: str) -> tuple[str, str, Path | None]:
    var, rest = spec.split("=", 1)
    pol, _, prm = rest.partition(":")
    return var, pol, (Path(prm) if prm else None)


def job(var: str, pol: str, has_params: bool, set_name: str, key: str, steps: int = STEPS, dbg: bool = False) -> dict:
    b, w = key.split("/")
    pf = "v13.py" if pol == "v13" else "sadr_struct.py"
    argv = [MAC_PY, f"{MAC_SRC}/run_scenario.py", "--policy", "transfer", "--policy-file", f"{MAC}/policies/{pf}"]
    if has_params:
        argv += ["--params-json", f"{MAC}/params/{var}.json"]
    argv += ["--building", b, "--weather", w, "--steps", str(steps), "--save-ts",
             "--results-dir", f"{MAC}/out/runs/{var}/{set_name}", "--scenarios-dir", f"{MAC_KIT}/{c.SET_DIRS.get(set_name, set_name)}"]
    j = {"id": f"{var}__{set_name}__{b}__{w}", "cwd": MAC, "argv": argv}
    if dbg:
        j["env"] = {"SADR_DEBUG_LOG": f"{MAC}/dbg/{var}__{set_name}__{b}__{w}.csv"}
    return j


def start(batch: str, jobs: list[dict], files: dict[str, bytes]) -> None:
    gate()
    files[f"jobs/{batch}.json"] = json.dumps(jobs, indent=1).encode()
    put_files(files)
    script = (f"( cd {MAC} && nohup {MAC_PY} {MAC}/src/mac_runner_struct.py --jobs jobs/{batch}.json "
              f"--state state/{batch} --workers 6 > ~/neurips/logs/struct_{batch}.log 2>&1 < /dev/null & ) "
              f"> /dev/null 2>&1; sleep 2; pgrep -f 'jobs/{batch}.json' >/dev/null && echo RUNNING")
    r = ssh(script)
    print(batch, len(jobs), "jobs:", r.stdout.decode().strip() or r.stderr.decode()[-300:])


def cmd_launch(batch: str, specs: list[str], dbg: bool = False) -> int:
    harsh, public = c.scenario_list()
    jobs, files = [], {}
    for spec in specs:
        var, pol, prm = parse_variant(spec)
        if prm:
            files[f"params/{var}.json"] = prm.read_bytes()
        jobs += [job(var, pol, prm is not None, s, k, dbg=dbg) for s, k in harsh + public]
    start(batch, jobs, files)
    return 0


def cmd_launch1(batch: str, spec: str, sk: str, steps: str = str(STEPS)) -> int:
    var, pol, prm = parse_variant(spec)
    s, k = sk.split("/", 1)
    files = {f"params/{var}.json": prm.read_bytes()} if prm else {}
    start(batch, [job(var, pol, prm is not None, s, k, int(steps))], files)
    return 0


def hs18_keys() -> list[str]:
    base = c.KB / c.SET_DIRS["r6hs"]
    return sorted(f"{b.name}/{w.name}" for b in base.iterdir() if b.is_dir() for w in b.iterdir()
                  if (w / "config.gin").exists())


def cmd_launchhs(batch: str, specs: list[str]) -> int:
    """Full-length (8640 steps) HS-18 runs with time series, for the frost report of finalists."""
    jobs, files = [], {}
    for spec in specs:
        var, pol, prm = parse_variant(spec)
        if prm:
            files[f"params/{var}.json"] = prm.read_bytes()
        for k in hs18_keys():
            j = job(var, pol, prm is not None, "r6hs", k, steps=8640)
            j["argv"][j["argv"].index("--results-dir") + 1] = f"{MAC}/out/runs/{var}_hs18/r6hs"
            jobs.append(j)
    start(batch, jobs, files)
    return 0


def cmd_frosths(variants: list[str]) -> int:
    keys = [("r6hs", k) for k in hs18_keys()]
    ref = "v13ref_hs18"
    out = {}
    for var in [ref] + variants:
        d = f"{var}_hs18" if not var.endswith("_hs18") else var
        losses = {}
        for s, k in keys:
            p = RUNS / d / s / k / "summary.json"
            sm = json.loads(p.read_text())
            assert sm["total_steps"] == 8640, (d, k)
            losses[k] = abs(sm["avg_reward"])
        f = frost(d, keys)
        out[d] = {"n": len(losses), "mean_loss": float(np.mean(list(losses.values()))), "losses": losses, **f}
    r = out[ref]
    for d, v in out.items():
        if d != ref:
            ratios = [v["losses"][k] / r["losses"][k] for k in v["losses"]]
            v["hs18_mean_ratio_vs_v13"] = float(np.mean(ratios))
            v["hs18_wins"] = int(sum(x < 1 for x in ratios))
            v["below5_delta_pp"] = 100 * (v["below5_share"] - r["below5_share"])
            v["coldest_delta_k"] = v["coldest_c"] - r["coldest_c"]
        print(d, {k: (round(x, 5) if isinstance(x, float) else x) for k, x in v.items() if k != "losses"})
    (OUT / f"frost_hs18_{'_'.join(variants)}.json").write_text(json.dumps(out, indent=1))
    return 0


def cmd_status(batch: str) -> int:
    r = ssh(f"ls {MAC}/state/{batch}/*.done 2>/dev/null | wc -l; python3 -c 'import json;print(len(json.load(open(\"{MAC}/jobs/{batch}.json\"))))'; "
            f"pgrep -f 'jobs/{batch}.json' >/dev/null && echo RUNNING || echo STOPPED; tail -2 ~/neurips/logs/struct_{batch}.log")
    print(r.stdout.decode())
    return 0


def cmd_fetch(variants: list[str]) -> int:
    pats = " ".join(f"./{v}" for v in variants)
    r = ssh(f"cd {MAC}/out/runs && find {pats} \\( -name summary.json -o -name timeseries.csv \\) 2>/dev/null | tar czf - -T -",
            timeout=3600)
    n = 0
    with tarfile.open(fileobj=io.BytesIO(r.stdout), mode="r:*") as tf:
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            parts = Path(name).parts
            if not m.isfile() or ".." in parts or parts[0] not in variants:
                continue
            # out/runs/<var>/<set>/<b>/<w>/transfer/<file> -> RUNS/<var>/<set>/<b>/<w>/<file>
            dst = RUNS / parts[0] / parts[1] / parts[2] / parts[3] / parts[-1]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(tf.extractfile(m).read())
            n += 1
    print(f"fetched {n} files")
    return 0


def load(var: str, set_name: str, key: str) -> dict | None:
    p = RUNS / var / set_name / key / "summary.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())
    return s if int(s.get("total_steps", 0)) == STEPS else None


def frost(var: str, keys: list[tuple[str, str]]) -> dict:
    tmin, below, total = None, 0, 0
    for s, k in keys:
        f = RUNS / var / s / k / "timeseries.csv"
        with f.open() as fh:
            rd = csv.reader(fh)
            h = next(rd)
            zi = [i for i, x in enumerate(h) if x.startswith("zone_")]
            for row in rd:
                v = np.array([float(row[i]) for i in zi])
                tmin = float(v.min()) if tmin is None else min(tmin, float(v.min()))
                below += int((v < 278.15).sum())
                total += v.size
    return {"coldest_c": tmin - 273.15, "below5_share": below / total}


def comps(s: dict) -> dict:
    n = s["total_steps"]
    w = (s["productivity_weight"], s["energy_weight"], s["carbon_weight"])
    tw = sum(w)
    return {"comfort": -s["total_normalized_productivity_regret"] * w[0] / tw / n,
            "energy": s["total_normalized_energy_cost"] * w[1] / tw / n,
            "carbon": s["total_normalized_carbon_emission"] * w[2] / tw / n}


def cmd_score(variants: list[str]) -> int:
    harsh, public = c.scenario_list()
    for var in variants:
        per, comp = {}, {"harsh": {}, "public": {}}
        for grp, lst in (("harsh", harsh), ("public", public)):
            acc = {"comfort": [0.0, 0.0], "energy": [0.0, 0.0], "carbon": [0.0, 0.0]}
            for s, k in lst:
                a, r = load(var, s, k), load(REF, s, k)
                if a is None or r is None:
                    print(f"{var}: missing {s}/{k}")
                    return 1
                per[f"{s}/{k}"] = {"loss": abs(a["avg_reward"]), "ref": abs(r["avg_reward"]),
                                   "ratio": abs(a["avg_reward"]) / abs(r["avg_reward"])}
                ca, cr = comps(a), comps(r)
                for t in acc:
                    acc[t][0] += ca[t]
                    acc[t][1] += cr[t]
            comp[grp] = {t: {"cand": v[0] / len(lst), "ref": v[1] / len(lst)} for t, v in acc.items()}
        rh = float(np.mean([per[f"{s}/{k}"]["ratio"] for s, k in harsh]))
        rp = float(np.mean([per[f"{s}/{k}"]["ratio"] for s, k in public]))
        out = {"variant": var, "ref": REF, "harsh_ratio": rh, "public_ratio": rp, "mixture": rh / 3 + 2 * rp / 3,
               "harsh_wins": sum(per[f"{s}/{k}"]["ratio"] < 1 for s, k in harsh),
               "public_wins": sum(per[f"{s}/{k}"]["ratio"] < 1 for s, k in public),
               "components_per_step": comp, "frost_hs12": frost(var, harsh), "frost_hs12_ref": frost(REF, harsh),
               "per_window": per}
        if var != REF:
            pf = RUNS / var / "params.json"
            if pf.exists():
                out["params"] = json.loads(pf.read_text())
        (OUT / f"screen_{var}.json").write_text(json.dumps(out, indent=1))
        f = out["frost_hs12"]
        print(f"{var}: harsh {rh:.4f} ({out['harsh_wins']}/12)  public {rp:.4f} ({out['public_wins']}/12)  "
              f"mix {out['mixture']:.4f}  coldest {f['coldest_c']:.2f} C  below5 {100 * f['below5_share']:.2f}%")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "ship":
        sys.exit(cmd_ship())
    if a[0] == "launch":
        sys.exit(cmd_launch(a[1], [x for x in a[2:] if x != "--dbg"], dbg="--dbg" in a))
    if a[0] == "launch1":
        sys.exit(cmd_launch1(*a[1:]))
    if a[0] == "launchhs":
        sys.exit(cmd_launchhs(a[1], a[2:]))
    if a[0] == "frosths":
        sys.exit(cmd_frosths(a[1:]))
    if a[0] == "status":
        sys.exit(cmd_status(a[1]))
    if a[0] == "fetch":
        sys.exit(cmd_fetch(a[1:]))
    if a[0] == "score":
        sys.exit(cmd_score(a[1:]))

