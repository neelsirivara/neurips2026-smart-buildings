"""Ship the round-5 candidate that met the pre-registered rule: policy_candidates/transfer_policy_v8.py +
<candidate>.json -> submission/transfer_policy.py (DEFAULT_PARAMS baked), results/tune/best_params.json
(+ best_params_v8.json; the v7 set stays in best_params_v7.json), the shipped v7 file kept as
results/round5/transfer_policy_v7_shipped_before_round5.py; then bake check, robustness test and a 36-step smoke run.

Usage:  python ship_round5.py r5_cXX_...
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
    src = HERE / "policy_candidates" / "transfer_policy_v8.py"
    overrides = json.loads((HERE / "policy_candidates" / f"{cand}.json").read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = RES / "round5" / "transfer_policy_v7_shipped_before_round5.py"
    if not keep.exists():
        shutil.copy(dst, keep)
    text = src.read_text(encoding="utf-8")
    old_head = "for the SB26 challenge (v8 candidate code, round 5)."
    assert old_head in text, "v8 header not found"
    text = text.replace(old_head, f"for the SB26 challenge (v8, final; round 5, {cand}).", 1)
    over = ", ".join(f"{k} {v:g}" for k, v in overrides.items())
    old_doc = "Round 5 adds switches that all default to off (with them off the code reproduces v7 bit for bit):"
    assert old_doc in text, "v8 docstring paragraph not found"
    text = text.replace(old_doc, f"v8 turns on the overrides of {cand} in DEFAULT_PARAMS ({over}); the round-5 "
                                 "switches (with them off the code reproduces v7 bit for bit) are:", 1)
    dst.write_text(text, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("v8_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update(overrides)
    tune = RES / "tune"
    if not (tune / "best_params_v7.json").exists():
        shutil.copy(tune / "best_params.json", tune / "best_params_v7.json")
    (tune / "best_params_v8.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    print(f"wrote {dst} (from {src.name} + {cand}.json) and {tune / 'best_params.json'}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    tpl.write_text(tpl.read_text().replace("SADR policy (v7, final; round 4).", "SADR policy (v8, final; round 5)."))
    for cmd in ([PY, str(HERE / "bake_params.py"), str(tune / "best_params.json")],
                [PY, str(HERE / "test_policy_robustness.py"), str(dst)],
                [PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                 "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(RES / "round5" / "smoke_shipped"),
                 "--force"]):
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        print(" ".join(Path(c).name for c in cmd[1:3]), "rc", rc)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
