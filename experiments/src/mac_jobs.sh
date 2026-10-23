#!/usr/bin/env bash
# Simulator work on the second machine ("mac": Apple M5 Pro, 18 cores). Layout there mirrors
# this tree: ~/neurips/sb/{experiments/src,submission,experiments/results}, kit -> ~/neurips/starter-kit.
# Everything is resumable (per-scenario summary.json checkpoints; tune.py caches by parameter hash).
#   stage 1  pid_water on the 6 screening scenarios (1,440 steps)  -> results/tune_baseline
#            v5 candidate sweep (policy_candidates/c*.json on the v5 code, tag "v5") + ablation
#   stage 2  v4 (baked) + pid_water + pid + fixed_setpoint + bang_bang at 8,640 steps on the
#            30 public scenarios, then v4 + pid_water on the 10 generated held-out scenarios
#   stage 3  every v5 candidate at 8,640 steps on the 30 public scenarios -> results/full_v5/<name>
set -u
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
mkdir -p "$LOG"
SCREEN="building_train_8/fairbanks_8 building_train_1/denver_7 building_train_2/atlanta_3 building_train_8/phoenix_4 building_train_1/singapore_8 building_train_5/fairbanks_5"
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

echo "[$(date)] stage 1: screening reference + v5 sweep + ablation" | tee -a "$LOG/mac_chain.log"
"$PY" run_eval_parallel.py --policies pid_water --steps 1440 --results-dir ../results/tune_baseline --workers 6 \
    --scenarios $SCREEN > "$LOG/mac_tune_baseline.log" 2>&1 &
A=$!
( for f in policy_candidates/c*.json; do
    echo "-- candidate $f"
    "$PY" tune.py eval --params-json "$f" --policy-file policy_candidates/transfer_policy_v5.py --tag v5 --steps 1440 --workers 6
  done
  "$PY" ablation.py --workers 6 ) > "$LOG/mac_candidates.log" 2>&1 &
B=$!
wait $A $B
echo "[$(date)] stage 1 done" | tee -a "$LOG/mac_chain.log"

echo "[$(date)] stage 2: full length, public (5 policies) then held-out (2 policies)" | tee -a "$LOG/mac_chain.log"
"$PY" run_eval_parallel.py --policies transfer pid_water pid fixed_setpoint bang_bang --steps 8640 \
    --results-dir ../results/full --workers 14 > "$LOG/mac_full.log" 2>&1
"$PY" run_eval_parallel.py --policies transfer pid_water --steps 8640 --results-dir ../results/heldout \
    --scenarios-dir ../../kit/smart_buildings/heldout_scenarios --workers 14 > "$LOG/mac_heldout.log" 2>&1
echo "[$(date)] stage 2 done" | tee -a "$LOG/mac_chain.log"

echo "[$(date)] stage 3: v5 candidates at full length on the public scenarios" | tee -a "$LOG/mac_chain.log"
for f in policy_candidates/c*.json; do
  n=$(basename "$f" .json)
  "$PY" run_eval_parallel.py --policies transfer --policy-file policy_candidates/transfer_policy_v5.py \
      --params-json "$f" --steps 8640 --results-dir "../results/full_v5/$n" --workers 14 > "$LOG/mac_full_v5_$n.log" 2>&1
  echo "[$(date)] stage 3: $n done rc=$?" | tee -a "$LOG/mac_chain.log"
done
echo "[$(date)] mac chain done" | tee -a "$LOG/mac_chain.log"
