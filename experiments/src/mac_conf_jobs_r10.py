"""Round 10 (runs on the Mac, so the laptop stays idle): job files for the frozen candidate r10_K.

    python mac_conf_jobs_r10.py devcheck     # r10_K on the six cold HC2 dev scenarios (development only)
    python mac_conf_jobs_r10.py confirm      # v11 + r10_K on HC3 and HH (interleaved), then r10_K on P, HS, M, FD

Scenario lists come from the Mac's r6 kit copy; `confirm` refuses unless the counts are 40 / 40 / 30 / 18 / 12 / 20,
the P / HS / M / FD keys equal v11's run keys (r9_dow), and no run of any policy exists yet on HC3 or HH.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

H = Path.home() / "neurips" / "sb"
R10 = H / "r10"
MK = H / "r6" / "sb" / "kit" / "smart_buildings"
PY = str(H / "kit" / ".venv" / "bin" / "python")
RUNNER = str(H / "r9" / "src" / "run_scenario.py")
SETS = {"r10hc": "heldout_scenarios_r10hc", "r10hh": "heldout_scenarios_r10hh", "pub30": "training_scenarios",
        "r6hs": "heldout_scenarios_r6hs", "r5m": "heldout_scenarios_r5m", "r4c": "heldout_scenarios_r4c",
        "r7hc": "heldout_scenarios_r7hc"}
FD_B = ("building_0604", "building_0607", "building_0610", "building_0639")
DEV6 = ["building_train_1/denver_c3", "building_train_4/fairbanks_c4", "building_train_5/denver_c2",
        "building_train_7/minneapolis_c2", "building_train_8/fairbanks_c3", "building_train_8/minneapolis_c3"]
NEED = {"r10hc": 40, "r10hh": 40, "pub30": 30, "r6hs": 18, "r5m": 12, "r4c": 20}


def keys(s: str) -> list[str]:
    d = MK / SETS[s]
    out = [f"{b.name}/{w.name}" for b in sorted(d.iterdir()) if b.is_dir() for w in sorted(b.iterdir())
           if (w / "config.gin").exists()]
    return [k for k in out if k.split("/")[0] in FD_B] if s == "r4c" else out


def job(variant: str, policy: str, params: str | None, s: str, k: str) -> dict:
    b, w = k.split("/")
    argv = [PY, RUNNER, "--policy", "transfer", "--policy-file", str(R10 / "policies" / policy)]
    if params:
        argv += ["--params-json", str(R10 / "params" / params)]
    argv += ["--building", b, "--weather", w, "--steps", "8640", "--results-dir",
             str(R10 / "out" / "runs" / variant / s), "--scenarios-dir", str(MK / SETS[s])]
    return {"id": f"{variant}__{s}__{b}__{w}", "cwd": str(R10), "argv": argv}


def main() -> int:
    v11 = ("r10_v11", "v11.py", None)
    cand = ("r10_K", "v12d_r10.py", "r10_K.json")
    if sys.argv[1] == "devcheck":
        jobs = [job(*cand, "r7hc", k) for k in DEV6]
        out = R10 / "jobs" / "devcheck_K.json"
    else:
        an = R10 / "an" / "results" / "round6" / "runs" / "r9_dow"
        for s, n in NEED.items():
            ks = keys(s)
            if len(ks) != n:
                raise SystemExit(f"{s}: {len(ks)} scenarios, expected {n}")
            if s in ("pub30", "r6hs", "r5m", "r4c"):
                have = sorted(f"{p.parts[-4]}/{p.parts[-3]}" for p in (an / s).glob("*/*/transfer/summary.json"))
                if s == "r4c":
                    have = [k for k in have if k.split("/")[0] in FD_B]
                if have != sorted(ks):
                    raise SystemExit(f"{s}: keys differ from v11's runs")
        for s in ("r10hc", "r10hh"):
            seen = list((R10 / "out" / "runs").glob(f"*/{s}/*/*/transfer/summary.json"))
            if seen:
                raise SystemExit(f"{s} already has {len(seen)} runs")
        jobs = []
        for s in ("r10hc", "r10hh"):
            for k in keys(s):
                jobs += [job(*v11, s, k), job(*cand, s, k)]
        for s in ("pub30", "r6hs", "r5m", "r4c"):
            jobs += [job(*cand, s, k) for k in keys(s)]
        out = R10 / "jobs" / "confirm_K.json"
    assert len({j["id"] for j in jobs}) == len(jobs)
    out.write_text(json.dumps(jobs, indent=1))
    print(out, len(jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
