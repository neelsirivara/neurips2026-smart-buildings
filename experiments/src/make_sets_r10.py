"""Round 10: a fresh cold CONFIRMATION set of never-run generated buildings (HC3, PREREG round 10, part 1).

Every earlier confirmation set has now been read (HC2 confirmed round 9's v11), so round 10 needs new pairs.  The
kit README says the Kaggle evaluation buildings come from "the same generator and parameter ranges as the shipped
six", so HC3 uses new buildings from that family (round 4's ``shipped`` ranges, ``gen_buildings_r4.py``) instead of
yet another weather window of the shipped six:

    buildings  seeds 700-707 of the shipped family (a seed the kit rejects is replaced by the next free seed >= 708,
               as in round 4); materials stratified across the batch exactly as round 4 does it
    strips     the ten cold Sunday-06:00 windows built for rounds 6-7 (fairbanks_c1..c4, minneapolis_c1..c3,
               denver_c1..c3); building i (0-7) gets strips (i + 2k) mod 10 for k = 0..4, so every strip appears
               4 times and every building sees 5 different windows -> 40 scenarios
    files      one base scenario per building from the kit's own scenario generator (weather fairbanks_1), then
               the cold strips by the round-5 rewrite (only the weather lines differ between strips of a building;
               forward-slash paths)

Round 10 additions (2026-11-01, before any policy has run on these sets):

    HH (hot)   the same 8 buildings x 5 hot windows: building i gets HOT_STRIPS[(i + 2k) mod 10], k = 0..4
               (phoenix_3..7, singapore_1/3/4/6/8; every strip 4 times, each building 2-3 Phoenix + 2-3
               Singapore) -> heldout_scenarios_r10hh, 40 scenarios, by the same rewrite of the base scenario
    D10 (dev)  development only, never confirmation: the shipped six x four windows the public 30 does not use
               (atlanta_4/7, denver_1/4, phoenix_7, singapore_2/5) -> heldout_scenarios_r10dev, 24 scenarios,
               from the kit's own generator

Run on the Mac in a generator copy of the r6 kit (the laptop's generator writes backslash paths into config.gin;
the r6 simulator copy has no generator):

    python make_sets_r10.py buildings      # -> kit/smart_buildings/heldout_buildings_r10 (+ base scenarios)
    python make_sets_r10.py write          # -> kit/smart_buildings/heldout_scenarios_r10hc
    python make_sets_r10.py hot            # -> kit/smart_buildings/heldout_scenarios_r10hh
    python make_sets_r10.py dev            # -> kit/smart_buildings/heldout_scenarios_r10dev
    python make_sets_r10.py list           # scenario lists + strip definitions
    python make_sets_r10.py manifest       # sha256 of every scenario file (for the pre-registration)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_sets_r5 as m5  # noqa: E402
import make_sets_r6 as m6  # noqa: E402
import make_sets_r7 as m7  # noqa: E402,F401  (registers the round-7 cold strips in m6.COLD_STRIPS)

KIT = Path(os.environ.get("SB_KIT_DIR", str(HERE.parents[1] / "kit")))
KB = KIT / "smart_buildings"
BLD = KB / "heldout_buildings_r10"
BASE = KB / "heldout_scenarios_r10base"
OUT = KB / "heldout_scenarios_r10hc"
STRIPS = ["fairbanks_c1", "minneapolis_c1", "denver_c1", "fairbanks_c2", "minneapolis_c2", "denver_c2",
          "fairbanks_c3", "minneapolis_c3", "denver_c3", "fairbanks_c4"]
SEEDS = list(range(700, 708))
OUT_HH = KB / "heldout_scenarios_r10hh"
HOT_STRIPS = ["phoenix_3", "phoenix_4", "phoenix_5", "phoenix_6", "phoenix_7",
              "singapore_1", "singapore_3", "singapore_4", "singapore_6", "singapore_8"]
OUT_DEV = KB / "heldout_scenarios_r10dev"
SHIPPED = ["building_train_1", "building_train_2", "building_train_4", "building_train_5", "building_train_7",
           "building_train_8"]


def dev_pairs() -> list[tuple[str, str]]:
    """D10: windows the public 30 does not pair with any shipped building (atlanta 4/7, denver 1/4, phoenix 7,
    singapore 2/5), alternating over the six buildings."""
    out = []
    for j, b in enumerate(SHIPPED):
        out += [(b, ("atlanta_4", "atlanta_7")[j % 2]), (b, ("denver_1", "denver_4")[j % 2]), (b, "phoenix_7"),
                (b, ("singapore_2", "singapore_5")[j % 2])]
    return out
PY = sys.executable


def base_ok(name: str) -> bool:
    d = BASE / name / "fairbanks_1"
    return (d / "config.gin").exists() and (d / "zone_map.npy").exists()


def buildings() -> list[str]:
    """Write the YAMLs and a base scenario per building; replace seeds the kit rejects."""
    BLD.mkdir(parents=True, exist_ok=True)
    good: list[int] = []
    nxt = max(SEEDS) + 1
    queue = list(SEEDS)
    tried = []
    while queue and len(tried) < 40:
        sd = queue.pop(0)
        tried.append(sd)
        name = f"building_{sd:04d}"
        # one seed per call keeps each building's geometry the seed's alone; materials are drawn for the final
        # list below so that they are stratified across the batch as in round 4
        subprocess.run([PY, str(HERE / "gen_buildings_r4.py"), "write", "--family", "shipped", "--seeds", str(sd),
                        "--out", str(BLD / "_probe")], check=True, cwd=str(HERE))
        r = subprocess.run([PY, "-m", "smart_buildings.run_scenario_generator", "--buildings",
                            f"smart_buildings/heldout_buildings_r10/_probe/{name}.yaml", "--weathers", "fairbanks_1",
                            "--output-dir", "smart_buildings/heldout_scenarios_r10probe"],
                           cwd=str(KIT), capture_output=True, text=True)
        ok = r.returncode == 0 and (KB / "heldout_scenarios_r10probe" / name / "fairbanks_1" / "config.gin").exists()
        print(f"seed {sd}: {'ok' if ok else 'rejected'}{'' if ok else ' -- ' + (r.stderr or r.stdout)[-300:]}")
        if ok:
            good.append(sd)
        else:
            queue.append(nxt)
            nxt += 1
    if len(good) < len(SEEDS):
        raise SystemExit(f"only {len(good)} usable seeds: {good}")
    shutil.rmtree(BLD / "_probe", ignore_errors=True)
    shutil.rmtree(KB / "heldout_scenarios_r10probe", ignore_errors=True)
    # final batch: stratified materials over the accepted seeds, then the base scenarios
    subprocess.run([PY, str(HERE / "gen_buildings_r4.py"), "write", "--family", "shipped", "--seeds",
                    *map(str, good), "--out", str(BLD)], check=True, cwd=str(HERE))
    if BASE.exists():
        shutil.rmtree(BASE)
    names = [f"building_{sd:04d}" for sd in good]
    for n in names:
        r = subprocess.run([PY, "-m", "smart_buildings.run_scenario_generator", "--buildings",
                            f"smart_buildings/heldout_buildings_r10/{n}.yaml", "--weathers", "fairbanks_1",
                            "--output-dir", "smart_buildings/heldout_scenarios_r10base"],
                           cwd=str(KIT), capture_output=True, text=True)
        if r.returncode != 0 or not base_ok(n):
            raise SystemExit(f"{n}: base scenario failed after the probe passed: {(r.stderr or r.stdout)[-400:]}")
    (BLD / "seeds.json").write_text(json.dumps({"tried": tried, "accepted": good}, indent=1))
    print("accepted", good)
    return names


def pairs(names: list[str], strips: list[str] = STRIPS) -> list[tuple[str, str]]:
    return [(b, strips[(i + 2 * k) % len(strips)]) for i, b in enumerate(names) for k in range(5)]


def write(names: list[str], out: Path = OUT, strips: list[str] = STRIPS) -> None:
    if out.exists():
        shutil.rmtree(out)
    for b, strip in pairs(names, strips):
        src = BASE / b / "fairbanks_1"
        dst = out / b / strip
        dst.mkdir(parents=True, exist_ok=True)
        gin, yml = m5.rewrite(src, f"smart_buildings/{out.name}/{b}/{strip}", b, strip)
        if "\\" in gin:
            raise SystemExit(f"{b}/{strip}: backslash in config.gin")
        (dst / "config.gin").write_text(gin, newline="\n")
        (dst / "config.yaml").write_text(yml, newline="\n")
        for f in ("floor_plan.npy", "zone_map.npy"):
            shutil.copyfile(src / f, dst / f)
    print(f"wrote {len(pairs(names, strips))} scenarios to {out}")


def dev() -> None:
    if OUT_DEV.exists():
        shutil.rmtree(OUT_DEV)
    by_b: dict[str, list[str]] = {}
    for b, w in dev_pairs():
        by_b.setdefault(b, []).append(w)
    for b, ws in by_b.items():
        r = subprocess.run([PY, "-m", "smart_buildings.run_scenario_generator", "--buildings", b, "--weathers", *ws,
                            "--output-dir", f"smart_buildings/{OUT_DEV.name}"], cwd=str(KIT), capture_output=True,
                           text=True)
        if r.returncode != 0:
            raise SystemExit(f"{b}: {(r.stderr or r.stdout)[-400:]}")
        for w in ws:
            if "\\" in (OUT_DEV / b / w / "config.gin").read_text():
                raise SystemExit(f"{b}/{w}: backslash in config.gin")
    print(f"wrote {len(dev_pairs())} scenarios to {OUT_DEV}")


def manifest() -> dict:
    out = {}
    for d in (OUT, OUT_HH, OUT_DEV, BLD):
        if not d.exists():
            continue
        h = hashlib.sha256()
        files = sorted(f for f in d.rglob("*") if f.is_file() and "metrics" not in f.parts)
        for f in files:
            h.update(str(f.relative_to(d)).replace("\\", "/").encode())
            h.update(hashlib.sha256(f.read_bytes()).digest())
        out[d.name] = {"files": len(files), "sha256": h.hexdigest()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["buildings", "write", "hot", "dev", "list", "manifest"])
    a = ap.parse_args()
    assert len(STRIPS) == 10 and all(s in m6.COLD_STRIPS for s in STRIPS), sorted(m6.COLD_STRIPS)
    if a.cmd == "buildings":
        buildings()
        return 0
    if a.cmd == "dev":
        dev()
        return 0
    if a.cmd == "manifest":
        print(json.dumps(manifest(), indent=1))
        return 0
    seeds = json.loads((BLD / "seeds.json").read_text())["accepted"]
    names = [f"building_{sd:04d}" for sd in seeds]
    if a.cmd == "list":
        print(json.dumps({"r10hc": [f"{b}/{w}" for b, w in pairs(names)],
                          "r10hh": [f"{b}/{w}" for b, w in pairs(names, HOT_STRIPS)],
                          "r10dev": [f"{b}/{w}" for b, w in dev_pairs()],
                          "strips": {s: m6.COLD_STRIPS[s] for s in STRIPS},
                          "hot_strips": {s: m5.read_strip(s) for s in HOT_STRIPS}}, indent=1))
        return 0
    if a.cmd == "hot":
        write(names, OUT_HH, HOT_STRIPS)
        return 0
    write(names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
