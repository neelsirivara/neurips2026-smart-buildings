"""Round 4: generate new buildings for the screening set and the fresh confirmation set.

Two parameter-range families (the kit's generator code, materials stratified across each batch
exactly as run_floor_generator.py does it; geometry from the seed alone):

    default   the kit's DEFAULT_RANGES in run_floor_generator.py (what round 3 used; width 400-700 ft,
              height 300-500 ft, rooms 30-60 ft) -- note this does NOT reproduce the shipped six
              (seed 0 gives 597 x 494 ft, building_train_1 with seed 0 is 373 x 188 ft)
    shipped   the min-max envelope of the six shipped buildings' own YAML parameters (width 318-430,
              height 188-301, floors 2-4, min room 25-35, span 11-16, shape ratio 0.294-0.384,
              coverage 0.651-0.802, AHUs >= 3-9, occupants 1-2) -- the kit README says the Kaggle
              evaluation buildings come from "the same generator and parameter ranges as the
              shipped six", so this is the closer proxy for the leaderboard

    python gen_buildings_r4.py scan --seeds 606-699                  # geometry only (default ranges)
    python gen_buildings_r4.py write --family shipped --seeds 520 521 --out ../../kit/smart_buildings/heldout_buildings_r4s
    python gen_buildings_r4.py pairs --buildings building_0520 ... --offset 0   # strip per station (Latin square)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1] / "kit"
sys.path.insert(0, str(KIT))

import yaml  # noqa: E402

from smart_buildings.run_floor_generator import DEFAULT_RANGES  # noqa: E402
from smart_buildings.smart_control.utils.config_generator import generate_config  # noqa: E402
from smart_buildings.smart_control.utils.materials import draw_materials, envelope_capacity, facade_u  # noqa: E402

SHIPPED_RANGES = dict(
    width=(318, 430),
    height=(188, 301),
    num_floors=(2, 4),
    min_room_size=(25, 35),
    room_size_span=(11, 16),
    shape_ratio=(0.294, 0.384),
    composite_coverage=(0.651, 0.802),
    composite_style="architectural",
    num_ahus=(3, 9),
    occupants_per_zone=(1, 2),
)
FAMILIES = {"default": DEFAULT_RANGES, "shipped": SHIPPED_RANGES}
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore")


def parse_seeds(items):
    out = []
    for it in items:
        if "-" in str(it):
            a, b = str(it).split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(it))
    return out


def cfg(seed, family, mats=None):
    c = generate_config(name=f"building_{seed:04d}", seed=seed, building_shape="composite", **FAMILIES[family])
    if mats is not None:
        c["materials"] = mats
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--seeds", nargs="+", required=True)
    s.add_argument("--family", default="default", choices=list(FAMILIES))
    w = sub.add_parser("write")
    w.add_argument("--seeds", nargs="+", required=True)
    w.add_argument("--family", required=True, choices=list(FAMILIES))
    w.add_argument("--out", required=True)
    pr = sub.add_parser("pairs")
    pr.add_argument("--buildings", nargs="+", required=True)
    pr.add_argument("--offset", type=int, default=0)
    a = ap.parse_args()

    if a.cmd == "scan":
        rows = []
        for sd in parse_seeds(a.seeds):
            fp = cfg(sd, a.family)["floor_plan"]
            gross = fp["width"] * fp["height"] * fp["num_floors"]
            rows.append({"seed": sd, "width": fp["width"], "height": fp["height"], "floors": fp["num_floors"],
                         "min_room": fp["min_room_size"], "max_room": fp["max_room_size"], "gross_ft2": gross})
        print(json.dumps(rows))
        return 0

    if a.cmd == "pairs":
        # Latin square: building i, station s -> strip ((i + 2 s + offset) mod 8) + 1
        out = []
        for i, b in enumerate(a.buildings):
            for si, st in enumerate(STATIONS):
                out.append(f"{b}/{st}_{(i + 2 * si + a.offset) % 8 + 1}")
        print(" ".join(out))
        return 0

    seeds = parse_seeds(a.seeds)
    digest = hashlib.sha256(repr(seeds).encode()).digest()
    mats = draw_materials(random.Random(int.from_bytes(digest[:8], "big")), len(seeds))
    outd = Path(a.out)
    outd.mkdir(parents=True, exist_ok=True)
    for sd, m in zip(seeds, mats):
        c = cfg(sd, a.family, m)
        fp = c["floor_plan"]
        (outd / f"{c['name']}.yaml").write_text(yaml.dump(c, default_flow_style=False, sort_keys=False))
        print(f"{c['name']} ({a.family}): {fp['width']}x{fp['height']} ft, floors={fp['num_floors']}, "
              f"rooms {fp['min_room_size']}-{fp['max_room_size']}, AHUs>={c['ahu']['num_ahus']}, "
              f"U={facade_u(m):.2f}, C={envelope_capacity(m) / 1e6:.2f} MJ/m3K -> {outd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
