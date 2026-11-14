"""Round 13 confirmation (results/round13/PLAN.md), adapted from confirm_r12v.py. Original header follows.

Round 12 follow-up (user, 2026-11-08: "run new experiments ... best possible performance"): the frost-safe variant.

Candidate r12var = the round-12 CMA mean (candidate_mean.json) with v12's two setback depths restored
(night_low_ext 10.0, night_high_ext 6.0); every other tuned constant kept. Same confirmation and ship rule as
confirm_r12.py (PLAN.md: 1/3 HC3 + 2/3 HH mixture 95% CI < 0, and pub30 not worse), plus the HS frost report of
frost_r12.py. Round-12 outputs (decision.json, frost.json, r12cand runs) are not touched.

    python confirm_r12v.py launch   # Kaggle: pub30 + r10hc; Mac: r10hh + r6hs (save-ts) if free, else all Kaggle
    python confirm_r12v.py decide   # fetch Mac summaries, write round12/decision_r12var.json (+ frost when HS is in)
"""
from __future__ import annotations

import base64
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "paper"))
import cma_r12 as c  # noqa: E402
import jobs_r6  # noqa: E402

R12 = c.R12
VAR, REF, FROST_REF = "r13cand", "r10_K", "ab12_ref"
R13 = R12.parent / "round13"
PARAMS = R13 / "candidate_mean.json"
OUT = R13 / "decision.json"
FROST_OUT = R13 / "frost.json"


def make_params() -> dict:
    p = json.loads(PARAMS.read_text())   # round 13's CMA mean, used as is (depths already fixed at v12)
    assert p["night_low_ext"] == 10.0 and p["night_high_ext"] == 6.0
    return p


def mac_job(set_name: str, key: str, save_ts: bool, kit_dir: str) -> dict:
    b, w = key.split("/")
    argv = [c.MAC_PY, f"{c.MAC_SRC}/run_scenario.py", "--policy", "transfer", "--policy-file",
            f"{c.MAC_ROOT}/policies/v12.py", "--params-json", f"{c.MAC_ROOT}/params/{VAR}.json",
            "--building", b, "--weather", w, "--steps", "8640"]
    if save_ts:
        argv.append("--save-ts")
    argv += ["--results-dir", f"{c.MAC_ROOT}/out/runs/{VAR}/{set_name}", "--scenarios-dir", f"{c.MAC_KIT}/{kit_dir}"]
    return {"id": f"{VAR}__{set_name}__{b}__{w}", "cwd": c.MAC_ROOT, "argv": argv}


def launch() -> int:
    p = make_params()
    files = []
    for s in ("pub30", "r10hc"):
        files += jobs_r6.make(VAR, s, str(PARAMS), False, 10, None, None, str(c.POLICY))
    ok = False
    if c.mac_share():
        jobs = [mac_job("r10hh", k, False, "heldout_scenarios_r10hh") for k in jobs_r6.scenarios("r10hh")]
        hs = sorted(Path(x).parts[-4] + "/" + Path(x).parts[-3] for x in
                    (str(q) for q in (c.RUNS / FROST_REF / "r6hs").glob("*/*/transfer/summary.json")))
        jobs += [mac_job("r6hs", k, True, "heldout_scenarios_r6hs") for k in hs]
        script = [f"mkdir -p {c.MAC_ROOT}/params {c.MAC_ROOT}/jobs {c.MAC_ROOT}/state ~/neurips/logs",
                  f"echo {base64.b64encode(json.dumps(p, indent=1).encode()).decode()} | base64 -D > {c.MAC_ROOT}/params/{VAR}.json",
                  f"echo {base64.b64encode(json.dumps(jobs, indent=1).encode()).decode()} | base64 -D > {c.MAC_ROOT}/jobs/{VAR}.json",
                  f"( cd {c.MAC_ROOT} && nohup {c.MAC_PY} {c.MAC_SRC}/mac_runner_r9.py --jobs jobs/{VAR}.json "
                  f"--state state/{VAR} --workers 4 > ~/neurips/logs/{VAR}.log 2>&1 < /dev/null & ) > /dev/null 2>&1",
                  "echo STARTED"]
        try:
            c.ssh("bash -s", timeout=60, inp="\n".join(script).encode())
        except Exception:  # noqa: BLE001
            pass
        ok = b"RUNNING" in c.ssh(f"pgrep -f 'jobs/{VAR}.json' >/dev/null && echo RUNNING").stdout
        c.log(f"{VAR}: HH ({len(jobs) - len(hs)}) + HS frost ({len(hs)}) on the Mac {'started' if ok else 'FAILED'}")
    if not ok:
        files += jobs_r6.make(VAR, "r10hh", str(PARAMS), False, 10, None, None, str(c.POLICY))
        files += jobs_r6.make(VAR, "r6hs", str(PARAMS), True, 10, None, None, str(c.POLICY))
        c.log(f"{VAR}: HH and HS go to Kaggle")
    c.enqueue(files)
    return 0


def losses(var: str, s: str) -> dict:
    out = {}
    for k in jobs_r6.scenarios(s):
        q = c.RUNS / var / s / k / "transfer" / "summary.json"
        if q.exists():
            d = json.loads(q.read_text())
            if d.get("total_steps") == 8640:
                out[k] = abs(float(d["avg_reward"]))
    return out


def fetch_hs_ts() -> None:
    """HS runs carry time series (needed for frost); copy the whole r6hs tree of this variant from the Mac."""
    try:
        r = c.ssh(f"cd {c.MAC_ROOT}/out/runs 2>/dev/null && test -d ./{VAR}/r6hs && find ./{VAR}/r6hs -type f | tar cf - -T -",
                  timeout=600)
    except Exception:  # noqa: BLE001
        return
    if not r.stdout:
        return
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for mem in tf.getmembers():
            name = mem.name.lstrip("./")
            if mem.isfile() and ".." not in Path(name).parts and Path(name).parts[0] == VAR:
                dst = c.RUNS / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(tf.extractfile(mem).read())


def frost() -> dict | None:
    import make_macros_r11 as m  # noqa: E402
    cand = m.summaries(f"round6/runs/{VAR}/r6hs/*/*/transfer/summary.json")
    ref = m.summaries(f"round6/runs/{FROST_REF}/r6hs/*/*/transfer/summary.json")
    if len(cand) < len(ref):
        return None
    tc, bc, nc = m.coldest(cand)
    tr, br, nr = m.coldest(ref)
    out = {"n_cand": len(cand), "n_ts_cand": nc, "n_ts_ref": nr,
           "coldest_c_cand": tc - 273.15 if tc else None, "coldest_c_v12": tr - 273.15 if tr else None,
           "below5_cand": bc, "below5_v12": br,
           "hs_loss_ratio": (sum(abs(s["avg_reward"]) for s in cand.values()) / len(cand))
           / (sum(abs(s["avg_reward"]) for s in ref.values()) / len(ref))}
    FROST_OUT.write_text(json.dumps(out, indent=1))
    return out


def decide() -> int:
    c.fetch_mac([VAR])
    fetch_hs_ts()
    res = {}
    for s in ("r10hc", "r10hh", "pub30"):
        cand, ref = losses(VAR, s), losses(REF, s)
        keys = sorted(set(cand) & set(ref))
        res[s] = {"n": len(keys), "n_need": len(jobs_r6.scenarios(s)), "ratios": {k: cand[k] / ref[k] for k in keys}}
    done = all(r["n"] == r["n_need"] for r in res.values())
    rng = np.random.default_rng(20261107)
    hc = np.array(list(res["r10hc"]["ratios"].values()))
    hh = np.array(list(res["r10hh"]["ratios"].values()))
    pub = np.array(list(res["pub30"]["ratios"].values()))
    out = {"variant": VAR, "complete": done, "n": {s: res[s]["n"] for s in res}}
    if len(hc) and len(hh):
        mix = hc.mean() / 3 + 2 * hh.mean() / 3 - 1
        boots = [rng.choice(hc, len(hc)).mean() / 3 + 2 * rng.choice(hh, len(hh)).mean() / 3 - 1 for _ in range(2000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out.update({"mixture": mix, "mixture_ci": [lo, hi], "hc3": hc.mean() - 1, "hh": hh.mean() - 1,
                    "hc3_wins": int((hc < 1).sum()), "hh_wins": int((hh < 1).sum())})
    if len(pub):
        out.update({"pub30": pub.mean() - 1, "pub30_wins": int((pub < 1).sum())})
    if done:
        out["primary_pass"] = bool(out["mixture_ci"][1] < 0)
        out["guard_pass"] = bool(pub.mean() <= 1.0)
        out["ship"] = out["primary_pass"] and out["guard_pass"]
    f = frost()
    if f:
        out["frost"] = f
    out["frost_complete"] = bool(f)
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit({"launch": launch, "decide": decide, "params": lambda: print(json.dumps(make_params(), indent=1)) or 0}[sys.argv[1]]())
