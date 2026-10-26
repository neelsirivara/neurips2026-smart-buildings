#!/usr/bin/env bash
# Round 5: poll `kaggle competitions submissions` every 10 min until none of the given refs is PENDING.
# Appends each poll to experiments/results/round5/kaggle_poll.log.   Usage: kaggle_poll_submissions.sh <ref> [<ref> ...]
K="$USERPROFILE/.kaggle-cli-venv/Scripts/kaggle.exe"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="$ROOT/experiments/results/round5/kaggle_poll.log"
while true; do
  out=$("$K" competitions submissions neurips-2026-smart-buildings 2>&1)
  { echo "== $(date -u +%FT%TZ)"; echo "$out" | head -12; } >> "$LOG"
  left=0
  for r in "$@"; do
    line=$(echo "$out" | grep "^$r ")
    case "$line" in *PENDING*|"") left=$((left+1));; esac
  done
  if [ $left -eq 0 ]; then
    for r in "$@"; do echo "$out" | grep "^$r "; done
    exit 0
  fi
  sleep 600
done
