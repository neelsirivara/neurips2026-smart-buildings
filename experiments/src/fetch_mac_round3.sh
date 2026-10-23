#!/usr/bin/env bash
# Copy the Mac's round-3 result trees (summary.json, diag.csv, zones.npz, *__agg.json) into
# experiments/results/mac/round3/ so that scoring, decomposition and macros stay local. Safe to re-run
# (whole-tree copy through a tar stream; the Mac tree is small enough: ~5 MB per diag scenario).
#   usage: fetch_mac_round3.sh [subdir ...]     default: every subdir of results/round3 on the Mac
set -u
cd "$(dirname "$0")/../results"
mkdir -p mac/round3 logs/mac
if [ $# -eq 0 ]; then
  set -- $(ssh -o BatchMode=yes mac 'ls ~/neurips/sb/experiments/results/round3')
fi
for d in "$@"; do
  if ssh -o BatchMode=yes mac "test -d ~/neurips/sb/experiments/results/round3/$d"; then
    rm -rf "mac/round3/$d.tmp" && mkdir -p "mac/round3/$d.tmp"
    ssh -o BatchMode=yes mac "cd ~/neurips/sb/experiments/results/round3/$d && tar czf - ." | tar xzf - -C "mac/round3/$d.tmp" \
      && rm -rf "mac/round3/$d" && mv "mac/round3/$d.tmp" "mac/round3/$d"
    echo "fetched round3/$d: $(find mac/round3/$d -name summary.json | wc -l) summary files"
  fi
done
scp -q "mac:~/neurips/logs/r3_*.log" logs/mac/ 2>/dev/null && echo "fetched round-3 mac logs"
