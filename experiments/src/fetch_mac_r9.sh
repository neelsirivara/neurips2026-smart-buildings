#!/usr/bin/env bash
# Round 9: copy the Mac's round-9 outputs (~/neurips/sb/r9/src/out/<batch>) into experiments/results/round9/mac/<batch>.
# Usage: bash experiments/src/fetch_mac_r9.sh v10_diag quirk_probe lp_bound
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HERE/../results/round9/mac"
mkdir -p "$DST"
for b in "$@"; do
  # run_diag_r9 writes under r9/src/out (paths relative to its own dir); quirk_probe / lp_bound under r9/out
  timeout 600 ssh mac "if [ -d ~/neurips/sb/r9/src/out/$b ]; then cd ~/neurips/sb/r9/src/out; else cd ~/neurips/sb/r9/out; fi && tar czf - $b" | tar xzf - -C "$DST"
  echo "fetched $b -> $DST/$b ($(find "$DST/$b" -name '*.json' | wc -l) json)"
done
