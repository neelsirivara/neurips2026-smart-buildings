"""Round 5: scenarios of the shipped six buildings under the unused Minneapolis weather station.

No generator run is needed: a scenario's config.gin differs between weather strips of the same building only in
the header comment, ``convection_coefficient``, ``weather_csv_path``, the floor-plan / zone-map paths,
``start_timestamp``, ``label`` and ``metrics_path`` (config.yaml: ``name`` and the weather block), and the
floor plan and zone map are identical. So each new scenario is a copy of one shipped strip of the building with
those lines rewritten from ``weather/<strip>.yaml``. Paths are written with forward slashes (the laptop's own
generator writes backslashes, which gin reads as escapes).

Self-check (``--check``): rewriting every shipped scenario into every other shipped strip of the same building
reproduces the shipped config.gin and config.yaml byte for byte.

Set ``r5m`` (12 scenarios; Latin-square-like, every Minneapolis strip at least once):
    building i of (1, 2, 4, 5, 7, 8) gets minneapolis_{(i mod 8)+1} and minneapolis_{((i+4) mod 8)+1}.

    python make_sets_r5.py --check
    python make_sets_r5.py write            # -> kit/smart_buildings/heldout_scenarios_r5m
    python make_sets_r5.py write_r5ms       # -> heldout_scenarios_r5ms (screening: the other 12 strips)
    python make_sets_r5.py write_r5x        # -> heldout_scenarios_r5x (screening: building_train_7 x fairbanks_1)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KB = ROOT / "kit" / "smart_buildings"
TRAIN = KB / "training_scenarios"
BUILDINGS = ["building_train_1", "building_train_2", "building_train_4", "building_train_5",
             "building_train_7", "building_train_8"]


def read_strip(strip: str) -> dict:
    out = {}
    for line in (KB / "weather" / f"{strip}.yaml").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def rewrite(src_dir: Path, dst_rel: str, building: str, strip: str) -> tuple[str, str]:
    """Return (config.gin, config.yaml) text of ``building``/``strip`` placed at kit-relative ``dst_rel``."""
    w = read_strip(strip)
    gin = (src_dir / "config.gin").read_text()
    yml = (src_dir / "config.yaml").read_text()
    label = f"{building}/{strip}"
    station_csv = w["weather_csv"]                      # csv/<station>.csv
    rules = [
        (r"^# Scenario: .*$", f"# Scenario: {label}"),
        (r"^convection_coefficient = .*$", f"convection_coefficient = {w['convection_coefficient']}"),
        (r"^weather_csv_path = .*$", f"weather_csv_path = 'smart_buildings/weather/{station_csv}'"),
        (r'^floor_plan_filepath = .*$', f'floor_plan_filepath = "{dst_rel}/floor_plan.npy"'),
        (r'^zone_map_filepath = .*$', f'zone_map_filepath = "{dst_rel}/zone_map.npy"'),
        (r"^start_timestamp = .*$", f"start_timestamp = '{w['start_timestamp']}'"),
        (r"^label = .*$", f"label = '{label}'"),
        (r'^metrics_path = .*$', f'metrics_path = "{dst_rel}/metrics"'),
    ]
    for pat, rep in rules:
        gin, n = re.subn(pat, rep, gin, flags=re.M)
        if n != 1:
            raise SystemExit(f"{src_dir}: pattern {pat!r} matched {n} times")
    yml, n = re.subn(r"^name: .*$", f"name: {label}", yml, flags=re.M)
    if n != 1:
        raise SystemExit(f"{src_dir}: yaml name matched {n} times")
    head, sep, wblock = yml.partition("\nweather:\n")      # only the weather block (simulation has its own date)
    if not sep:
        raise SystemExit(f"{src_dir}: no weather block in config.yaml")
    yrules = [
        (r"^  convection_coefficient: .*$", f"  convection_coefficient: {w['convection_coefficient']}"),
        (r"^  start_timestamp: .*$", f"  start_timestamp: {w['start_timestamp']}"),
        (r"^  weather_csv: .*$", f"  weather_csv: {station_csv}"),
    ]
    for pat, rep in yrules:
        wblock, n = re.subn(pat, rep, wblock, flags=re.M)
        if n != 1:
            raise SystemExit(f"{src_dir}: yaml pattern {pat!r} matched {n} times")
    return gin, head + sep + wblock


def check() -> int:
    bad = 0
    n = 0
    for b in BUILDINGS:
        strips = sorted(p.name for p in (TRAIN / b).iterdir() if p.is_dir())
        for s_src in strips:
            for s_dst in strips:
                if s_src == s_dst:
                    continue
                gin, yml = rewrite(TRAIN / b / s_src, f"smart_buildings/training_scenarios/{b}/{s_dst}", b, s_dst)
                n += 1
                if gin != (TRAIN / b / s_dst / "config.gin").read_text() or \
                        yml != (TRAIN / b / s_dst / "config.yaml").read_text():
                    bad += 1
                    print("MISMATCH", b, s_src, "->", s_dst)
    print(f"checked {n} rewrites, {bad} mismatches")
    return 1 if bad else 0


def r5m_pairs() -> list[tuple[str, str]]:
    pairs = []
    for i, b in enumerate(BUILDINGS):
        for s in ((i % 8) + 1, ((i + 4) % 8) + 1):
            pairs.append((b, f"minneapolis_{s}"))
    return pairs


def r5ms_pairs() -> list[tuple[str, str]]:
    """Screening companion of r5m: the strips r5m does not use, building i -> (i+2 mod 8)+1, (i+6 mod 8)+1."""
    pairs = []
    for i, b in enumerate(BUILDINGS):
        for s in (((i + 2) % 8) + 1, ((i + 6) % 8) + 1):
            pairs.append((b, f"minneapolis_{s}"))
    return pairs


def write(tag: str, pairs: list[tuple[str, str]]) -> int:
    out_root = KB / f"heldout_scenarios_{tag}"
    for b, strip in pairs:
        src = TRAIN / b / sorted(p.name for p in (TRAIN / b).iterdir() if p.is_dir())[0]
        dst = out_root / b / strip
        dst.mkdir(parents=True, exist_ok=True)
        gin, yml = rewrite(src, f"smart_buildings/heldout_scenarios_{tag}/{b}/{strip}", b, strip)
        (dst / "config.gin").write_text(gin, newline="\n")
        (dst / "config.yaml").write_text(yml, newline="\n")
        for f in ("floor_plan.npy", "zone_map.npy"):
            shutil.copyfile(src / f, dst / f)
        print(f"{b}/{strip} <- {src.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="write", choices=["write", "pairs", "write_r5ms", "write_r5x"])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.cmd == "pairs":
        print(" ".join(f"{b}/{s}" for b, s in r5m_pairs()))
        return 0
    if a.cmd == "write_r5ms":
        return write("r5ms", r5ms_pairs())
    if a.cmd == "write_r5x":
        # extra screening scenario (PREREG part 2 amendment): a public building never run in deep cold
        return write("r5x", [("building_train_7", "fairbanks_1")])
    return write("r5m", r5m_pairs())


if __name__ == "__main__":
    sys.exit(main())
