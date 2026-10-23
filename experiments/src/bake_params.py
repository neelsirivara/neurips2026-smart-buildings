"""Bake tuned parameters into submission/transfer_policy.py's DEFAULT_PARAMS.

The shipped policy must not read any file, so the tuned values are written into
the source dictionary literal (one key per line, value replaced in place; the
comment on the line is kept). A copy of the tuned JSON is stored next to the
policy as best_params.json for provenance.

Usage: python bake_params.py ../results/tune/best_params.json
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
POLICY = ROOT / "submission" / "transfer_policy.py"


def main() -> int:
    src = Path(sys.argv[1])
    if not src.is_absolute():
        src = (HERE / src).resolve()
    params = json.loads(src.read_text())
    text = POLICY.read_text()
    changed = []
    for k, v in params.items():
        pat = re.compile(rf'^(\s*"{re.escape(k)}":\s*)([^,]+)(,.*)$', re.M)
        m = pat.search(text)
        if not m:
            print(f"  (skip) {k} not in DEFAULT_PARAMS")
            continue
        old = m.group(2).strip()
        if isinstance(v, bool):
            new = repr(v)
        elif isinstance(v, int) or (isinstance(v, float) and v.is_integer() and k in ("min_on_steps", "min_off_steps", "heat_season_steps")):
            new = str(int(v))
        else:
            new = repr(float(v)) if not isinstance(v, str) else repr(v)
        if old != new:
            text = text[: m.start(2)] + new + text[m.end(2):]
            changed.append((k, old, new))
    POLICY.write_text(text)
    shutil.copy(src, ROOT / "submission" / "best_params.json")
    for k, o, n in changed:
        print(f"  {k}: {o} -> {n}")
    print(f"baked {len(changed)} changed value(s) into {POLICY}")
    # sanity: import and compare
    import importlib.util
    spec = importlib.util.spec_from_file_location("sadr_baked", POLICY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bad = {k: (mod.DEFAULT_PARAMS.get(k), v) for k, v in params.items()
           if k in mod.DEFAULT_PARAMS and abs(float(mod.DEFAULT_PARAMS[k]) - float(v)) > 1e-9}
    print("mismatches after bake:", bad or "none")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
