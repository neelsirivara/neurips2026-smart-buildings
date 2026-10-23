#!/usr/bin/env bash
# Cheap follow-ups after run_final_eval.sh (all resumable, 4 workers at most):
#   1. pid_water on the six tuning screening scenarios at 1,440 steps (reference for the
#      screening scores in the tuning figure/paragraph)            -> results/tune_baseline
#   2. ablation of the four tuned parameters on the screening set  -> results/tune/ablation.json
#   3. (optional, long) the other three organizer baselines on the 30 public scenarios
#      at 8,640 steps; skipped unless RUN_OTHER_BASELINES=1          -> results/full
set -u
cd "$(dirname "$0")"
PY=../../kit/.venv/Scripts/python.exe
LOG=../results/logs
mkdir -p "$LOG"
echo "[$(date)] post 1: pid_water on the screening set" | tee -a "$LOG/post_chain.log"
"$PY" run_eval_parallel.py --policies pid_water --steps 1440 --results-dir ../results/tune_baseline --workers 4 \
    --scenarios building_train_8/fairbanks_8 building_train_1/denver_7 building_train_2/atlanta_3 \
                building_train_8/phoenix_4 building_train_1/singapore_8 building_train_5/fairbanks_5 \
    >> "$LOG/post_tune_baseline.log" 2>&1
echo "[$(date)] post 1 rc=$?" | tee -a "$LOG/post_chain.log"
echo "[$(date)] post 2: ablation" | tee -a "$LOG/post_chain.log"
"$PY" ablation.py --workers 4 >> "$LOG/post_ablation.log" 2>&1
echo "[$(date)] post 2 rc=$?" | tee -a "$LOG/post_chain.log"
if [ "${RUN_OTHER_BASELINES:-0}" = "1" ]; then
  echo "[$(date)] post 3: pid / fixed_setpoint / bang_bang on the public scenarios" | tee -a "$LOG/post_chain.log"
  "$PY" run_eval_parallel.py --policies pid fixed_setpoint bang_bang --steps 8640 --results-dir ../results/full \
      --workers 4 >> "$LOG/post_other_baselines.log" 2>&1
  echo "[$(date)] post 3 rc=$?" | tee -a "$LOG/post_chain.log"
fi
echo "[$(date)] post chain done" | tee -a "$LOG/post_chain.log"
