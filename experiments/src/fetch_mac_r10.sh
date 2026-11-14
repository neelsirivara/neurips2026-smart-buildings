#!/usr/bin/env bash
# Round 10: copy the Mac's run summaries (~/neurips/sb/r10/out/runs/<variant>/<set>/<b>/<w>/transfer/summary.json)
# into results/round6/runs/<variant>/<set>/... (compare_r10.py reads that tree). Summaries only; existing files are
# overwritten only if the Mac copy differs (tar keeps the Mac's content).
#   bash experiments/src/fetch_mac_r10.sh [variant-glob]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HERE/../results/round6/runs"
PAT="${1:-r10_*}"
mkdir -p "$DST"
ssh mac "cd ~/neurips/sb/r10/out/runs && find . -path './$PAT/*' -name summary.json -print0 | xargs -0 tar cf -" \
  | tar xf - -C "$DST"
find "$DST" -path "*/$PAT/*" -name summary.json | wc -l
