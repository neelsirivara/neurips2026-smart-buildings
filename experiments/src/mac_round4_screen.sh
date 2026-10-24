#!/usr/bin/env bash
# Round 4 on the Mac: held-26 screen of all single-change candidates at 2,880 steps (resumable).
#   usage: nohup bash mac_round4_screen.sh <workers> <candidates...> > ~/neurips/logs/r4_screen.out 2>&1 &
set -u
W=${1:?workers}; shift
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "[$(date)] r4 screen held-26: $* ($W workers)" | tee -a "$LOG/r4_chain.log"
"$PY" screen_round4.py run --sets held --steps 2880 --workers "$W" --candidates "$@" > "$LOG/r4_screen_held.log" 2>&1
echo "[$(date)] r4 screen held-26 rc=$? $(tail -n 1 $LOG/r4_screen_held.log)" | tee -a "$LOG/r4_chain.log"
