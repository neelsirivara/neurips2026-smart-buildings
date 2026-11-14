"""Round 9: job files for mac_runner_r9.py (run_scenario.py on the Mac's r6 kit copy, results merged like Kaggle's).

    python mac_jobs_r9.py --variant r9_hwl --policy v11_screen.py --params r9_hwl.json --sets r7hc r5m r4c \
        --out ../results/round9/jobs/mac_r9hwl_confirm.json
Results land on the Mac in ~/neurips/sb/r9/out/runs/<variant>/<set>/<b>/<w>/transfer/summary.json; fetch with
fetch_mac_r9.sh runs, then copy into results/round6/runs/<variant>/<set>/ (compare_r9.py reads that tree).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import jobs_r6

MK = "/Users/neel.sirivara/neurips/sb/r6/sb/kit/smart_buildings"
PY = "/Users/neel.sirivara/neurips/sb/kit/.venv/bin/python"
R9 = "/Users/neel.sirivara/neurips/sb/r9"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--policy", required=True, help="file name in ~/neurips/sb/r9/policies")
    ap.add_argument("--params", required=True, help="file name in ~/neurips/sb/r9/params")
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    jobs = []
    for s in a.sets:
        for k in jobs_r6.scenarios(s):
            b, w = k.split("/")
            jobs.append({"id": f"{a.variant}__{s}__{b}__{w}", "cwd": R9,
                         "argv": [PY, f"{R9}/src/run_scenario.py", "--policy", "transfer",
                                  "--policy-file", f"{R9}/policies/{a.policy}", "--params-json", f"{R9}/params/{a.params}",
                                  "--building", b, "--weather", w, "--steps", "8640",
                                  "--results-dir", f"{R9}/out/runs/{a.variant}/{s}",
                                  "--scenarios-dir", f"{MK}/{jobs_r6.SETS[s]}"]})
    # slow buildings first
    jobs.sort(key=lambda j: -jobs_r6.SPEED.get(j["argv"][j["argv"].index("--building") + 1], 0.3))
    Path(a.out).write_text(json.dumps(jobs, indent=1))
    print(a.out, len(jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
