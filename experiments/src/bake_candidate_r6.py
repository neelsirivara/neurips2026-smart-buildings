"""Write a self-contained policy file for a round-6 candidate (v9 code with the candidate's overrides baked into
DEFAULT_PARAMS) without touching submission/, e.g. for a Kaggle probe of a candidate that is not (yet) shipped.

The overrides are written into the DEFAULT_PARAMS literal line by line (same rule as bake_params.py); the script
then imports the result and checks that DEFAULT_PARAMS equals v9 defaults + overrides.

    python bake_candidate_r6.py r6_cXX out.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_params(path: Path) -> dict:
    spec = importlib.util.spec_from_file_location(f"m_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.DEFAULT_PARAMS)


def main() -> int:
    cand, out = sys.argv[1], Path(sys.argv[2])
    src = HERE.parent / "results" / "round6" / "policies" / "v9_screen2.py"  # frozen screen code (+ sb_boost_cold, off by default)
    over = json.loads((HERE / "policy_candidates" / f"{cand}.json").read_text())
    text = src.read_text(encoding="utf-8")
    for k, v in over.items():
        pat = re.compile(r'^(\s*"' + re.escape(k) + r'":\s*)([^,]+)(,.*)$', re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"key {k} not found exactly once in DEFAULT_PARAMS")
        text = pat.sub(lambda m: m.group(1) + repr(float(v)) + m.group(3), text, count=1)
    text = text.replace("for the SB26 challenge (v9 candidate code, round 6).",
                        f"for the SB26 challenge (v9 candidate {cand} baked, round 6).", 1)
    out.write_text(text, encoding="utf-8", newline="\n")
    want = load_params(src)
    want.update({k: float(v) for k, v in over.items()})
    got = load_params(out)
    bad = {k for k in want if want[k] != got.get(k)}
    print(f"wrote {out}; mismatches after bake: {sorted(bad) if bad else 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
