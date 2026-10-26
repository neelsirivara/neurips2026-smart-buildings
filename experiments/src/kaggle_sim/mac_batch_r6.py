"""Round 6: build a Mac batch from (variant, set) specs in the Kaggle job format and launch it on the Mac.

    python mac_batch_r6.py --batch NAME --spec r6_comp:r6hs --spec r6_comp:pub30:PUB12+building_train_1/atlanta_2 \
        [--params-from r6_comp] [--skip-done] [--repro v8:pub30:building_train_8/fairbanks_8] [--no-launch]

spec = <variant>:<set>[:<scenario list, '+'-separated, or PUB12>]; parameters are policy_candidates/<variant>.json for
r6_* variants (v8/v7/pid_water use their frozen files, see jobs_r6.VARIANTS). --skip-done drops scenarios that already
have an 8,640-step summary under results/round6/runs/<variant>/<set>. Repro jobs are tagged macrepro/... so they never
overwrite a Kaggle or laptop run. Jobs are ordered longest first (per-building speed of jobs_r6.SPEED). The batch file is
written to results/round6/mac_jobs/<batch>.json, copied to ~/neurips/sb/r6/jobs/ (with every policy file it needs) and
started with mac_shard_runner_r6.py (global cap 8 simulator processes, memory guard 30%).
"""
from __future__ import annotations

import argparse
import json
import ntpath
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
sys.path.insert(0, str(SRC))
import jobs_r6  # noqa: E402
from compare_r6 import PUB12, runs  # noqa: E402

R6 = jobs_r6.R6
MJ = R6 / "mac_jobs"


def spec_jobs(spec: str, skip_done: bool) -> list[dict]:
    parts = spec.split(":")
    variant, set_name = parts[0], parts[1]
    only = None
    if len(parts) > 2 and parts[2]:
        only = []
        for x in parts[2].split("+"):
            only += PUB12 if x == "PUB12" else [x]
    params = None
    if variant.startswith("r6_"):
        params = str(SRC / "policy_candidates" / f"{variant}.json")
    keys = only or jobs_r6.scenarios(set_name)
    if skip_done:
        have = set(runs(variant, set_name))
        keys = [k for k in keys if k not in have]
    if not keys:
        return []
    files = jobs_r6.make(variant, set_name, params, False, 10_000, f"_mac_{variant}_{set_name}", keys, None)
    out = []
    for f in files:
        out += json.loads(f.read_text())
        f.unlink()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--spec", action="append", default=[])
    ap.add_argument("--repro", action="append", default=[])
    ap.add_argument("--skip-done", action="store_true")
    ap.add_argument("--no-launch", action="store_true")
    a = ap.parse_args()
    jobs = []
    for s in a.spec:
        jobs += spec_jobs(s, a.skip_done)
    rep = []
    for s in a.repro:
        for j in spec_jobs(s, False):
            j = dict(j)
            j["id"], j["tag"] = "macrepro/" + j["id"], "macrepro/" + j["tag"]
            rep.append(j)
    sp = jobs_r6.SPEED
    jobs.sort(key=lambda j: sp.get(j["building"], 0.3) * (3.0 if j["id"].startswith("v5/") else 1.0), reverse=True)
    allj = jobs + rep          # repro jobs are short: fill the tail
    MJ.mkdir(parents=True, exist_ok=True)
    bf = MJ / f"{a.batch}.json"
    bf.write_text(json.dumps(allj, indent=1))
    pols = sorted({j["policy_path"] for j in allj if j.get("policy_path")})
    print(f"{bf}: {len(jobs)} jobs + {len(rep)} repro; policies {[ntpath.basename(p) for p in pols]}")
    if a.no_launch:
        return 0
    for p in pols:
        subprocess.run(["scp", "-q", "-o", "BatchMode=yes", p, "mac:neurips/sb/r6/policies/"], check=True)
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", str(HERE / "mac_shard_runner_r6.py"), "mac:neurips/sb/r6/"],
                   check=True)
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", str(bf), "mac:neurips/sb/r6/jobs/"], check=True)
    cmd = (f"cd ~/neurips/sb/r6 && memory_pressure | tail -1 && nohup ~/neurips/sb/kit/.venv/bin/python -u "
           f"mac_shard_runner_r6.py --batch {a.batch} --jobs jobs/{a.batch}.json > out/{a.batch}.nohup.txt 2>&1 "
           f"< /dev/null & sleep 5; tail -3 out/{a.batch}/runner_log.txt")
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "mac", cmd], capture_output=True, text=True)
    print(r.stdout, r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
