#!/usr/bin/env bash
# Final-policy runs on the Mac, after the v5 winner is chosen and baked into
# submission/transfer_policy.py (copied over with scp before this runs):
#   results/final          winner + pid_water on the 30 public scenarios, 8,640 steps, WITH time series
#   results/final_heldout  winner + pid_water on the 10 generated held-out scenarios, 8,640 steps
# 14 workers; resumable.
set -u
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "[$(date)] final: public" | tee -a "$LOG/mac_final_chain.log"
"$PY" run_eval_parallel.py --policies transfer pid_water --steps 8640 --results-dir ../results/final \
    --workers 14 --save-ts > "$LOG/mac_final.log" 2>&1
echo "[$(date)] final: public rc=$?" | tee -a "$LOG/mac_final_chain.log"
echo "[$(date)] final: held-out" | tee -a "$LOG/mac_final_chain.log"
"$PY" run_eval_parallel.py --policies transfer pid_water --steps 8640 --results-dir ../results/final_heldout \
    --scenarios-dir ../../kit/smart_buildings/heldout_scenarios --workers 14 > "$LOG/mac_final_heldout.log" 2>&1
echo "[$(date)] final: held-out rc=$?" | tee -a "$LOG/mac_final_chain.log"
echo "[$(date)] mac final done" | tee -a "$LOG/mac_final_chain.log"
