#!/usr/bin/env bash
# Round 4: build the screening set (r4s) and the fresh confirmation set (r4c) of generated buildings.
#   r4s (screening, 4 buildings x 5 stations = 20 scenarios): shipped-range seeds 520, 524; default-range 522, 523
#   r4c (confirmation, never screened, 8 x 5 = 40):          shipped-range seeds 601, 602, 603, 606;
#                                                            default-range 604, 607, 610 (largest rooms of seeds
#                                                            606-699), 639 (largest gross area of seeds 606-699)
# Seed rule (PREREG.md): shipped 600-603 and default 604-605 plus the two largest of a geometry scan of 606-699;
# a seed the kit's generator rejects (zones below 20 m2: 521, 600, 605) is replaced by the next free seed that
# passes (524, 606, 607).  Weather: Latin square, building i of the list, station s -> strip (i + 2 s + offset) % 8 + 1.
set -eu
cd "$(dirname "$0")"
PY=$(pwd)/../../kit/.venv/bin/python
[ -x "$PY" ] || PY=$(pwd)/../../kit/.venv/Scripts/python.exe
KB=../../kit/smart_buildings
export WRAPT_DISABLE_EXTENSIONS=true
$PY gen_buildings_r4.py write --family shipped --seeds 520 524 --out $KB/heldout_buildings_r4s
$PY gen_buildings_r4.py write --family default --seeds 522 523 --out $KB/heldout_buildings_r4s
$PY gen_buildings_r4.py write --family shipped --seeds 601 602 603 606 --out $KB/heldout_buildings_r4c
$PY gen_buildings_r4.py write --family default --seeds 604 607 610 639 --out $KB/heldout_buildings_r4c
gen_set() {  # tag offset buildings...
  local tag=$1 off=$2; shift 2
  local pairs; pairs=$($PY gen_buildings_r4.py pairs --buildings "$@" --offset "$off")
  for b in "$@"; do
    local ws; ws=$(echo "$pairs" | tr ' ' '\n' | grep "^$b/" | cut -d/ -f2 | tr '\n' ' ')
    (cd ../../kit && $PY -m smart_buildings.run_scenario_generator --buildings smart_buildings/heldout_buildings_$tag/$b.yaml \
        --weathers $ws --output-dir smart_buildings/heldout_scenarios_$tag 2>&1 | grep -E " -> |Error" )
  done
}
gen_set r4s 0 building_0520 building_0524 building_0522 building_0523
gen_set r4c 4 building_0601 building_0602 building_0603 building_0606 building_0604 building_0607 building_0610 building_0639
