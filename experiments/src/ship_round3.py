"""Ship the chosen round-3 variant: policy_candidates/transfer_policy_v6.py + <candidate>.json ->
submission/transfer_policy.py (DEFAULT_PARAMS baked), results/tune/best_params.json (+ the v5 set
kept as best_params_v5.json), then the robustness test and a 36-step smoke run of the baked file.

Usage:  python ship_round3.py r3_c00_v6_default
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
PY = sys.executable


def main() -> int:
    cand = sys.argv[1] if len(sys.argv) > 1 else "r3_c00_v6_default"
    src = HERE / "policy_candidates" / "transfer_policy_v6.py"
    overrides = json.loads((HERE / "policy_candidates" / f"{cand}.json").read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    text = src.read_text()
    text = text.replace('for the SB26 challenge (v6 candidate).', f'for the SB26 challenge (v6, final; round 3, {cand}).', 1)
    dst.write_text(text)
    # full parameter set = v6 defaults + the candidate's overrides
    spec = importlib.util.spec_from_file_location("v6_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update(overrides)
    tune = RES / "tune"
    v5 = tune / "best_params.json"
    if v5.exists() and not (tune / "best_params_v5.json").exists():
        shutil.copy(v5, tune / "best_params_v5.json")
    (tune / "best_params_v6.json").write_text(json.dumps(params, indent=1))
    v5.write_text(json.dumps(params, indent=1))
    print(f"wrote {dst} (from {src.name} + {cand}.json) and {tune / 'best_params.json'}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    tt = tpl.read_text().replace("SADR policy (v5, final).", "SADR policy (v6, final; round 3).")
    tpl.write_text(tt)
    rc = subprocess.run([PY, str(HERE / "bake_params.py"), str(v5)], cwd=str(HERE)).returncode
    if rc:
        return rc
    rc = subprocess.run([PY, str(HERE / "test_policy_robustness.py"), str(dst)], cwd=str(HERE)).returncode
    if rc:
        return rc
    rc = subprocess.run([PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                         "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(RES / "round3" / "smoke_shipped"),
                         "--force"], cwd=str(HERE)).returncode
    print("smoke run rc", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
