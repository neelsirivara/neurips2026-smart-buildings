"""Round 7: a fresh harsh-weather CONFIRMATION set of the shipped six buildings (PREREG round 7, part 1).

Built exactly as round 6's sets (make_sets_r6 / make_sets_r5.rewrite: a copy of one shipped strip of the building
with the weather lines rewritten). New cold-month strips are 30-day windows of the shipped station CSVs starting on a
Sunday at 06:00, chosen as the coldest Sunday-start windows of each station that no earlier set used as a strip
(overlaps with earlier windows are stated; a scenario is a building x strip pair, and no pair below has been run by
any earlier round):

    fairbanks_c3    2023-01-29 06:00   mean -17.5 C, min -41 C   (overlaps fairbanks_c2 / fairbanks_2 by 16 days)
    fairbanks_c4    2023-11-05 06:00   mean -15.1 C, min -35 C   (overlaps fairbanks_8 by 16 days, fairbanks_c1 by 9)
    minneapolis_c2  2023-01-22 06:00   mean  -6.4 C, min -24 C   (overlaps minneapolis_1 by 16 days)
    minneapolis_c3  2023-02-05 06:00   mean  -3.1 C, min -22 C   (overlaps minneapolis_2 and minneapolis_c2 by 16)
    denver_c2       2023-01-01 06:00   mean  -0.3 C, min -19 C   (overlaps denver_1 by 16 days)
    denver_c3       2023-02-05 06:00   mean  +0.1 C, min -21 C   (overlaps denver_c1 by 16 days)

    r7hc (44): the six new strips x all six buildings (36); fairbanks_c2 x (train_2, train_4, train_7) and denver_c1 x
          (train_1, train_5, train_8) (the round-6 cold strips on the buildings round 6 did not run them on, 6); the two
          unused shipped Fairbanks cold pairs, train_4/fairbanks_8 and train_5/fairbanks_2 (2).

    python make_sets_r7.py list | write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_sets_r5 as m5  # noqa: E402
import make_sets_r6 as m6  # noqa: E402

B = m5.BUILDINGS
NEW = {
    "fairbanks_c3": ("csv/fairbanks.csv", "8.8", "2023-01-29 06:00"),
    "fairbanks_c4": ("csv/fairbanks.csv", "8.8", "2023-11-05 06:00"),
    "minneapolis_c2": ("csv/minneapolis.csv", "21.5", "2023-01-22 06:00"),
    "minneapolis_c3": ("csv/minneapolis.csv", "21.5", "2023-02-05 06:00"),
    "denver_c2": ("csv/denver.csv", "26.7", "2023-01-01 06:00"),
    "denver_c3": ("csv/denver.csv", "26.7", "2023-02-05 06:00"),
}
for k, (csvf, cc, start) in NEW.items():
    m6.COLD_STRIPS[k] = {"name": k, "weather_csv": csvf, "convection_coefficient": cc, "start_timestamp": start}


def r7hc_pairs() -> list[tuple[str, str]]:
    pairs = [(b, s) for s in NEW for b in B]
    pairs += [(b, "fairbanks_c2") for b in ("building_train_2", "building_train_4", "building_train_7")]
    pairs += [(b, "denver_c1") for b in ("building_train_1", "building_train_5", "building_train_8")]
    pairs += [("building_train_4", "fairbanks_8"), ("building_train_5", "fairbanks_2")]
    return pairs


def sanity() -> None:
    public = {(b, w.name) for b in B for w in (m5.TRAIN / b).iterdir() if w.is_dir()}
    used = set(public) | set(m5.r5m_pairs()) | set(m5.r5ms_pairs()) | {("building_train_7", "fairbanks_1")}
    used |= set(m6.r6hc_pairs()) | set(m6.r6hs_pairs())
    hc = r7hc_pairs()
    assert len(hc) == len(set(hc)) == 44, len(hc)
    assert not set(hc) & used, sorted(set(hc) & used)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="list", choices=["write", "list"])
    a = ap.parse_args()
    sanity()
    if a.cmd == "list":
        print(json.dumps({"r7hc": [f"{b}/{w}" for b, w in r7hc_pairs()],
                          "new_strips": {k: m6.COLD_STRIPS[k] for k in NEW}}, indent=1))
        return 0
    m6.write("r7hc", r7hc_pairs())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
