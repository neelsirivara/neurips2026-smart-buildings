"""Collect environment / compute facts into results/env_info.json for make_macros.py.

Walks every summary.json under experiments/results (full, heldout, tune, dev*) and
records simulator speed statistics and the total simulated core-hours, plus the
interpreter and key package versions of the kit venv.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"


def main() -> int:
    sps, mins, total_s, n = [], [], 0.0, 0
    per_tree: dict[str, int] = {}
    for f in RES.rglob("summary.json"):
        try:
            s = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        steps = int(s.get("total_steps", 0))
        sec = s.get("seconds_per_step")
        if not steps or sec is None:
            continue
        n += 1
        tree = f.relative_to(RES).parts[0]
        per_tree[tree] = per_tree.get(tree, 0) + 1
        total_s += sec * steps + float(s.get("env_load_seconds", 0.0))
        if steps == 8640:
            sps.append(sec)
            mins.append(sec * steps / 60.0)
    info = {
        "n_runs": n,
        "runs_per_tree": per_tree,
        "sec_per_step_median": float(np.median(sps)) if sps else None,
        "sec_per_step_min": float(np.min(sps)) if sps else None,
        "sec_per_step_max": float(np.max(sps)) if sps else None,
        "min_per_scenario_median": float(np.median(mins)) if mins else None,
        "total_core_hours": total_s / 3600.0,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    try:
        import numba, gymnasium, pandas  # noqa: E401
        info["versions"] = {"numpy": np.__version__, "numba": numba.__version__,
                            "gymnasium": gymnasium.__version__, "pandas": pandas.__version__}
    except Exception as e:  # noqa: BLE001
        info["versions_error"] = str(e)
    (RES / "env_info.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
