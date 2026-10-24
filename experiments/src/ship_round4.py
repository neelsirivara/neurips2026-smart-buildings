"""Ship the round-4 candidate that met the pre-registered rule: policy_candidates/transfer_policy_v7.py +
<candidate>.json -> submission/transfer_policy.py (DEFAULT_PARAMS baked), results/tune/best_params.json
(+ best_params_v7.json; the v6 set stays in best_params_v6.json), the shipped v6 file kept as
results/round4/transfer_policy_v6_shipped_before_round4.py; then the robustness test and a 36-step smoke
run of the baked file.

Usage:  python ship_round4.py r4_cXX_...
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
    cand = sys.argv[1]
    src = HERE / "policy_candidates" / "transfer_policy_v7.py"
    overrides = json.loads((HERE / "policy_candidates" / f"{cand}.json").read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = RES / "round4" / "transfer_policy_v6_shipped_before_round4.py"
    if not keep.exists():
        shutil.copy(dst, keep)
    text = src.read_text()
    text = text.replace("for the SB26 challenge (v7 candidate, round 4).", f"for the SB26 challenge (v7, final; round 4, {cand}).", 1)
    old_doc = ("Round-4 candidate switches (all off by default, so the defaults reproduce the shipped v6\n"
               "bit for bit):")
    new_doc = ("Round-4 switches (v7 turns on the five overrides of " + cand + " in DEFAULT_PARAMS:\n"
               "disch_margin_k 0, occ_press_dyn with e0 0.1 K / span 0.5 K, flush_on + flush_heat_guard,\n"
               "sb_neutral, f_cap_pre 0.316; with all of them off the code reproduces v6 bit for bit). Switches:")
    assert old_doc in text, "docstring paragraph not found"
    text = text.replace(old_doc, new_doc, 1)
    dst.write_text(text)
    spec = importlib.util.spec_from_file_location("v7_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update(overrides)
    tune = RES / "tune"
    (tune / "best_params_v7.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    print(f"wrote {dst} (from {src.name} + {cand}.json) and {tune / 'best_params.json'}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    tpl.write_text(tpl.read_text().replace("SADR policy (v6, final; round 3).", "SADR policy (v7, final; round 4)."))
    rc = subprocess.run([PY, str(HERE / "bake_params.py"), str(tune / "best_params.json")], cwd=str(HERE)).returncode
    if rc:
        return rc
    rc = subprocess.run([PY, str(HERE / "test_policy_robustness.py"), str(dst)], cwd=str(HERE)).returncode
    if rc:
        return rc
    rc = subprocess.run([PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                         "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(RES / "round4" / "smoke_shipped"),
                         "--force"], cwd=str(HERE)).returncode
    print("smoke run rc", rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
