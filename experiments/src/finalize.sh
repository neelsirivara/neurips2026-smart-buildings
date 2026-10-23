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
echo "== score"
"$PY" score_all.py --results-dir ../results/final --ours transfer --baselines transfer_v4 pid_water pid fixed_setpoint bang_bang \
    --out ../results/final_scores.json --label "Mac, final policy (v5) and all baselines"
"$PY" score_all.py --results-dir ../results/final_heldout --ours transfer --baselines transfer_v4 pid_water \
    --out ../results/heldout_scores.json --label "Mac, generated held-out buildings"
"$PY" score_all.py --results-dir ../results/full --ours transfer --baselines pid_water pid fixed_setpoint bang_bang \
    --out ../results/final_scores_local.json --label "laptop, v4 baked"
"$PY" score_all.py --results-dir ../results/heldout --ours transfer --baselines pid_water \
    --out ../results/heldout_scores_local.json --label "laptop, v4 baked, generated buildings"
echo "== analysis (final tree, time series)"
"$PY" analyze_final.py --results-dir ../results/final --out ../results/analysis.json
"$PY" analyze_final.py --results-dir ../results/full --out ../results/analysis_v4_local.json
"$PY" env_info.py > /dev/null
"$PY" compare_candidates.py > ../results/candidates_ranking.txt
echo "== macros + figures"
"$PY" make_macros.py
"$PY" make_audit.py
"$PY" make_figures.py --results-dir ../results/final --scores ../results/final_scores.json \
    --held-scores ../results/heldout_scores.json --analysis ../results/analysis.json \
    --trace building_train_8/fairbanks_8 --trace-day 8
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
