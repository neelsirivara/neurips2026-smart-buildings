#!/usr/bin/env bash
# Final evaluation chain (resumable; every scenario checkpoints its own summary.json):
#   1. SADR (baked parameters) + pid_water on the 30 public scenarios, 8,640 steps
#   2. SADR + pid_water on the 10 generated held-out scenarios (buildings 0501/0502)
# Four worker processes at most (the machine is shared). Re-running this script skips
# finished scenarios.
set -u
cd "$(dirname "$0")"
PY=../../kit/.venv/Scripts/python.exe
LOG=../results/logs
mkdir -p "$LOG"
echo "[$(date)] phase 1: public scenarios" | tee -a "$LOG/final_chain.log"
"$PY" run_eval_parallel.py --policies transfer pid_water --steps 8640 --results-dir ../results/full \
    --workers 4 --save-ts >> "$LOG/final_full.log" 2>&1
echo "[$(date)] phase 1 rc=$?" | tee -a "$LOG/final_chain.log"
echo "[$(date)] phase 2: held-out generated buildings" | tee -a "$LOG/final_chain.log"
"$PY" run_eval_parallel.py --policies transfer pid_water --steps 8640 --results-dir ../results/heldout \
    --scenarios-dir ../../kit/smart_buildings/heldout_scenarios --workers 4 --save-ts >> "$LOG/final_heldout.log" 2>&1
echo "[$(date)] phase 2 rc=$?" | tee -a "$LOG/final_chain.log"
echo "[$(date)] chain done" | tee -a "$LOG/final_chain.log"
