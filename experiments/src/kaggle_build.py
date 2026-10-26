"""Build a one-cell Kaggle notebook for a policy, the way SADR v7 was pushed (round 5).

The cell is the policy source unchanged except that its ``class TransferPolicy:`` is renamed
``_SADRPolicy`` (or, for the organizers' pid_water baseline, kit ``pid.py`` + ``pid_plus.py`` with the
intra-kit import removed), followed by the organizers' template wiring (a ``TransferPolicy`` subclass
of ``kaggle_evaluation.smart_buildings_inference_server.Policy`` that delegates to the policy, then
``SmartBuildingsInferenceServer(TransferPolicy).run(...)``).

Writes
    submission/kaggle/<slug>/push/<slug>.ipynb, kernel-metadata.json   (what `kaggle kernels push -p` takes)
    submission/kaggle/<slug>/<slug>_cell.py                            (the cell, for diffing)
    submission/kaggle/<slug>/<slug>_localtest.py                       (policy + `TransferPolicy = impl`, for
                                                                        run_scenario.py --policy-file)

Self-check: ``--check-v7`` rebuilds the v7 cell from submission/kaggle/sadr_v7_submission.py's policy
part and verifies it is byte-identical to the cell that was pushed in round 4.

Usage:
    python kaggle_build.py --source <policy.py> --slug sadr-v6-smart-buildings --title "SADR v6 Smart Buildings" --label "SADR v6"
    python kaggle_build.py --pid-water --slug pid-water-baseline-smart-buildings --title "pid water baseline Smart Buildings" --label "pid_water"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KAGGLE = ROOT / "submission" / "kaggle"
KIT_BASE = ROOT / "kit" / "smart_buildings" / "baselines"

WIRING = '''


# ---------------------------------------------------------------------------
# Kaggle wiring (unchanged from the organizers' TransferPolicy Notebook template):
# the organizers' Policy base class wraps {label}, and their inference server runs it.
import sys as _sys
_sys.path.append('/kaggle/input/competitions/neurips-2026-smart-buildings/kaggle_evaluation')
from kaggle_evaluation import smart_buildings_inference_server

COMPETITION_DATA_FOLDER = '/kaggle/input/competitions/neurips-2026-smart-buildings/'


class TransferPolicy(smart_buildings_inference_server.Policy):
    """{label} (https://github.com/neelsirivara/neurips2026-smart-buildings)."""

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        self._impl = {impl}(building_meta_data, action_spec)
        print({hello}, flush=True)

    def get_action(self, obs):
        return self._impl.get_action(obs)


smart_buildings_inference_server.SmartBuildingsInferenceServer(TransferPolicy).run(
    competition_data_folder=COMPETITION_DATA_FOLDER,
)
'''


def sadr_policy_part(source: str) -> str:
    marker = "\nclass TransferPolicy:\n"
    if source.count(marker) != 1:
        raise SystemExit("expected exactly one 'class TransferPolicy:' in the source")
    return source.replace(marker, "\nclass _SADRPolicy:\n").rstrip("\n") + "\n"


def pid_water_policy_part() -> str:
    pid = (KIT_BASE / "pid.py").read_text(encoding="utf-8")
    plus = (KIT_BASE / "pid_plus.py").read_text(encoding="utf-8")
    imp = "from smart_buildings.baselines.pid import PIDPolicy\n"
    if plus.count(imp) != 1:
        raise SystemExit("unexpected pid_plus.py import layout")
    plus = plus.replace(imp, "# (kit import of PIDPolicy removed: pid.py is inlined above)\n")
    return ("# Organizers' starter-kit baselines pid.py + pid_plus.py (Apache-2.0), inlined unchanged.\n"
            + pid.rstrip("\n") + "\n\n\n" + plus.rstrip("\n") + "\n")


def build_cell(policy_part: str, label: str, impl: str, hello: str) -> str:
    return policy_part.rstrip("\n") + WIRING.format(label=label, impl=impl, hello=hello)


def notebook(cell: str, cell_id: str) -> dict:
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "id": cell_id, "metadata": {},
                   "outputs": [], "source": cell.splitlines(keepends=True)}],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5}


def metadata(slug: str, title: str) -> dict:
    return {"id": f"neelsiri/{slug}", "title": title, "code_file": f"{slug}.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [],
            "competition_sources": ["neurips-2026-smart-buildings"], "kernel_sources": [], "model_sources": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--pid-water", action="store_true")
    ap.add_argument("--slug")
    ap.add_argument("--title")
    ap.add_argument("--label")
    ap.add_argument("--check-v7", action="store_true")
    a = ap.parse_args()

    if a.check_v7:
        pushed = json.loads((KAGGLE / "push" / "sadr-v7-smart-buildings.ipynb").read_text(encoding="utf-8"))
        pushed_cell = "".join(pushed["cells"][0]["source"])
        shipped = (ROOT / "submission" / "transfer_policy.py").read_text(encoding="utf-8")
        rebuilt = build_cell(sadr_policy_part(shipped), "SADR v7", "_SADRPolicy",
                             'f"SADR v7 controlling {self._impl.K} AHUs"')
        ok = rebuilt.rstrip("\n") == pushed_cell.rstrip("\n")
        print("v7 cell rebuilt byte-identical:", ok)
        return 0 if ok else 1

    if a.pid_water:
        part, impl, hello = pid_water_policy_part(), "PIDWaterResetPolicy", f'"{a.label} baseline initialised"'
    else:
        part = sadr_policy_part(Path(a.source).read_text(encoding="utf-8"))
        impl, hello = "_SADRPolicy", 'f"' + a.label + ' controlling {self._impl.K} AHUs"'
    cell = build_cell(part, a.label, impl, hello)
    out = KAGGLE / a.slug
    (out / "push").mkdir(parents=True, exist_ok=True)
    (out / f"{a.slug}_cell.py").write_text(cell, encoding="utf-8", newline="\n")
    (out / f"{a.slug}_localtest.py").write_text(part + f"\n\nTransferPolicy = {impl}\n", encoding="utf-8",
                                                newline="\n")
    (out / "push" / f"{a.slug}.ipynb").write_text(json.dumps(notebook(cell, a.slug[:40]), indent=1),
                                                  encoding="utf-8", newline="\n")
    (out / "push" / "kernel-metadata.json").write_text(json.dumps(metadata(a.slug, a.title), indent=1),
                                                       encoding="utf-8", newline="\n")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
