#!/usr/bin/env bash
# Copy the Mac's result trees (summary.json files only; no time series are written there) into
# experiments/results/mac/ so that scoring and macros stay local. Safe to re-run.
set -u
cd "$(dirname "$0")/../results"
mkdir -p mac
for d in tune tune_baseline full heldout full_v5 final final_heldout; do
  if ssh -o BatchMode=yes mac "test -d ~/neurips/sb/experiments/results/$d"; then
    rm -rf "mac/$d.tmp"
    scp -q -r "mac:~/neurips/sb/experiments/results/$d" "mac/$d.tmp" && rm -rf "mac/$d" && mv "mac/$d.tmp" "mac/$d"
    echo "fetched $d: $(find mac/$d -name summary.json | wc -l) summary files"
  fi
done
mkdir -p logs/mac
scp -q "mac:~/neurips/logs/mac_*.log" logs/mac/ 2>/dev/null && echo "fetched mac logs"
