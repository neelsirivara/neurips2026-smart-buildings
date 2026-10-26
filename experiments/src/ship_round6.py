"""Ship the round-6 candidate that met the pre-registered rule (PREREG round 6): results/round6/policies/v9_screen2.py
(the frozen code every round-6 run used) + <candidate>.json -> submission/transfer_policy.py (DEFAULT_PARAMS baked),
results/tune/best_params.json (+ best_params_v9.json; v8's set kept as best_params_v8.json), the shipped v8 file kept
as submission/transfer_policy_v8_shipped_before_round6.py; then bake check, robustness test and a 36-step smoke run.

Usage:  python ship_round6.py r6_cXX_...
"""
from __future__ import annotations

import importlib.util
import json
import re
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
    src = RES / "round6" / "policies" / "v9_screen2.py"
    overrides = json.loads((HERE / "policy_candidates" / f"{cand}.json").read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = ROOT / "submission" / "transfer_policy_v8_shipped_before_round6.py"
    if not keep.exists():
        shutil.copy(dst, keep)
    text = src.read_text(encoding="utf-8")
    old_head = "for the SB26 challenge (v9 candidate code, round 6)."
    assert old_head in text, "v9 header not found"
    text = text.replace(old_head, f"for the SB26 challenge (v9, final; round 6, {cand}).", 1)
    over = ", ".join(f"{k} {v:g}" for k, v in overrides.items())
    old_doc = "Round-6 switches (all off by default, which reproduces v8 bit for bit):"
    assert old_doc in text, "v9 docstring paragraph not found"
    text = text.replace(old_doc, f"v9 turns on the overrides of {cand} in DEFAULT_PARAMS ({over}). The round-6 switches "
                                 "(all off reproduces v8 bit for bit):", 1)
    for k, v in overrides.items():          # bake: same rule as bake_params.py / bake_candidate_r6.py
        pat = re.compile(r'^(\s*"' + re.escape(k) + r'":\s*)([^,]+)(,.*)$', re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"key {k} not found exactly once in DEFAULT_PARAMS")
        text = pat.sub(lambda m: m.group(1) + repr(float(v)) + m.group(3), text, count=1)
    dst.write_text(text, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("v9_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update({k: float(v) for k, v in overrides.items()})
    spec2 = importlib.util.spec_from_file_location("v9_dst", dst)
    mod2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    bad = {k for k in params if params[k] != mod2.DEFAULT_PARAMS.get(k)}
    if bad:
        raise SystemExit(f"bake mismatch: {sorted(bad)}")
    tune = RES / "tune"
    if not (tune / "best_params_v8.json").exists():
        shutil.copy(tune / "best_params.json", tune / "best_params_v8.json")
    (tune / "best_params_v9.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    shutil.copy(tune / "best_params.json", ROOT / "submission" / "best_params.json")
    print(f"wrote {dst} (from {src.name} + {cand}.json) and {tune / 'best_params.json'}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    tpl.write_text(tpl.read_text().replace("SADR policy (v8, final; round 5).", "SADR policy (v9, final; round 6)."))
    for cmd in ([PY, str(HERE / "test_policy_robustness.py"), str(dst)],
                [PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                 "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(RES / "round6" / "smoke_shipped"),
                 "--force"]):
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        print(" ".join(Path(c).name for c in cmd[1:3]), "rc", rc)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
