"""Round 12 confirmation (PLAN.md, fixed before any run): the CMA mean at full length on HC3, HH and the public 30.

    python confirm_r12.py launch    # Kaggle: pub30 + r10hc (shards of 10); Mac: r10hh if free (else Kaggle too)
    python confirm_r12.py fetch     # Mac summaries -> results/round6/runs/r12cand/...
    python confirm_r12.py decide    # primary (1/3 HC3 + 2/3 HH mixture CI < 0) and guard (pub30 ratio <= 1)
v12's runs are r10_K (rounds 10-11, bit-reproducible across machines).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cma_r12 as c  # noqa: E402
import jobs_r6  # noqa: E402

R12 = c.R12
VAR, REF = "r12cand", "r10_K"
PARAMS = R12 / "candidate_mean.json"


def launch() -> int:
    files = []
    for s in ("pub30", "r10hc"):
        files += jobs_r6.make(VAR, s, str(PARAMS), False, 10, None, None, str(c.POLICY))
    n_mac = c.mac_share()
    hh = jobs_r6.scenarios("r10hh")
    if n_mac:
        p = json.loads(PARAMS.read_text())
        jobs = []
        for k in hh:
            b, w = k.split("/")
            jobs.append({"id": f"{VAR}__r10hh__{b}__{w}", "cwd": c.MAC_ROOT,
                         "argv": [c.MAC_PY, f"{c.MAC_SRC}/run_scenario.py", "--policy", "transfer", "--policy-file",
                                  f"{c.MAC_ROOT}/policies/v12.py", "--params-json", f"{c.MAC_ROOT}/params/{VAR}.json",
                                  "--building", b, "--weather", w, "--steps", "8640", "--results-dir",
                                  f"{c.MAC_ROOT}/out/runs/{VAR}/r10hh", "--scenarios-dir",
                                  f"{c.MAC_KIT}/heldout_scenarios_r10hh"]})
        import base64
        script = [f"mkdir -p {c.MAC_ROOT}/params {c.MAC_ROOT}/jobs {c.MAC_ROOT}/state",
                  f"echo {base64.b64encode(json.dumps(p, indent=1).encode()).decode()} | base64 -D > {c.MAC_ROOT}/params/{VAR}.json",
                  f"echo {base64.b64encode(json.dumps(jobs, indent=1).encode()).decode()} | base64 -D > {c.MAC_ROOT}/jobs/confirm.json",
                  f"( cd {c.MAC_ROOT} && nohup {c.MAC_PY} {c.MAC_SRC}/mac_runner_r9.py --jobs jobs/confirm.json "
                  f"--state state/confirm --workers 4 > ~/neurips/logs/r12_confirm.log 2>&1 < /dev/null & ) > /dev/null 2>&1",
                  "echo STARTED"]
        try:
            r = c.ssh("bash -s", timeout=60, inp="\n".join(script).encode())
        except Exception:  # noqa: BLE001
            pass
        ok = b"RUNNING" in c.ssh("pgrep -f 'jobs/confirm.json' >/dev/null && echo RUNNING").stdout
        c.log(f"confirm: HH on the Mac {'started' if ok else 'FAILED, on Kaggle instead'}")
        if not ok:
            files += jobs_r6.make(VAR, "r10hh", str(PARAMS), False, 10, None, None, str(c.POLICY))
    else:
        files += jobs_r6.make(VAR, "r10hh", str(PARAMS), False, 10, None, None, str(c.POLICY))
    c.enqueue(files)
    return 0


def losses(var: str, s: str) -> dict:
    out = {}
    for k in jobs_r6.scenarios(s):
        p = c.RUNS / var / s / k / "transfer" / "summary.json"
        if p.exists():
            d = json.loads(p.read_text())
            if d.get("total_steps") == 8640:
                out[k] = abs(float(d["avg_reward"]))
    return out


def decide() -> int:
    c.fetch_mac([VAR])
    res = {}
    for s in ("r10hc", "r10hh", "pub30"):
        cand, ref = losses(VAR, s), losses(REF, s)
        keys = sorted(set(cand) & set(ref))
        res[s] = {"n": len(keys), "n_need": len(jobs_r6.scenarios(s)),
                  "ratios": {k: cand[k] / ref[k] for k in keys}}
    done = all(r["n"] == r["n_need"] for r in res.values())
    rng = np.random.default_rng(20261107)
    hc = np.array(list(res["r10hc"]["ratios"].values()))
    hh = np.array(list(res["r10hh"]["ratios"].values()))
    pub = np.array(list(res["pub30"]["ratios"].values()))
    out = {"complete": done, "n": {s: res[s]["n"] for s in res}}
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
    (R12 / "decision.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit({"launch": launch, "decide": decide, "fetch": lambda: c.fetch_mac([VAR]) or 0}[sys.argv[1]]())
