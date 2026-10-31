"""Ship round 8's candidate if it met the pre-registered rule (results/round8/PREREG.md): the frozen code every
round-8 run used, results/round6/policies/v10b_screen.py, + policy_candidates/r7L_mbr2.json -> submission/
transfer_policy.py (DEFAULT_PARAMS baked; v10), results/tune/best_params.json (+ best_params_v10.json; v9's set kept as
best_params_v9.json), the shipped v9 file kept as submission/transfer_policy_v9_shipped_before_round8.py; then bake
check, robustness test and a 36-step smoke run. Refuses to run unless results/round8/confirm_r7L_mbr2.json says the
rule is met.

Usage:  python ship_round8.py
"""
from __future__ import annotations

import hashlib
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
CAND = "r7L_mbr2"
SRC_SHA = "2827a88af85a63e84a668099689a277c7cb7c285b13cfd15ab5ddf8ac811f931"
PAR_SHA = "79857dd13b2ed8beb935bf5fd58d3b5307b02a21025dff26564fe21d42277bbe"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    conf = json.loads((RES / "round8" / f"confirm_{CAND}.json").read_text())
    if not (conf.get("rule") or {}).get("met"):
        raise SystemExit(f"rule not met: {conf.get('rule')}; nothing shipped")
    src = RES / "round6" / "policies" / "v10b_screen.py"
    pfile = HERE / "policy_candidates" / f"{CAND}.json"
    if sha(src) != SRC_SHA or sha(pfile) != PAR_SHA:
        raise SystemExit("frozen code or parameters changed since PREREG round 8")
    overrides = json.loads(pfile.read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = ROOT / "submission" / "transfer_policy_v9_shipped_before_round8.py"
    if not keep.exists():
        shutil.copy(dst, keep)
    text = src.read_text(encoding="utf-8")
    old_head = "for the SB26 challenge (v10 candidate code, round 7)."
    assert old_head in text, "v10 header not found"
    text = text.replace(old_head, f"for the SB26 challenge (v10, final; round 8, {CAND}).", 1)
    over = ", ".join(f"{k} {v:g}" for k, v in overrides.items())
    old_doc = "Round-7 switches (all off by default, which reproduces the v9 code bit for bit):"
    assert old_doc in text, "v10 docstring paragraph not found"
    text = text.replace(old_doc, f"v10 turns on the overrides of {CAND} in DEFAULT_PARAMS ({over}); with "
                                 "``mbr_lead_cap`` the model may only shorten the learned-rate lead and is ignored "
                                 "where it predicts the target is unreachable at the cap. Round-7 switches (all off "
                                 "reproduces the v9 code bit for bit):", 1)
    for k, v in overrides.items():          # bake: same rule as ship_round6.py
        pat = re.compile(r'^(\s*"' + re.escape(k) + r'":\s*)([^,]+)(,.*)$', re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"key {k} not found exactly once in DEFAULT_PARAMS")
        text = pat.sub(lambda m: m.group(1) + repr(float(v)) + m.group(3), text, count=1)
    dst.write_text(text, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("v10_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update({k: float(v) for k, v in overrides.items()})
    spec2 = importlib.util.spec_from_file_location("v10_dst", dst)
    mod2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    bad = {k for k in params if params[k] != mod2.DEFAULT_PARAMS.get(k)}
    if bad:
        raise SystemExit(f"bake mismatch: {sorted(bad)}")
    tune = RES / "tune"
    if not (tune / "best_params_v9.json").exists():
        shutil.copy(tune / "best_params.json", tune / "best_params_v9.json")
    (tune / "best_params_v10.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    shutil.copy(tune / "best_params.json", ROOT / "submission" / "best_params.json")
    print(f"wrote {dst} (from {src.name} + {CAND}.json) and {tune / 'best_params.json'}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    tpl.write_text(tpl.read_text().replace("SADR policy (v9, final; round 6).", "SADR policy (v10, final; round 8)."))
    for cmd in ([PY, str(HERE / "test_policy_robustness.py"), str(dst)],
                [PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                 "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(RES / "round8" / "smoke_shipped"),
                 "--force"]):
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        print(" ".join(Path(c).name for c in cmd[1:3]), "rc", rc)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
