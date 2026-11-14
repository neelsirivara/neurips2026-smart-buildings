"""Round 13 (copy of kaggle_probe_r12.py for v13): a private Kaggle notebook of the v13 candidate (built, pushed and checked; the SUBMIT step is the
coordinator's decision and refuses to run unless SB_COORDINATOR_OK=1 is set).

    python kaggle_probe_r13.py build    # one-cell notebook from submission/candidates/transfer_policy_v13.py (v13, parameters baked)
    python kaggle_probe_r13.py push     # kaggle kernels push (private, internet off)
    python kaggle_probe_r13.py check    # wait, download log + parquet, compare building_train_1/atlanta_2 with local
    python kaggle_probe_r13.py submit   # kaggle competitions submit + kaggle_feedback.json (refuses unless check ok)

Slug sadr-v13-smart-buildings. Local reference total: r12var's 8,640-step run of
building_train_1/atlanta_2 (results/round6/runs/r12var/pub30/...; SADR reproduces across machines); the competition gateway runs 8,641 steps, so
totals agree to ~0.02%. No submission without the coordinator (round-9 instructions).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
KAG = ROOT / "submission" / "kaggle"
FB = RES / "kaggle_feedback.json"
KAGGLE = Path.home() / ".kaggle-cli-venv" / "Scripts" / "kaggle.exe"
COMP = "neurips-2026-smart-buildings"
SLUG = "sadr-v13-smart-buildings"
SHIP = ROOT / "submission" / "candidates" / "transfer_policy_v13.py"
LABEL = "v13_r12var"


def kag(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(KAGGLE), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def local_total() -> float | None:
    f = next((RES / "round6" / "runs" / "r12var" / "pub30" / "building_train_1" / "atlanta_2").rglob("summary.json"),
             None)
    if not f:
        return None
    s = json.loads(f.read_text())
    return s["total_reward"] if s["total_steps"] == 8640 else None


def build() -> int:
    return subprocess.call([sys.executable, str(HERE / "kaggle_build.py"), "--source", str(SHIP), "--slug", SLUG,
                            "--title", "SADR v13 Smart Buildings", "--label", "SADR v13"])


def push() -> int:
    meta = json.loads((KAG / SLUG / "push" / "kernel-metadata.json").read_text())
    if not meta.get("is_private") or meta.get("enable_internet"):
        raise SystemExit("kernel metadata must be private with internet off")
    r = kag("kernels", "push", "-p", str(KAG / SLUG / "push"))
    print(r.stdout, r.stderr)
    return 0 if (r.returncode == 0 and "error" not in (r.stdout + r.stderr).lower()) else 1


def check(wait: bool = True) -> dict:
    while True:
        st = kag("kernels", "status", f"neelsiri/{SLUG}").stdout
        if any(x in st for x in ("COMPLETE", "ERROR", "CANCEL")) or not wait:
            break
        time.sleep(60)
    out = KAG / SLUG / "run_v1"
    out.mkdir(parents=True, exist_ok=True)
    kag("kernels", "output", f"neelsiri/{SLUG}", "-p", str(out), "-o")
    tot = None
    for lf in out.glob("*.log"):
        m = re.findall(r"Total reward: \{'agent_0': (-?[0-9.eE+-]+)\}", lf.read_text(errors="replace"))
        if m:
            tot = float(m[-1])
    loc = local_total()
    res = {"slug": SLUG, "status": st.strip(), "kaggle_atlanta_2_total": tot, "local_atlanta_2_total": loc,
           "rel_diff": (tot - loc) / abs(loc) if (tot is not None and loc) else None,
           "parquet": (out / "submission.parquet").exists(),
           "shipped_sha256": hashlib.sha256(SHIP.read_bytes()).hexdigest()}
    res["ok"] = bool(res["parquet"] and res["rel_diff"] is not None and abs(res["rel_diff"]) < 1e-3)
    print(json.dumps(res, indent=1))
    (out / "check.json").write_text(json.dumps(res, indent=1))
    return res


def submit() -> int:
    import os
    if os.environ.get("SB_COORDINATOR_OK") != "1":
        print("submission is the coordinator's decision: set SB_COORDINATOR_OK=1 to submit")
        return 1
    chk = json.loads((KAG / SLUG / "run_v1" / "check.json").read_text())
    if not chk.get("ok"):
        print("check not passed; not submitting")
        return 1
    fb = json.loads(FB.read_text())
    if any(s.get("label") == LABEL for s in fb.get("submissions", [])):
        print("v13 was already probed")
        return 1
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    used = fb.get("daily_count_utc", {}).get(day, 0)
    if used >= 1:
        print(f"a probe was already submitted on {day}")
        return 1
    m = "SADR v13 r12var (round-13 probe)"
    r = kag("competitions", "submit", COMP, "-k", f"neelsiri/{SLUG}", "-v", "1", "-f", "submission.parquet", "-m", m)
    print(r.stdout, r.stderr)
    if r.returncode != 0 or "error" in (r.stdout + r.stderr).lower():
        return 1
    time.sleep(10)
    subs = kag("competitions", "submissions", COMP).stdout
    ref = None
    for line in subs.splitlines():
        if m[:30] in line:
            ref = line.split()[0]
            break
    fb.setdefault("daily_count_utc", {})[day] = used + 1
    fb.setdefault("submissions", []).append({
        "ref": int(ref) if ref and ref.isdigit() else ref, "round": 13,
        "submitted_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "submitted_utc_day": day,
        "label": LABEL, "policy": f"SADR v13 = r12var, submission/candidates/transfer_policy_v13.py (sha256 {chk['shipped_sha256']}), "
                                  f"kernel neelsiri/{SLUG} v1",
        "kaggle_interactive_atlanta_2_total": chk["kaggle_atlanta_2_total"],
        "local_atlanta_2_total": chk["local_atlanta_2_total"], "push": "experiments/src/kaggle_probe_r13.py",
        "public_score": None})
    FB.write_text(json.dumps(fb, indent=1))
    print("logged", ref)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "push", "check", "submit"])
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()
    if a.cmd == "build":
        return build()
    if a.cmd == "push":
        return push()
    if a.cmd == "check":
        return 0 if check(not a.no_wait).get("ok") else 1
    return submit()


if __name__ == "__main__":
    raise SystemExit(main())
