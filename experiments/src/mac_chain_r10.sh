#!/bin/bash
# Round 10 (Mac): start the next mac_runner_r9.py batch only after the previous runner has exited and none of our
# simulator workers is left (guards against the round-9 chaining error that briefly ran 5 workers).
#   nohup bash mac_chain_r10.sh <prev_runner_pid> <jobs.json> <state_dir> <log> > <chain_log> 2>&1 &
# One pid only (a number); the check counts our run_scenario.py workers by their script path.
set -u
PREV="$1"; JOBS="$2"; STATE="$3"; LOG="$4"
case "$PREV" in ''|*[!0-9]*) echo "bad pid '$PREV'"; exit 2;; esac
R10=~/neurips/sb/r10
while kill -0 "$PREV" 2>/dev/null; do sleep 30; done
echo "$(date '+%F %T') runner $PREV gone"
while true; do
  n=$(pgrep -f "neurips/sb/r9/src/run_scenario.py" | wc -l | tr -d ' ')
  r=$(pgrep -f "mac_runner_r9.py" | wc -l | tr -d ' ')
  free=$(memory_pressure | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  if [ "$n" -eq 0 ] && [ "$r" -eq 0 ] && [ "${free:-0}" -ge 30 ] && [ ! -e ~/neurips/GPU_LOCK ]; then break; fi
  echo "$(date '+%F %T') waiting: workers=$n runners=$r free=$free"
  sleep 60
done
cd "$R10" || exit 1
nohup ~/neurips/sb/kit/.venv/bin/python "$R10/mac_runner_r9.py" --jobs "$JOBS" --state "$STATE" --workers 3 > "$LOG" 2>&1 &
echo "$(date '+%F %T') started runner pid $! for $JOBS (free $free%)"
