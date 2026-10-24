#!/usr/bin/env bash
# Everything after the simulator runs, in order (idempotent):
#   results/final, results/final_heldout   assembled from the Mac trees (assemble_final_tree.py)
#   final_scores.json, heldout_scores.json, final_scores_local.json, heldout_scores_local.json
#   analysis.json (final tree, with time series), env_info.json, candidates_summary.json
#   paper/results_macros.tex, per_scenario_table.tex, tuning_tables.tex, figures/, main.pdf
#   kit/score_leaderboard.py on the final tree (the official formula and printout)
set -u
cd "$(dirname "$0")"
PY=../../kit/.venv/Scripts/python.exe
[ -x "$PY" ] || PY=../../kit/.venv/bin/python
set -e
echo "== assemble final trees"
"$PY" assemble_final_tree.py
"$PY" assemble_round3_tree.py
echo "== score"
"$PY" score_all.py --results-dir ../results/final --ours transfer --baselines transfer_v5 transfer_v4 pid_water pid fixed_setpoint bang_bang \
    --out ../results/final_scores.json --label "Mac, final policy (v6, round 3), v5, v4 and all baselines"
"$PY" score_all.py --results-dir ../results/final_heldout --ours transfer --baselines transfer_v5 transfer_v4 pid_water \
    --out ../results/heldout_scores.json --label "Mac, generated held-out buildings (0501, 0502)"
if [ -d ../results/final_heldout_r3 ]; then
"$PY" score_all.py --results-dir ../results/final_heldout_r3 --ours transfer --baselines transfer_v5 pid_water \
    --out ../results/heldout_r3_scores.json --label "Mac, six generated held-out buildings (round 3)"
fi
"$PY" score_all.py --results-dir ../results/full --ours transfer --baselines pid_water pid fixed_setpoint bang_bang \
    --out ../results/final_scores_local.json --label "laptop, v4 baked"
"$PY" score_all.py --results-dir ../results/heldout --ours transfer --baselines pid_water \
    --out ../results/heldout_scores_local.json --label "laptop, v4 baked, generated buildings"
echo "== analysis (final tree, time series)"
"$PY" analyze_final.py --results-dir ../results/final --out ../results/analysis.json
"$PY" analyze_final.py --results-dir ../results/full --out ../results/analysis_v4_local.json
"$PY" env_info.py > /dev/null
"$PY" compare_candidates.py > ../results/candidates_ranking.txt
echo "== round 3: loss decomposition, screening summary, candidates ledger"
for pair in "public_v5:mac/round3/diag_v5_public" "heldout_v5:mac/round3/diag_v5_heldout" "heldout_r3_v5:mac/round3/diag_v5_r3" \
            "public_v6:mac/round3/final_v6_public" "heldout_v6:mac/round3/final_v6_heldout" "heldout_r3_v6:mac/round3/final_v6_r3"; do
  name=${pair%%:*}; dir=${pair#*:}
  if [ -d "../results/$dir" ]; then
    "$PY" decompose_loss.py --dirs "../results/$dir" --policy transfer --out "../results/round3/loss_decomposition_$name.json" --label "$name" > /dev/null
  fi
done
"$PY" screen_round3.py summarize --steps 2880 > ../results/round3/screen_ranking.txt 2>&1 || true
"$PY" screen_round3.py summarize --steps 2880 --ref r3_c00_v6_default > ../results/round3/screen_ranking_vs_c00.txt 2>&1 || true
"$PY" ledger_round3.py > /dev/null || true
echo "== round 4: diagnosis of v6, screen summary, full-length confirmation, ledger"
if [ ! -f ../results/round4/diag_round4.json ]; then
  "$PY" diag_cooling_r4.py --dirs ../results/mac/round3/final_v6_public ../results/mac/round3/final_v6_heldout \
      ../results/mac/round3/final_v6_r3 --out ../results/round4/diag_cooling_v6.json > /dev/null
  "$PY" diag_round4.py > /dev/null
fi
"$PY" screen_round4.py summarize --steps 2880 > ../results/round4/screen_ranking.txt 2>&1 || true
R4CAND=$("$PY" -c "import json; print(json.load(open('../results/round4/decision.json')).get('chosen') or '')" 2>/dev/null || true)
if [ -n "$R4CAND" ]; then
  "$PY" confirm_round4.py --cand "$R4CAND" > ../results/round4/confirm_ranking.txt 2>&1 || true
  tail -n 2 ../results/round4/confirm_ranking.txt
  # where the gain comes from: decompositions of v7 and v6 on the three confirmation sets
  R=../results
  for spec in "public_v7:$R/round4/full/$R4CAND/pub30 $R/mac/round4/full/$R4CAND/pub30" \
              "old40_v7:$R/round4/full/$R4CAND/old40 $R/mac/round4/full/$R4CAND/old40" \
              "old40_v6:$R/mac/round3/final_v6_heldout $R/mac/round3/final_v6_r3" \
              "fresh40_v7:$R/round4/full/$R4CAND/fresh40 $R/mac/round4/full/$R4CAND/fresh40" \
              "fresh40_v6:$R/round4/full/r4_c00_v6/fresh40 $R/mac/round4/full/r4_c00_v6/fresh40"; do
    name=${spec%%:*}; dirs=${spec#*:}
    existing=""; for d in $dirs; do [ -d "$d" ] && existing="$existing $d"; done
    [ -n "$existing" ] && "$PY" decompose_loss.py --dirs $existing --policy transfer \
        --out "$R/round4/loss_decomposition_$name.json" --label "$name" > /dev/null 2>&1 || true
  done
fi
"$PY" ledger_round4.py > /dev/null || true
if [ -f assemble_round4_tree.py ]; then "$PY" assemble_round4_tree.py || true; fi
echo "== macros + figures"
"$PY" make_macros.py
"$PY" make_audit.py
"$PY" make_figures.py --results-dir ../results/final --scores ../results/final_scores.json \
    --held-scores ../results/heldout_scores.json --analysis ../results/analysis.json \
    --trace building_train_8/fairbanks_8 --trace-day 8 \
    --decomp "v5=../results/round3/loss_decomposition_public_v5.json" "v6=../results/round3/loss_decomposition_public_v6.json" \
    --heldout-scores-r3 ../results/heldout_r3_scores.json
"$PY" make_figures_r4.py
echo "== official scorer on the final tree"
( cd ../../kit && "./.venv/Scripts/python.exe" score_leaderboard.py ../experiments/results/final --policy transfer --expect 30 \
    > ../experiments/results/score_leaderboard_final.txt 2>&1 || "./.venv/bin/python" score_leaderboard.py ../experiments/results/final --policy transfer --expect 30 > ../experiments/results/score_leaderboard_final.txt 2>&1 )
grep -E "LEADERBOARD|pid_water|scenarios" ../results/score_leaderboard_final.txt | head -4
echo "== paper"
cd ../../paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex > build1.log 2>&1
bibtex main > bibtex.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error main.tex > build2.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error main.tex > build3.log 2>&1
echo "errors: $(grep -c '^!' build3.log)  undefined refs: $(grep -c 'undefined' build3.log)  pages: $(pdfinfo main.pdf | grep Pages | awk '{print $2}')  ??: $(pdftotext main.pdf - | grep -c '??')  TODO: $(pdftotext main.pdf - | grep -c 'TODO')"
