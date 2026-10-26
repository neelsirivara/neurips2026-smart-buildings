"""Round 6: Kaggle competition probes of screened candidates (goal 3), one command per stage.

    python kaggle_probe_r6.py build  --cand r6_cXX [--label "SADR v9 cXX"]   # bake + one-cell notebook
    python kaggle_probe_r6.py push   --cand r6_cXX                           # kaggle kernels push (private, internet off)
    python kaggle_probe_r6.py check  --cand r6_cXX                           # wait, download log + parquet, compare atlanta_2
    python kaggle_probe_r6.py submit --cand r6_cXX                           # kaggle competitions submit + kaggle_feedback.json

The slug is sadr-v9-<cXX>-smart-buildings. The local reference total is the candidate's 8,640-step run of
building_train_1/atlanta_2 (results/round6/runs/<cand>/pub30/...); Kaggle's gateway runs 8,641 steps, so totals agree
to ~0.02% (round 5: 0.01%). A probe is submitted only if the check passes (< 0.1%). The daily limit is enforced from
kaggle_feedback.json -> daily_count_utc (3 more on 2026-10-26 UTC, 4 per later UTC day).
"""
from __future__ import annotations

import argparse
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
R6 = RES / "round6"
KAG = ROOT / "submission" / "kaggle"
FB = RES / "kaggle_feedback.json"
KAGGLE = Path.home() / ".kaggle-cli-venv" / "Scripts" / "kaggle.exe"
COMP = "neurips-2026-smart-buildings"
LIMIT = {"2026-10-26": 4}          # total per UTC day incl. the one already used on 10-26
DEFAULT_LIMIT = 4


def slug(cand: str) -> str:
    return f"sadr-v9-{cand.split('_')[1]}-smart-buildings"


def kag(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(KAGGLE), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def local_total(cand: str) -> float | None:
    f = R6 / "runs" / cand / "pub30" / "building_train_1" / "atlanta_2" / "transfer" / "summary.json"
    if not f.exists():
        return None
    s = json.loads(f.read_text())
    return s["total_reward"] if s["total_steps"] == 8640 else None


def build(cand: str, label: str | None) -> int:
    pol = R6 / "policies" / f"v9_{cand}.py"
    r = subprocess.call([sys.executable, str(HERE / "bake_candidate_r6.py"), cand, str(pol)])
    if r:
        return r
    lab = label or f"SADR v9 {cand.split('_')[1]}"
    return subprocess.call([sys.executable, str(HERE / "kaggle_build.py"), "--source", str(pol), "--slug", slug(cand),
                            "--title", f"SADR v9 {cand.split('_')[1]} Smart Buildings", "--label", lab])


def push(cand: str) -> int:
    r = kag("kernels", "push", "-p", str(KAG / slug(cand) / "push"))
    print(r.stdout, r.stderr)
    return 0 if (r.returncode == 0 and "error" not in (r.stdout + r.stderr).lower()) else 1


def check(cand: str, wait: bool = True) -> dict:
    s = slug(cand)
    while True:
        st = kag("kernels", "status", f"neelsiri/{s}").stdout
        if any(x in st for x in ("COMPLETE", "ERROR", "CANCEL")) or not wait:
            break
        time.sleep(60)
    out = KAG / s / "run_v1"
    out.mkdir(parents=True, exist_ok=True)
    kag("kernels", "output", f"neelsiri/{s}", "-p", str(out), "-o")
    tot = None
    for lf in out.glob("*.log"):
        m = re.findall(r"Total reward: \{'agent_0': (-?[0-9.eE+-]+)\}", lf.read_text(errors="replace"))
        if m:
            tot = float(m[-1])
    loc = local_total(cand)
    res = {"cand": cand, "slug": s, "status": st.strip(), "kaggle_atlanta_2_total": tot, "local_atlanta_2_total": loc,
           "rel_diff": (tot - loc) / abs(loc) if (tot is not None and loc) else None,
           "parquet": (out / "submission.parquet").exists()}
    res["ok"] = bool(res["parquet"] and res["rel_diff"] is not None and abs(res["rel_diff"]) < 1e-3)
    print(json.dumps(res, indent=1))
    (out / "check.json").write_text(json.dumps(res, indent=1))
    return res


def submit(cand: str, msg: str | None) -> int:
    chk = json.loads((KAG / slug(cand) / "run_v1" / "check.json").read_text())
    if not chk.get("ok"):
        print("check not passed; not submitting")
        return 1
    fb = json.loads(FB.read_text())
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    used = fb.get("daily_count_utc", {}).get(day, 0)
    if used >= LIMIT.get(day, DEFAULT_LIMIT):
        print(f"daily limit reached for {day} ({used})")
        return 1
    m = msg or f"SADR v9 {cand} (round-6 probe)"
    r = kag("competitions", "submit", COMP, "-k", f"neelsiri/{slug(cand)}", "-v", "1", "-f", "submission.parquet",
            "-m", m)
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
        "ref": int(ref) if ref and ref.isdigit() else ref, "round": 6,
        "submitted_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "submitted_utc_day": day,
        "label": cand, "policy": f"SADR v9 candidate {cand} (results/round6/policies/v9_{cand}.py), kernel neelsiri/{slug(cand)} v1",
        "kaggle_interactive_atlanta_2_total": chk["kaggle_atlanta_2_total"],
        "local_atlanta_2_total": chk["local_atlanta_2_total"], "push": "experiments/src/kaggle_probe_r6.py",
        "public_score": None})
    FB.write_text(json.dumps(fb, indent=1))
    print("logged", ref)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "push", "check", "submit"])
    ap.add_argument("--cand", required=True)
    ap.add_argument("--label")
    ap.add_argument("--msg")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()
    if a.cmd == "build":
        return build(a.cand, a.label)
    if a.cmd == "push":
        return push(a.cand)
    if a.cmd == "check":
        return 0 if check(a.cand, not a.no_wait).get("ok") else 1
    return submit(a.cand, a.msg)


if __name__ == "__main__":
    raise SystemExit(main())
