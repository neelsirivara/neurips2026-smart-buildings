"""Round 6: harsher-weather scenario sets of the shipped six buildings (PREREG round 6, part 1).

Scenarios are made exactly as in round 5 (make_sets_r5.rewrite: a copy of one shipped strip of the building with
the weather lines rewritten; byte-identical to the shipped configs for shipped strips). New "cold-month" strips are
30-day windows of the shipped station CSVs that no shipped strip covers, starting on a Sunday at 06:00 like every
shipped strip (all shipped strips start on Sundays, 6 weeks apart); their convection coefficient is the station's.

Cold-month strips (mean / min outdoor temperature over the 30 days, from the CSVs):
    fairbanks_c1    2023-11-26 06:00   -20.1 / -38.9 C   (no shipped Fairbanks strip covers Nov 22 - Dec 31)
    fairbanks_c2    2023-01-15 06:00   -21.7 / -41.1 C   (overlaps fairbanks_1 by 16 days)
    minneapolis_c1  2023-11-26 06:00    -4.4 / -20.0 C
    denver_c1       2023-01-22 06:00    -3.1 / -21.1 C   (the coldest Sunday-start window of Denver)

Sets (building i of 1, 2, 4, 5, 7, 8):
    r6hc  harsh CONFIRMATION set (48, never used before):
          Minneapolis: the 24 building x strip pairs that neither r5m nor r5ms uses (every strip 3 times);
          Fairbanks shipped cold strips (1 Jan, 2 Feb, 8 Oct-Nov), one per building, none public or r5x;
          denver_1 (Jan, the coldest shipped Denver strip; no set has used it) for all six;
          fairbanks_c1 and minneapolis_c1 for all six.
    r6hs  harsh SCREENING set (18):
          r5ms's colder strip of each building (6), the other Fairbanks cold pairs (6), fairbanks_c2 x
          (train_1, train_5, train_8) and denver_c1 x (train_2, train_4, train_7).

    python make_sets_r6.py --check      # round-5 self-check (120 shipped rewrites byte for byte)
    python make_sets_r6.py write        # -> kit/smart_buildings/heldout_scenarios_r6hc, heldout_scenarios_r6hs
    python make_sets_r6.py list
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_sets_r5 as m5  # noqa: E402

KB = m5.KB
TRAIN = m5.TRAIN
B = m5.BUILDINGS          # building_train_1, _2, _4, _5, _7, _8

COLD_STRIPS = {
    "fairbanks_c1": {"name": "fairbanks_c1", "weather_csv": "csv/fairbanks.csv", "convection_coefficient": "8.8",
                     "start_timestamp": "2023-11-26 06:00"},
    "fairbanks_c2": {"name": "fairbanks_c2", "weather_csv": "csv/fairbanks.csv", "convection_coefficient": "8.8",
                     "start_timestamp": "2023-01-15 06:00"},
    "minneapolis_c1": {"name": "minneapolis_c1", "weather_csv": "csv/minneapolis.csv",
                       "convection_coefficient": "21.5", "start_timestamp": "2023-11-26 06:00"},
    "denver_c1": {"name": "denver_c1", "weather_csv": "csv/denver.csv", "convection_coefficient": "26.7",
                  "start_timestamp": "2023-01-22 06:00"},
}

_orig_read_strip = m5.read_strip


def read_strip(strip: str) -> dict:
    if strip in COLD_STRIPS:
        return dict(COLD_STRIPS[strip])
    return _orig_read_strip(strip)


m5.read_strip = read_strip      # rewrite() looks the strip up through the module global


def minneapolis_rest() -> list[tuple[str, str]]:
    used = set(m5.r5m_pairs()) | set(m5.r5ms_pairs())
    return [(b, f"minneapolis_{s}") for b in B for s in range(1, 9) if (b, f"minneapolis_{s}") not in used]


FAIR_HC = {"building_train_1": 8, "building_train_2": 1, "building_train_4": 2, "building_train_5": 8,
           "building_train_7": 2, "building_train_8": 1}
FAIR_HS = {"building_train_1": 2, "building_train_2": 8, "building_train_4": 1, "building_train_5": 1,
           "building_train_7": 8, "building_train_8": 2}
R5MS_COLD = {"building_train_1": "minneapolis_3", "building_train_2": "minneapolis_8",
             "building_train_4": "minneapolis_1", "building_train_5": "minneapolis_2",
             "building_train_7": "minneapolis_3", "building_train_8": "minneapolis_8"}


def r6hc_pairs() -> list[tuple[str, str]]:
    pairs = list(minneapolis_rest())
    pairs += [(b, f"fairbanks_{FAIR_HC[b]}") for b in B]
    pairs += [(b, "denver_1") for b in B]
    pairs += [(b, "fairbanks_c1") for b in B]
    pairs += [(b, "minneapolis_c1") for b in B]
    return pairs


def r6hs_pairs() -> list[tuple[str, str]]:
    pairs = [(b, R5MS_COLD[b]) for b in B]
    pairs += [(b, f"fairbanks_{FAIR_HS[b]}") for b in B]
    pairs += [(b, "fairbanks_c2") for b in ("building_train_1", "building_train_5", "building_train_8")]
    pairs += [(b, "denver_c1") for b in ("building_train_2", "building_train_4", "building_train_7")]
    return pairs


def sanity() -> None:
    public = {(b, w.name) for b in B for w in (TRAIN / b).iterdir() if w.is_dir()}
    r5 = set(m5.r5m_pairs()) | set(m5.r5ms_pairs()) | {("building_train_7", "fairbanks_1")}
    hc, hs = r6hc_pairs(), r6hs_pairs()
    assert len(hc) == len(set(hc)) == 48, len(hc)
    assert len(hs) == len(set(hs)) == 18, len(hs)
    assert not set(hc) & set(hs)
    assert not set(hc) & public and not set(hs) & public
    assert not set(hc) & r5, set(hc) & r5
    assert set(hs) - r5 == set(hs) - set(m5.r5ms_pairs())
    mins = [w for _, w in hc if w.startswith("minneapolis_") and not w.endswith("c1")]
    assert sorted(set(mins)) == [f"minneapolis_{i}" for i in range(1, 9)]
    assert all(mins.count(f"minneapolis_{i}") == 3 for i in range(1, 9))


def write(tag: str, pairs: list[tuple[str, str]]) -> None:
    out_root = KB / f"heldout_scenarios_{tag}"
    if out_root.exists():
        shutil.rmtree(out_root)
    for b, strip in pairs:
        src = TRAIN / b / sorted(p.name for p in (TRAIN / b).iterdir() if p.is_dir())[0]
        dst = out_root / b / strip
        dst.mkdir(parents=True, exist_ok=True)
        gin, yml = m5.rewrite(src, f"smart_buildings/heldout_scenarios_{tag}/{b}/{strip}", b, strip)
        (dst / "config.gin").write_text(gin, newline="\n")
        (dst / "config.yaml").write_text(yml, newline="\n")
        for f in ("floor_plan.npy", "zone_map.npy"):
            shutil.copyfile(src / f, dst / f)
    print(f"wrote {len(pairs)} scenarios to {out_root}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="list", choices=["write", "list"])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        return m5.check()
    sanity()
    if a.cmd == "list":
        print(json.dumps({"r6hc": [f"{b}/{w}" for b, w in r6hc_pairs()],
                          "r6hs": [f"{b}/{w}" for b, w in r6hs_pairs()], "cold_strips": COLD_STRIPS}, indent=1))
        return 0
    write("r6hc", r6hc_pairs())
    write("r6hs", r6hs_pairs())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
