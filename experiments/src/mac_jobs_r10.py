"""Round 10: job files for mac_runner_r9.py (run_scenario.py on the Mac's r6 kit copy; results merged like Kaggle's).

    python mac_jobs_r10.py --variant r10_v11 --policy v11.py --sets r10dev --out ../results/round10/jobs/dev_a.json
    python mac_jobs_r10.py --variant r10_d_be --policy v12_r10.py --params d_be.json --sets r10dev \
        --only-r7hc dev6 --out ... [--append]
Policies live in ~/neurips/sb/r10/policies, parameter files in ~/neurips/sb/r10/params (copied there by hand, md5
checked). Results land on the Mac in ~/neurips/sb/r10/out/runs/<variant>/<set>/<b>/<w>/transfer/summary.json; fetch
them with fetch_mac_r10.sh into results/round6/runs/<variant>/<set>/ (compare_r10.py reads that tree).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import jobs_r6

MK = "/Users/neel.sirivara/neurips/sb/r6/sb/kit/smart_buildings"
PY = "/Users/neel.sirivara/neurips/sb/kit/.venv/bin/python"
R9 = "/Users/neel.sirivara/neurips/sb/r9"
R10 = "/Users/neel.sirivara/neurips/sb/r10"
# the six cold HC2 scenarios of the round-10 dev batch (HC2 is no longer a clean set; v11 runs exist)
DEV6 = ["building_train_1/denver_c3", "building_train_4/fairbanks_c4", "building_train_5/denver_c2",
        "building_train_7/minneapolis_c2", "building_train_8/fairbanks_c3", "building_train_8/minneapolis_c3"]
SPEED = dict(jobs_r6.SPEED)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--policy", required=True, help="file name in ~/neurips/sb/r10/policies")
    ap.add_argument("--params", default=None, help="file name in ~/neurips/sb/r10/params")
    ap.add_argument("--sets", nargs="*", default=[])
    ap.add_argument("--dev6", action="store_true", help="also the six cold HC2 dev scenarios (set r7hc)")
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these <b>/<w> keys")
    ap.add_argument("--out", required=True)
    ap.add_argument("--append", action="store_true")
    a = ap.parse_args()
    todo = [(s, k) for s in a.sets for k in jobs_r6.scenarios(s)]
    if a.dev6:
        todo += [("r7hc", k) for k in DEV6]
    if a.only is not None:
        todo = [(s, k) for s, k in todo if k in set(a.only)]
    jobs = []
    for s, k in todo:
        b, w = k.split("/")
        argv = [PY, f"{R9}/src/run_scenario.py", "--policy", "transfer", "--policy-file", f"{R10}/policies/{a.policy}",
                "--building", b, "--weather", w, "--steps", "8640",
                "--results-dir", f"{R10}/out/runs/{a.variant}/{s}", "--scenarios-dir", f"{MK}/{jobs_r6.SETS[s]}"]
        if a.params:
            argv[argv.index("--building"):argv.index("--building")] = ["--params-json", f"{R10}/params/{a.params}"]
        jobs.append({"id": f"{a.variant}__{s}__{b}__{w}", "cwd": R10, "argv": argv})
    out = Path(a.out)
    old = json.loads(out.read_text()) if a.append and out.exists() else []
    ids = {j["id"] for j in old}
    dup = [j["id"] for j in jobs if j["id"] in ids]
    if dup:
        raise SystemExit(f"duplicate job ids: {dup[:3]}")
    allj = old + jobs
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(allj, indent=1))
    print(out, f"+{len(jobs)} -> {len(allj)} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
