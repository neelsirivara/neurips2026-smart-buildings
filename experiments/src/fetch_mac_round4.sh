#!/usr/bin/env bash
# Copy the Mac's round-4 result trees (results/round4/<tag>/...) into experiments/results/mac/round4/ and the
# round-4 Mac logs into experiments/results/logs/mac/.  Safe to re-run (whole-tree copy via a tar stream).
#   usage: fetch_mac_round4.sh [tag ...]     default: screen full
set -u
cd "$(dirname "$0")/../results"
mkdir -p mac/round4 logs/mac
[ $# -eq 0 ] && set -- screen full
for d in "$@"; do
  if ssh -o BatchMode=yes mac "test -d ~/neurips/sb/experiments/results/round4/$d"; then
    rm -rf "mac/round4/$d.tmp" && mkdir -p "mac/round4/$d.tmp"
    ssh -o BatchMode=yes mac "cd ~/neurips/sb/experiments/results/round4/$d && tar czf - ." | tar xzf - -C "mac/round4/$d.tmp" \
      && rm -rf "mac/round4/$d" && mv "mac/round4/$d.tmp" "mac/round4/$d"
    echo "fetched round4/$d: $(find mac/round4/$d -name summary.json | wc -l) summary files"
  fi
done
scp -q "mac:~/neurips/logs/r4_*.log" logs/mac/ 2>/dev/null && echo "fetched round-4 mac logs"
