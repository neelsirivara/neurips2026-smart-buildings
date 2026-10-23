#!/usr/bin/env bash
# Round 3, stage 2 on the Mac: ONE chosen v6 parameter set at full length (8,640 steps) with
# diagnostics on the 30 public scenarios, the 10 previous held-out scenarios and the 30 new
# held-out scenarios.  Resumable.  The results are the paper's `transfer` policy after
# assemble_round3_tree.py.
#   usage: mac_round3_full.sh <candidate name, e.g. r3_c00_v6_default> [tag, default v6] [sets: "public heldout r3"]
#   workers per set from W_PUB (12), W_HELD (10), W_R3 (8)
set -u
CAND=${1:?candidate name}
TAG=${2:-v6}
SETS=${3:-"public heldout r3"}
W_PUB=${W_PUB:-12}; W_HELD=${W_HELD:-10}; W_R3=${W_R3:-8}
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
R=../results/round3
PF=policy_candidates/transfer_policy_v6.py
PJ=policy_candidates/$CAND.json
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for SET in $SETS; do
  case $SET in
    public)  SD=../../kit/smart_buildings/training_scenarios; W=$W_PUB ;;
    heldout) SD=../../kit/smart_buildings/heldout_scenarios; W=$W_HELD ;;
    r3)      SD=../../kit/smart_buildings/heldout_scenarios_r3; W=$W_R3 ;;
    *) echo "unknown set $SET"; exit 2 ;;
  esac
  echo "[$(date)] r3 full ($CAND -> final_${TAG}_$SET, $W workers)" | tee -a "$LOG/r3_chain.log"
  "$PY" run_eval_parallel.py --runner diag --policies transfer --policy-file $PF --params-json $PJ --steps 8640 \
      --results-dir "$R/final_${TAG}_$SET" --scenarios-dir $SD --workers $W > "$LOG/r3_full_${TAG}_$SET.log" 2>&1
  echo "[$(date)] r3 full: $SET rc=$? $(grep -E '^==' $LOG/r3_full_${TAG}_$SET.log | tail -1)" | tee -a "$LOG/r3_chain.log"
done
echo "[$(date)] r3 full ($CAND: $SETS) done" | tee -a "$LOG/r3_chain.log"
