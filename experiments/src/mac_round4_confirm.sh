#!/usr/bin/env bash
# Round 4 on the Mac: full-length (8,640 steps) runs with diagnostics, one global queue, longest first.
#   usage: nohup bash mac_round4_confirm.sh <workers> <candidate:set> ... > ~/neurips/logs/r4_confirm.out 2>&1 &
#   e.g.   mac_round4_confirm.sh 12 r4_c00_v6:fresh40 r4_cXX:fresh40 r4_cXX:pub30 r4_cXX:old40
# Results: results/round4/full/<candidate>/<set>/...; resumable (run_diag.py skips finished scenarios).
set -u
W=${1:?workers}; shift
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "[$(date)] r4 full: $* ($W workers)" | tee -a "$LOG/r4_chain.log"
"$PY" screen_round4.py run --tag full --runner diag --steps 8640 --workers "$W" --pairs "$@" > "$LOG/r4_full.log" 2>&1
echo "[$(date)] r4 full rc=$? $(tail -n 1 $LOG/r4_full.log)" | tee -a "$LOG/r4_chain.log"
