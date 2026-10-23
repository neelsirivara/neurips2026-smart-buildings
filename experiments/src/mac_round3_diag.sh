#!/usr/bin/env bash
# Round 3, stage 1 on the Mac: the shipped v5 policy with per-step diagnostics (run_diag.py) at full
# length on the 30 public scenarios, the 10 previous held-out scenarios and the 30 new held-out
# scenarios (6 generated buildings, kit/smart_buildings/heldout_scenarios_r3), plus pid_water on the
# new set. 12 workers for the small buildings, 8 for the large ones (3 GB RSS each). Resumable.
set -u
cd ~/neurips/sb/experiments/src
PY=../../kit/.venv/bin/python
LOG=~/neurips/logs
R=../results/round3
mkdir -p "$LOG" "$R"
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "[$(date)] r3 diag: v5 public" | tee -a "$LOG/r3_chain.log"
"$PY" run_eval_parallel.py --runner diag --policies transfer --steps 8640 --results-dir "$R/diag_v5_public" \
    --workers 12 > "$LOG/r3_diag_public.log" 2>&1
echo "[$(date)] r3 diag: v5 public rc=$? $(grep -E '^==' $LOG/r3_diag_public.log | tail -1)" | tee -a "$LOG/r3_chain.log"
echo "[$(date)] r3 diag: v5 held-out (0501, 0502)" | tee -a "$LOG/r3_chain.log"
"$PY" run_eval_parallel.py --runner diag --policies transfer --steps 8640 --results-dir "$R/diag_v5_heldout" \
    --scenarios-dir ../../kit/smart_buildings/heldout_scenarios --workers 12 > "$LOG/r3_diag_heldout.log" 2>&1
echo "[$(date)] r3 diag: v5 held-out rc=$? $(grep -E '^==' $LOG/r3_diag_heldout.log | tail -1)" | tee -a "$LOG/r3_chain.log"
echo "[$(date)] r3 diag: v5 + pid_water on the 30 new held-out scenarios" | tee -a "$LOG/r3_chain.log"
"$PY" run_eval_parallel.py --runner diag --policies transfer pid_water --steps 8640 --results-dir "$R/diag_v5_r3" \
    --scenarios-dir ../../kit/smart_buildings/heldout_scenarios_r3 --workers 8 > "$LOG/r3_diag_r3.log" 2>&1
echo "[$(date)] r3 diag: new held-out rc=$? $(grep -E '^==' $LOG/r3_diag_r3.log | tail -2 | tr '\n' ' ')" | tee -a "$LOG/r3_chain.log"
echo "[$(date)] r3 diag chain done" | tee -a "$LOG/r3_chain.log"
