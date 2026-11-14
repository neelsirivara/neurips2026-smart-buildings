"""Ship the round-10 candidate if it met the pre-registered rule (results/round10/PREREG.md).

frozen code (results/round10/policies/v12d_r10.py) + params (results/round10/params/<cand>.json) ->
submission/transfer_policy.py (v12; DEFAULT_PARAMS baked), v11 kept as
submission/transfer_policy_v11_shipped_before_round10.py (v10 / v9 / v8 copies untouched),
results/tune/best_params.json (+ best_params_v12.json; v11's stays as best_params_v11.json), submission/best_params.json,
notebook template header; then bake check, robustness test and a 36-step smoke run. Refuses unless
results/round10/confirm_<cand>.json says the rule is met and the frozen files still have their registered hashes.

    python ship_round10.py --cand <cand>
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
R10 = RES / "round10"
PY = sys.executable
CODE = R10 / "policies" / "v12d_r10.py"   # frozen v12 code (make_v12_r10.py), registered in PREREG Part 2
CODE_SHA = "b31da04d53c61a713255dd5ae84cd140a25331a181e2b975b9f49f22c02b25eb"
V11_SHA = "f9c0ad1a3be0a3983905b434a91fa7f9eca6b4fd7de1957d9c87355fc2ddb8d8"
REG_FILE = R10 / "registered.json"   # candidate -> params sha256, written with PREREG Part 2


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    a = ap.parse_args()
    reg = json.loads(REG_FILE.read_text())
    if a.cand not in reg["candidates"]:
        raise SystemExit(f"{a.cand} is not registered: {sorted(reg['candidates'])}")
    conf = json.loads((R10 / f"confirm_{a.cand}.json").read_text())
    if not (conf.get("rule") or {}).get("met"):
        raise SystemExit(f"rule not met: {conf.get('rule')}; nothing shipped")
    pfile = R10 / "params" / f"{a.cand}.json"
    if sha(CODE) != CODE_SHA or sha(pfile) != reg["candidates"][a.cand]["params_sha256"]:
        raise SystemExit("frozen code or parameters changed since PREREG round 10")
    dst = ROOT / "submission" / "transfer_policy.py"
    keep = ROOT / "submission" / "transfer_policy_v11_shipped_before_round10.py"
    if not keep.exists():
        if sha(dst) != V11_SHA:
            raise SystemExit("submission/transfer_policy.py is not the shipped v11")
        shutil.copy(dst, keep)
    overrides = json.loads(pfile.read_text())
    text = CODE.read_text(encoding="utf-8")
    old_head = ("for the SB26 challenge (v12 candidate code, round 10;\nall round-10 switches off = v11, round 9, "
                "r9_dow).")
    assert old_head in text, "v12 header not found"
    over = ", ".join(f"{k} {v:g}" for k, v in overrides.items())
    text = text.replace(old_head, f"for the SB26 challenge (v12, final; round 10, {a.cand}:\n{over} on top of v11; "
                                  "every other round-10 switch off).", 1)
    for k, v in overrides.items():
        pat = re.compile(r'^(\s*"' + re.escape(k) + r'":\s*)([^,]+)(,.*)$', re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"key {k} not found exactly once in DEFAULT_PARAMS")
        text = pat.sub(lambda m: m.group(1) + repr(float(v)) + m.group(3), text, count=1)
    dst.write_text(text, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location("v12_src", CODE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    params = dict(mod.DEFAULT_PARAMS)
    params.update({k: float(v) for k, v in overrides.items()})
    spec2 = importlib.util.spec_from_file_location("v12_dst", dst)
    mod2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    bad = {k for k in params if params[k] != mod2.DEFAULT_PARAMS.get(k)}
    if bad or set(params) != set(mod2.DEFAULT_PARAMS):
        raise SystemExit(f"bake mismatch: {sorted(bad)}")
    tune = RES / "tune"
    if not (tune / "best_params_v11.json").exists():
        shutil.copy(tune / "best_params.json", tune / "best_params_v11.json")
    (tune / "best_params_v12.json").write_text(json.dumps(params, indent=1))
    (tune / "best_params.json").write_text(json.dumps(params, indent=1))
    shutil.copy(tune / "best_params.json", ROOT / "submission" / "best_params.json")
    print(f"wrote {dst} (from {CODE.name} + {pfile.name}), md5 {hashlib.md5(dst.read_bytes()).hexdigest()}, "
          f"sha256 {sha(dst)}")
    tpl = ROOT / "submission" / "kaggle_notebook_template.py"
    t = tpl.read_text()
    if "SADR policy (v11, final; round 9)." in t:
        tpl.write_text(t.replace("SADR policy (v11, final; round 9).", "SADR policy (v12, final; round 10)."))
    for cmd in ([PY, str(HERE / "test_policy_robustness.py"), str(dst)],
                [PY, str(HERE / "run_scenario.py"), "--policy", "transfer", "--building", "building_train_8",
                 "--weather", "fairbanks_8", "--steps", "36", "--results-dir", str(R10 / "smoke_shipped"), "--force"]):
        rc = subprocess.run(cmd, cwd=str(HERE)).returncode
        print(" ".join(Path(c).name for c in cmd[1:3]), "rc", rc)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
