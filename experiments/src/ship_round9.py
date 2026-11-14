"""Ship a round-9 candidate if it met the pre-registered rule (results/round9/PREREG.md).

frozen code (results/round9/policies/<code>) + params (results/round9/params/<cand>.json) -> submission/transfer_policy.py
(v11; DEFAULT_PARAMS baked), v10 kept as submission/transfer_policy_v10_shipped_before_round9.py (v9 / v8 copies
untouched), results/tune/best_params.json (+ best_params_v11.json; v10's kept as best_params_v10.json), notebook template
header; then bake check, robustness test and a 36-step smoke run.  Refuses unless results/round9/confirm_<cand>.json
says the rule is met and the frozen files still have their registered hashes.

    python ship_round9.py --cand r9_dow
"""
from __future__ import annotations

import argparse
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
R9 = RES / "round9"
PY = sys.executable
REG = {  # candidate -> (frozen code, code sha256, params sha256), as registered in PREREG round 9
    "r9_dow": ("v11d_screen.py", "88e92f969033e4c6bce07c91a133c610e1a5d6161e492ed266ece47e3c86f179",
               "14b9c2c47a25796788888ed846bbca343e9c81cde52a7f3b1d8431d006ca4e61"),
    "r9_hwl": ("v11_screen.py", "c3a58277340bf718fc577b5030f8b3775eafe1ce50d1cfad5f04fbc271eb106b",
               "8196ac2e478a7b9b8843c64baa8067d621eedc58a2b30bf1e2d8c5fee2c5c6d5"),
    "r9_mprs": ("v11c_screen.py", "1ce2157d0f56cbce047e9ea992526f9bdce6651dd93b43a15207b95c8a259ca2",
                "4afbab26765b5f6000f797e3ddf07f624870dc4a809a5b7077321be44a2273b6"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="r9_dow", choices=sorted(REG))
    a = ap.parse_args()
    conf = json.loads((R9 / f"confirm_{a.cand}.json").read_text())
    if not (conf.get("rule") or {}).get("met"):
        raise SystemExit(f"rule not met: {conf.get('rule')}; nothing shipped")
    code, csha, psha = REG[a.cand]
    src = R9 / "policies" / code
    pfile = R9 / "params" / f"{a.cand}.json"
    if sha(src) != csha or sha(pfile) != psha:
        raise SystemExit("frozen code or parameters changed since PREREG round 9")
    overrides = json.loads(pfile.read_text())
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = ROOT / "submission" / "transfer_policy_v10_shipped_before_round9.py"
    if not keep.exists():
        shutil.copy(dst, keep)
    text = src.read_text(encoding="utf-8")
    old_head = ("for the SB26 challenge (v11 candidate code, round 9;\nall round-9 switches off = v10, round 8, "
                "r7L_mbr2).")
    assert old_head in text, "v11 header not found"
    over = ", ".join(f"{k} {v:g}" for k, v in overrides.items())
    text = text.replace(old_head, f"for the SB26 challenge (v11, final; round 9, {a.cand}:\n{over} on top of v10; "
                                  "every other round-9 switch off).", 1)
    for k, v in overrides.items():
        pat = re.compile(r'^(\s*"' + re.escape(k) + r'":\s*)([^,]+)(,.*)$', re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"key {k} not found exactly once in DEFAULT_PARAMS")
        text = pat.sub(lambda m: m.group(1) + repr(float(v)) + m.group(3), text, count=1)
    dst.write_text(text, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("v11_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update({k: float(v) for k, v in overrides.items()})
    spec2 = importlib.util.spec_from_file_location("v11_dst", dst)
    mod2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    bad = {k for k in params if params[k] != mod2.DEFAULT_PARAMS.get(k)}
    if bad:
        raise SystemExit(f"bake mismatch: {sorted(bad)}")
    tune = RES / "tune"
    if not (tune / "best_params_v10.json").exists():
        shutil.copy(tune / "best_params.json", tune / "best_params_v10.json")
    (tune / "best_params_v11.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    shutil.copy(tune / "best_params.json", ROOT / "submission" / "best_params.json")
    print(f"wrote {dst} (from {src.name} + {pfile.name}), md5 {hashlib.md5(dst.read_bytes()).hexdigest()}, "
          f"sha256 {sha(dst)}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    t = tpl.read_text()
    if "SADR policy (v10, final; round 8)." in t:
        tpl.write_text(t.replace("SADR policy (v10, final; round 8).", "SADR policy (v11, final; round 9)."))
    for cmd in ([PY, str(HERE / "test_policy_robustness.py"), str(dst)],
                [PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                 "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(R9 / "smoke_shipped"), "--force"]):
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        print(" ".join(Path(c).name for c in cmd[1:3]), "rc", rc)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
