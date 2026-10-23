#!/usr/bin/env bash
# Stage 3 of mac_jobs.sh on its own: every v5 candidate at 8,640 steps on the 30 public scenarios.
set -u
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "[$(date)] stage 3 (restart): v5 candidates at full length on the public scenarios" | tee -a "$LOG/mac_chain.log"
for f in policy_candidates/c*.json; do
  n=$(basename "$f" .json)
  "$PY" run_eval_parallel.py --policies transfer --policy-file policy_candidates/transfer_policy_v5.py \
      --params-json "$f" --steps 8640 --results-dir "../results/full_v5/$n" --workers 14 > "$LOG/mac_full_v5_$n.log" 2>&1
  echo "[$(date)] stage 3: $n done rc=$? $(grep -E '^==' "$LOG/mac_full_v5_$n.log" | tail -1)" | tee -a "$LOG/mac_chain.log"
done
echo "[$(date)] mac chain done" | tee -a "$LOG/mac_chain.log"
