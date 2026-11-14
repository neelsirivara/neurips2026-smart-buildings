"""struct_r1 finalist HA: full-length confirmation vs v13 (results/struct_r1/CONFIRM_PLAN.md, sha256 8b82778e...).

HA = policies_struct/sadr_struct.py (v13 constants baked) + {"st_hand_c_h": 1.0}. Comparator: v13 = r12var's existing
full-length runs, valid only if fresh v13 runs (submission/candidates/transfer_policy_v13.py, no params) on 2 scenarios
per set reproduce them to a relative 1e-9 (the "v13chk" runs, on the Mac).

    python confirm_struct_ha.py launch   # Kaggle: pub30 + r10hc for HA; Mac: HA r10hh (40) + v13chk (2 per set)
    python confirm_struct_ha.py decide   # writes results/struct_r1/decision_HA.json
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cma_r12 as c  # noqa: E402  (ssh, enqueue, fetch_mac, Mac paths)
import jobs_r6  # noqa: E402

RES = c.RES
SR = RES / "struct_r1"
import os
VAR, CHK = "struct_HA", "v13chk"
# CONFIRM_PLAN: if v13chk fails 1e-9, v13 is re-run on all three sets ("v13fresh", same hosts as HA) and becomes REF
REF = os.environ.get("HA_REF", "r12var")
POL_HA = HERE / "policies_struct" / "sadr_struct.py"
POL_V13 = HERE.parents[1] / "submission" / "candidates" / "transfer_policy_v13.py"
PARAMS = SR / "params" / "HA.json"
OUT = SR / ("decision_HA_v13fresh.json" if os.environ.get("HA_REF") == "v13fresh" else "decision_HA.json")
MROOT = "/Users/neel.sirivara/neurips/sb/structc"
KITDIR = {"r10hc": "heldout_scenarios_r10hc", "r10hh": "heldout_scenarios_r10hh", "pub30": "training_scenarios"}


def chk_keys() -> dict:
    return {s: jobs_r6.scenarios(s)[:2] for s in ("r10hc", "r10hh", "pub30")}


def mac_job(var: str, s: str, key: str, policy: str, params: str | None) -> dict:
    b, w = key.split("/")
    argv = [c.MAC_PY, f"{c.MAC_SRC}/run_scenario.py", "--policy", "transfer", "--policy-file", f"{MROOT}/policies/{policy}"]
    if params:
        argv += ["--params-json", f"{MROOT}/params/{params}"]
    argv += ["--building", b, "--weather", w, "--steps", "8640", "--results-dir", f"{MROOT}/out/runs/{var}/{s}",
             "--scenarios-dir", f"{c.MAC_KIT}/{KITDIR[s]}"]
    return {"id": f"{var}__{s}__{b}__{w}", "cwd": MROOT, "argv": argv}


def launch() -> int:
    files = []
    for s in ("pub30", "r10hc"):
        files += jobs_r6.make(VAR, s, str(PARAMS), False, 10, None, None, str(POL_HA))
    jobs = [mac_job(VAR, "r10hh", k, "sadr_struct.py", "HA.json") for k in jobs_r6.scenarios("r10hh")]
    jobs += [mac_job(CHK, s, k, "transfer_policy_v13.py", None) for s, ks in chk_keys().items() for k in ks]
    put = {"policies/sadr_struct.py": POL_HA.read_bytes(), "policies/transfer_policy_v13.py": POL_V13.read_bytes(),
           "params/HA.json": PARAMS.read_bytes(), "jobs/confirm.json": json.dumps(jobs, indent=1).encode()}
    script = [f"mkdir -p {MROOT}/policies {MROOT}/params {MROOT}/jobs {MROOT}/state {MROOT}/out ~/neurips/logs"]
    script += [f"echo {base64.b64encode(d).decode()} | base64 -D > {MROOT}/{rel}" for rel, d in put.items()]
    script += [f"( cd {MROOT} && nohup {c.MAC_PY} {c.MAC_SRC}/mac_runner_r9.py --jobs jobs/confirm.json --state state/confirm "
               f"--workers 6 > ~/neurips/logs/structc.log 2>&1 < /dev/null & ) > /dev/null 2>&1", "echo STARTED"]
    try:
        c.ssh("bash -s", timeout=90, inp="\n".join(script).encode())
    except Exception:  # noqa: BLE001
        pass
    ok = b"RUNNING" in c.ssh(f"pgrep -f '{MROOT}|state/confirm --workers 6' >/dev/null && echo RUNNING").stdout
    c.log(f"structHA: Mac batch ({len(jobs)} runs) {'started' if ok else 'FAILED'}")
    if not ok:
        return 1
    c.enqueue(files)
    return 0


def launch_ref() -> int:
    """v13 fresh on all three sets, same hosts as HA: Kaggle pub30 + r10hc, Mac r10hh."""
    files = []
    for s in ("pub30", "r10hc"):
        files += jobs_r6.make("v13fresh", s, None, False, 10, None, None, str(POL_V13))
    jobs = [mac_job("v13fresh", "r10hh", k, "transfer_policy_v13.py", None) for k in jobs_r6.scenarios("r10hh")]
    script = [f"echo {base64.b64encode(json.dumps(jobs, indent=1).encode()).decode()} | base64 -D > {MROOT}/jobs/v13fresh.json",
              f"( cd {MROOT} && nohup {c.MAC_PY} {c.MAC_SRC}/mac_runner_r9.py --jobs jobs/v13fresh.json --state state/v13fresh "
              f"--workers 6 > ~/neurips/logs/structc_v13fresh.log 2>&1 < /dev/null & ) > /dev/null 2>&1", "echo STARTED"]
    try:
        c.ssh("bash -s", timeout=90, inp="\n".join(script).encode())
    except Exception:  # noqa: BLE001
        pass
    ok = b"RUNNING" in c.ssh("pgrep -f 'jobs/v13fresh.json' >/dev/null && echo RUNNING").stdout
    c.log(f"structHA: v13fresh Mac batch {'started' if ok else 'FAILED'}")
    c.enqueue(files)
    return 0 if ok else 1


def fetch() -> None:
    import io
    import tarfile
    try:
        r = c.ssh(f"cd {MROOT}/out/runs 2>/dev/null && find ./{VAR} ./{CHK} ./v13fresh -name summary.json 2>/dev/null | tar cf - -T - 2>/dev/null",
                  timeout=300)
    except Exception:  # noqa: BLE001
        return
    if not r.stdout:
        return
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            if m.isfile() and ".." not in Path(name).parts and Path(name).parts[0] in (VAR, CHK, "v13fresh"):
                dst = c.RUNS / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(tf.extractfile(m).read())


def summ(var: str, s: str) -> dict:
    out = {}
    for k in jobs_r6.scenarios(s):
        p = c.RUNS / var / s / k / "transfer" / "summary.json"
        if p.exists():
            d = json.loads(p.read_text())
            if d.get("total_steps") == 8640:
                out[k] = d
    return out


def decide() -> int:
    fetch()
    out = {"variant": VAR, "comparator": REF, "plan_sha256": "8b82778e477b768e"}
    # comparator validity
    chk, worst = {}, 0.0
    for s, ks in chk_keys().items():
        a, b = summ(CHK, s), summ(REF, s)
        for k in ks:
            if k in a and k in b:
                rel = abs(a[k]["avg_reward"] - b[k]["avg_reward"]) / abs(b[k]["avg_reward"])
                chk[f"{s}/{k}"] = rel
                worst = max(worst, rel)
    out["v13chk"] = {"n": len(chk), "max_rel_diff": worst, "valid": len(chk) == 6 and worst <= 1e-9}
    if REF == "v13fresh":   # the plan's fallback: comparator re-run in full, so the reuse check no longer applies
        out["v13chk"]["valid"] = True
        out["v13chk"]["note"] = "r12var reuse failed 1e-9 (pub30 denver_7 1.6e-9, Mac vs Kaggle); comparator = v13fresh"
    res = {}
    for s in ("r10hc", "r10hh", "pub30"):
        cand, ref = summ(VAR, s), summ(REF, s)
        keys = sorted(set(cand) & set(ref))
        res[s] = {"n": len(keys), "need": len(jobs_r6.scenarios(s)),
                  "r": np.array([abs(cand[k]["avg_reward"]) / abs(ref[k]["avg_reward"]) for k in keys]),
                  "reg": (np.mean([cand[k]["total_normalized_productivity_regret"] / 8640 for k in keys]) if keys else None,
                          np.mean([ref[k]["total_normalized_productivity_regret"] / 8640 for k in keys]) if keys else None)}
    out["n"] = {s: res[s]["n"] for s in res}
    complete = all(r["n"] == r["need"] for r in res.values())
    out["complete"] = complete
    hc, hh, pub = res["r10hc"]["r"], res["r10hh"]["r"], res["pub30"]["r"]
    if len(hc) and len(hh):
        rng = np.random.default_rng(20261107)
        boots = [rng.choice(hc, len(hc)).mean() / 3 + 2 * rng.choice(hh, len(hh)).mean() / 3 - 1 for _ in range(2000)]
        out.update({"mixture": hc.mean() / 3 + 2 * hh.mean() / 3 - 1, "mixture_ci": list(np.percentile(boots, [2.5, 97.5])),
                    "hc3": hc.mean() - 1, "hh": hh.mean() - 1, "hc3_wins": int((hc < 1).sum()), "hh_wins": int((hh < 1).sum())})
    if len(pub):
        out.update({"pub30": pub.mean() - 1, "pub30_wins": int((pub < 1).sum())})
    out["hh_regret_per_step"] = {"HA": res["r10hh"]["reg"][0], "v13": res["r10hh"]["reg"][1]}
    fr = json.loads((SR / "frost_hs18_HA.json").read_text())
    out["frost_source"] = fr
    if complete:
        a, b = fr["HA_hs18"], fr["v13ref_hs18"]
        g2 = bool(a["n"] == 18 and a["below5_share"] <= b["below5_share"] + 0.0025 and a["coldest_c"] >= b["coldest_c"] - 1.0)
        out["primary_pass"] = bool(out["mixture_ci"][1] < 0)
        out["guard1_pub30"] = bool(pub.mean() <= 1.0)
        out["guard2_frost"] = g2
        out["guard3_hh_comfort"] = bool(-out["hh_regret_per_step"]["HA"] <= -out["hh_regret_per_step"]["v13"])  # regret is stored negative
        out["ship"] = bool(out["v13chk"]["valid"] and out["primary_pass"] and out["guard1_pub30"] and g2
                           and out["guard3_hh_comfort"])
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit({"launch": launch, "launch_ref": launch_ref, "decide": decide}[sys.argv[1]]())
