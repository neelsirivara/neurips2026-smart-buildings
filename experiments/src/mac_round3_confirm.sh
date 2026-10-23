#!/usr/bin/env bash
# Round 3, confirmation chain on the Mac (run under nohup; every stage is resumable because
# run_eval_parallel.py skips scenarios whose summary.json exists):
#   1. the chosen v6 variant at full length (8,640 steps, diagnostics on) on the 30 public, the 10
#      previous held-out and the 30 new held-out scenarios -> results/round3/final_v6_{public,heldout,r3}
#   2. (ledger only) the v6 defaults r3_c00 on the two held-out sets -> results/round3/final_c00_{heldout,r3}
#      (r3_c00 on the public set was run on the laptop: results/round3/laptop_full_c00_public)
#   usage: nohup bash mac_round3_confirm.sh <candidate> > ~/neurips/logs/r3_confirm.out 2>&1 &
set -u
CAND=${1:?candidate name}
cd ~/neurips/sb/experiments/src
LOG=~/neurips/logs
echo "[$(date)] confirm chain: $CAND (v6) public heldout r3, then r3_c00 heldout r3" | tee -a "$LOG/r3_chain.log"
W_PUB=12 W_HELD=10 W_R3=10 bash mac_round3_full.sh "$CAND" v6 "public heldout r3"
W_HELD=10 W_R3=10 bash mac_round3_full.sh r3_c00_v6_default c00 "heldout r3"
echo "[$(date)] confirm chain done" | tee -a "$LOG/r3_chain.log"
