"""Write round-5 job files for run_queue_r5.py.

Policies are frozen copies in results/round5/policies/ (v7.py = the shipped round-4 file, v6.py, v5.py), so
later changes to submission/transfer_policy.py cannot leak into these runs. Results go to
results/round5/full/<variant>/<set>/<building>/<weather>/<policy>/summary.json (8,640 steps) or
results/round5/screen/<variant>/<set>/... (screening length).

    python jobs_r5.py goal1            # Minneapolis set x {v7, pid_water, v6, v5} and the PR #2 check
    python jobs_r5.py set --name NAME --variant V --set S [--steps N] [--params-json P] [--policy-file F] ...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R5 = RES / "round5"
KB = ROOT / "kit" / "smart_buildings"
QUEUE = R5 / "queue"
POL = R5 / "policies"
KIT_PR2 = R5 / "kit_pr2"

PUBLIC30 = [
    "building_train_1/atlanta_2", "building_train_1/denver_7", "building_train_1/fairbanks_1",
    "building_train_1/phoenix_5", "building_train_1/singapore_8",
    "building_train_2/atlanta_3", "building_train_2/denver_8", "building_train_2/fairbanks_2",
    "building_train_2/phoenix_6", "building_train_2/singapore_1",
    "building_train_4/atlanta_5", "building_train_4/denver_2", "building_train_4/fairbanks_4",
    "building_train_4/phoenix_8", "building_train_4/singapore_3",
    "building_train_5/atlanta_6", "building_train_5/denver_3", "building_train_5/fairbanks_5",
    "building_train_5/phoenix_1", "building_train_5/singapore_4",
    "building_train_7/atlanta_8", "building_train_7/denver_5", "building_train_7/fairbanks_7",
    "building_train_7/phoenix_3", "building_train_7/singapore_6",
    "building_train_8/atlanta_1", "building_train_8/denver_6", "building_train_8/fairbanks_8",
    "building_train_8/phoenix_4", "building_train_8/singapore_7",
]
SETS = {  # name -> (scenario dir, scenario keys or None = discover)
    "r5m": (KB / "heldout_scenarios_r5m", None),
    "pub30": (KB / "training_scenarios", PUBLIC30),
    "pubfair6": (KB / "training_scenarios", [s for s in PUBLIC30 if "fairbanks" in s]),
    "r5ms": (KB / "heldout_scenarios_r5ms", None),
    "r5x": (KB / "heldout_scenarios_r5x", None),
    "r4s": (KB / "heldout_scenarios_r4s", None),
    "r4c": (KB / "heldout_scenarios_r4c", None),
    "old10": (KB / "heldout_scenarios", None),
    "old30": (KB / "heldout_scenarios_r3", None),
}
# round-5 screen (PREREG part 2)
SCREEN = {
    "r5ms": ["building_train_1/minneapolis_7", "building_train_2/minneapolis_8", "building_train_4/minneapolis_1",
             "building_train_5/minneapolis_2", "building_train_7/minneapolis_3", "building_train_8/minneapolis_4"],
    "r4s": ["building_0520/fairbanks_1", "building_0522/fairbanks_3", "building_0523/denver_6",
            "building_0524/phoenix_8"],
    "r5x": ["building_train_7/fairbanks_1"],      # amendment 12:20 PDT (deep-cold public building)
    "pub30": ["building_train_1/fairbanks_1", "building_train_8/fairbanks_8", "building_train_2/denver_8",
              "building_train_1/phoenix_5"],
}
V8 = HERE / "policy_candidates" / "transfer_policy_v8.py"
CANDS = HERE / "policy_candidates"
VARIANTS = {  # name -> (policy key, policy file)
    "v7": ("transfer", POL / "v7.py"),
    "v6": ("transfer", POL / "v6.py"),
    "v5": ("transfer", POL / "v5.py"),
    "pid_water": ("pid_water", None),
}


def discover(d: Path) -> list[str]:
    return [f"{b.name}/{w.name}" for b in sorted(d.iterdir()) if b.is_dir()
            for w in sorted(b.iterdir()) if (w / "config.gin").exists()]


def scen_list(set_name: str, scen_dir_override: Path | None = None) -> tuple[Path, list[str]]:
    d, keys = SETS[set_name]
    if scen_dir_override is not None:
        d = scen_dir_override
    return d, (keys if keys is not None else discover(SETS[set_name][0]))


def jobs_for(variant: str, set_name: str, steps: int = 8640, kind: str = "full", tag: str | None = None,
             policy: str | None = None, policy_file: Path | None = None, params_json: Path | None = None,
             kit_dir: Path | None = None, runner: str = "scenario", scenarios: list[str] | None = None) -> list[dict]:
    pkey, pfile = VARIANTS.get(variant, ("transfer", None))
    pkey = policy or pkey
    pfile = policy_file or pfile
    scen_override = None
    if kit_dir is not None:
        scen_override = kit_dir / SETS[set_name][0].relative_to(ROOT / "kit")
    d, keys = scen_list(set_name, scen_override)
    if scenarios:
        keys = scenarios
    tag = tag or variant
    out_dir = R5 / kind / tag / set_name
    return [{"id": f"{kind}/{tag}/{set_name}/{k}", "policy": pkey,
             "policy_file": str(pfile) if pfile else None, "params_json": str(params_json) if params_json else None,
             "scen_dir": str(d), "scenario": k, "steps": steps, "results_dir": str(out_dir), "runner": runner,
             "kit_dir": str(kit_dir) if kit_dir else None} for k in keys]


def write(name: str, jobs: list[dict]) -> None:
    QUEUE.mkdir(parents=True, exist_ok=True)
    (QUEUE / f"{name}.json").write_text(json.dumps(jobs, indent=1))
    print(f"{name}: {len(jobs)} jobs")


def goal1() -> None:
    write("010_r5m_v7", jobs_for("v7", "r5m"))
    write("020_r5m_pid_water", jobs_for("pid_water", "r5m"))
    write("030_pr2_fair_v7", jobs_for("v7", "pubfair6", tag="v7_pr2", kit_dir=KIT_PR2))
    write("040_r5m_v6", jobs_for("v6", "r5m"))
    write("050_pr2_fair_pid_water", jobs_for("pid_water", "pubfair6", tag="pid_water_pr2", kit_dir=KIT_PR2))
    write("060_r5m_v5", jobs_for("v5", "r5m"))


def screen(cands: list[str], prefix: int = 100, steps: int = 2880) -> None:
    for i, c in enumerate(cands):
        jobs = []
        for set_name, keys in SCREEN.items():
            jobs += jobs_for(c, set_name, steps=steps, kind="screen", tag=c, policy="transfer", policy_file=V8,
                             params_json=CANDS / f"{c}.json", scenarios=keys)
        write(f"{prefix + i:03d}_screen_{c}", jobs)


def confirm(cand: str, sets: list[str], prefix: int = 330) -> None:
    for i, set_name in enumerate(sets):
        write(f"{prefix + i:03d}_confirm_{cand}_{set_name}",
              jobs_for(cand, set_name, steps=8640, kind="full", tag=cand, policy="transfer", policy_file=V8,
                       params_json=CANDS / f"{cand}.json"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["goal1", "set", "screen", "confirm"])
    ap.add_argument("--sets", nargs="*")
    ap.add_argument("--cands", nargs="*")
    ap.add_argument("--prefix", type=int, default=100)
    ap.add_argument("--name")
    ap.add_argument("--variant")
    ap.add_argument("--set")
    ap.add_argument("--steps", type=int, default=8640)
    ap.add_argument("--kind", default="full")
    ap.add_argument("--tag")
    ap.add_argument("--params-json")
    ap.add_argument("--policy-file")
    ap.add_argument("--runner", default="scenario")
    ap.add_argument("--scenarios", nargs="*")
    a = ap.parse_args()
    if a.cmd == "goal1":
        goal1()
        return 0
    if a.cmd == "confirm":
        confirm(a.cands[0], a.sets, a.prefix if a.prefix != 100 else 330)
        return 0
    if a.cmd == "screen":
        screen(a.cands, a.prefix, a.steps if a.steps != 8640 else 2880)
        return 0
    write(a.name, jobs_for(a.variant, a.set, steps=a.steps, kind=a.kind, tag=a.tag,
                           policy_file=Path(a.policy_file).resolve() if a.policy_file else None,
                           params_json=Path(a.params_json).resolve() if a.params_json else None,
                           runner=a.runner, scenarios=a.scenarios))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
