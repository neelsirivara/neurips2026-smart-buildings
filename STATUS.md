# Smart Buildings Challenge (SB26) -- STATUS

Last updated: 2026-10-23 07:05 PDT. State: COMPLETE for the poster round -- final policy baked,
all evaluations finished on both machines, paper built (0 errors, 0 `??`), audit and self-review
written. Open items are the user's (Kaggle submission, OpenReview upload with name).

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private; `kit/` and the
per-scenario time series are git-ignored; `.git`, `.gitignore`, `LICENSE`, `.github` and the
top-level `README.md` are managed by `make_repos.py` and were not edited here). Nothing was
committed or pushed from this session.

## Headline numbers (leaderboard metric = mean over scenarios of |mean per-step reward|, lower is better)
| set | SADR v5 (final) | SADR v4 | pid_water (same machine) | ratio v5/pid_water [95% CI] | wins |
|---|---|---|---|---|---|
| 30 public scenarios, 8,640 steps (Mac) | **0.00831** | 0.00920 | 0.05498 | 0.151 [0.117, 0.188] | 30/30 |
| 10 generated held-out scenarios (Mac, run once after selection) | **0.01109** | 0.01138 | 0.03989 | 0.278 [0.175, 0.355] | 10/10 |

- Official scorer (`kit/score_leaderboard.py` on `experiments/results/final`): LEADERBOARD SCORE =
  0.00831 over 30 scenarios; shipped baselines on the same scenarios: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520 (`experiments/results/score_leaderboard_final.txt`).
- Local re-runs of all four baselines on the Mac: pid_water 0.05498, pid 0.06782,
  fixed_setpoint 0.06550, bang_bang 0.22453. Local pid_water is -1.7% vs the shipped values on
  average (range -12.7% to +4.6% per scenario).
- v4 -> v5 on the public set: -9.7% (CI 5.1% to 15.2%), 19/30 wins, gain in Phoenix (-0.0020) and
  Singapore (-0.0018); on the held-out set -0.00030 (CI [-0.00071, +0.00006], 6/10) -- not
  significant, reported as such.
- By station (v5, public): Fairbanks 0.0175, Phoenix 0.0075, Singapore 0.0060, Atlanta 0.0055,
  Denver 0.0050. Comfort regret is 4.2% of our loss (3.2% of occupied zone-steps out of band);
  pid_water: 71.5% regret share, 61.5% out of band. 25% of our loss falls on unoccupied steps
  (38% in Fairbanks); the biggest hourly spend is hour 5 (12.5% of the day).
- Cross-machine check: v4 on the laptop 0.00920 vs the Mac 0.00920, per-scenario relative
  difference 0.000% (pid_water 0.017%).
- Kaggle public leaderboard (coordinator's read, 2026-10-22, `experiments/results/kaggle_leaderboard_2026-10-22.json`):
  #1 0.00578, #8 0.00647, #30 0.00996, #49 0.01056 on held-out buildings (33% public split) --
  same formula, not directly comparable; our public-set 0.00831 is 1.4x the leader.

## Final policy (`submission/transfer_policy.py`, SADR v5)
Schedule-Aware Demand-based Reset: occupancy-gated OCCUPIED / PRECONDITION / SETBACK modes with
holiday detection and a self-tuning optimum-start lead; per-zone PI loops on net heat (W)
translated to damper flow via the supply-air temperature and to reheat valve position via the
water capacity rate and the 308.15 K discharge limit; coldest supply air (285 K) whenever a
handler cools (v5; the coil load is q + flow x (mixed - zone) and the COP is constant, so lower
flow is strictly cheaper), 292 K floor on handlers that also heat; static pressure trim-and-respond
in closed form; proportional economiser with the fan break-even; loop dP reset to the most-open
valve; hot water 350 K in heating season; setback by burst heating/cooling against a floor widened
by 8 K below / 6 K above the eco band (v5; v4: 4/2 K). Pure numpy + stdlib, ~0.5 ms per step,
deterministic, shape-agnostic, every action slot written and clipped.

Parameter provenance: random search (16 configurations, 6 screening scenarios x 1,440 steps,
2026-10-21/22; ki_w_per_k_step 60 -> 120 is the whole gain, -9.8% alone; margin_pre 0.8,
sat_mix_floor 292, sb_hyst_k 1.0 are individually neutral, see `experiments/results/tune/ablation.json`),
then 13 analysis-driven candidates (`experiments/src/policy_candidates/`) screened and ALL run at
full length on the 30 public scenarios on the Mac (`experiments/results/mac/full_v5/`,
`experiments/results/candidates_summary.json`, ranking in `candidates_ranking.txt`); winner
`c10_satcold_night8_hi6` = sat_cool_hi 285, night_low_ext 8, night_high_ext 6 (0.00831; the next
two, c09 and c06, are within 0.00002). The v5 code change is one line (the mixed-handler SAT floor
no longer depends on the cooling ceiling); with v4 values it reproduces v4 exactly (0.00920).
Baked with `bake_params.py` ("mismatches after bake: none"); `submission/best_params.json` =
`experiments/results/tune/best_params.json`; v4 set kept as `tune/best_params_v4.json`.
The submitted file differs from the one that produced the Mac results only by a comment on the
`sat_cool_hi` line (synced back to the Mac afterwards).

## Machines
- `laptop`: this Windows laptop (8 cores shared; <= 4 simulator processes; 0.05-0.23 s/step).
  Runs: `experiments/results/full` (v4 + pid_water, 30 scenarios, with time series),
  `heldout` (v4 + pid_water, 10 scenarios), `tune` (random search), `dev*`, `smoke*`.
- `mac`: `ssh mac`, Apple M5 Pro, 18 cores, 48 GB, kit clone + uv venv (Python 3.12.15, same
  pins), ~6x faster per step; layout mirrors this tree at `~/neurips/sb` (`kit` -> clone); results
  copied back with `experiments/src/fetch_mac_results.sh` into `experiments/results/mac/`
  (summary.json only, plus time series for `mac/final`). Runs: `mac_jobs.sh` stage 1 (screening
  reference, v5 sweep, ablation), stage 2 (v4 + 4 baselines public; v4 + pid_water held-out),
  `mac_stage3.sh` (13 candidates at full length), `mac_final.sh` (v5 + pid_water public WITH time
  series, and held-out). Mac logs mirrored to `experiments/results/logs/mac/`.
- Paper trees: `experiments/results/final` and `final_heldout` (assembled from the Mac runs by
  `assemble_final_tree.py`: transfer = v5, transfer_v4 = v4, pid_water/pid/fixed_setpoint/bang_bang);
  the laptop trees are the cross-machine check.

## Deliverables (all present)
1. `submission/transfer_policy.py` (v5, baked), `submission/README.md` (paste-in steps for the
   Kaggle notebook, repo link), `submission/kaggle_notebook_template.py` (smoke-tested against the
   local kit with the final policy), `submission/best_params.json`.
2. `experiments/results/final_scores.json`, `heldout_scores.json`, `final_scores_local.json`,
   `heldout_scores_local.json`, `analysis.json`, `analysis_v4_local.json`, `candidates_summary.json`,
   `env_info.json`, `score_leaderboard_final.txt`; `paper/results_macros.tex`,
   `per_scenario_table.tex`, `tuning_tables.tex`; `paper/figures/*.pdf|png` (scores dumbbell,
   station decomposition, loss by hour, one-day trace, tuning); `paper/main.pdf` (10 pages: main
   text through page 6, references + Appendices A-C; 0 errors, 0 undefined, 0 `??`, 0 TODO,
   0 overfull boxes); `paper/AUDIT.md` (generated by `make_audit.py`: 24 claims, 0 missing values;
   header in `AUDIT_header.md`); `paper/bib_verification_log.json`; `paper/review/REVIEW_1.md`.
3. This file.

Pipeline (idempotent): `bash experiments/src/finalize.sh` regenerates everything in item 2 from the
result trees.

## Paper
NeurIPS 2026 style, `[sglblindworkshop,final]` + `\workshoptitle` (the official .sty needs a track
option with `[final]`). Sections: Introduction; Environment and metric; Method (topology, modes,
net-heat PI loops, actuator mapping incl. the v5 cold-SAT argument, safeguards, tuning protocol,
parameter table); Results (same-machine Table 2 with all baselines + organizer row, leaderboard
context, decomposition, held-out, candidates); Analysis (why it wins, where the loss sits and what
the revision bought, where it loses, implications); Limitations; Reproducibility and disclosure;
Appendices A (per-scenario tables), B (ablation + candidates), C (algorithm, trace, tuning figure).
Self-review (`paper/review/REVIEW_1.md`): overall 7/10; must-fixes 1-4 applied in this draft
(held-out v5 gain stated as not significant; Fairbanks v4->v5 change not called a gain;
decomposition in shares; main text within six pages); item 5 (author block) is the user's.

## To do (user)
- Kaggle (joined): follow `submission/README.md` -- open the official notebook template, replace
  the policy cell with `submission/transfer_policy.py`, run once on the public scenarios (expect
  the per-scenario totals in `experiments/results/final_scores.json` -> `policies.transfer.per_scenario`,
  a few per cent off if the grader's kit differs), submit. Keep the submitted file identical to
  the one here so the paper's numbers refer to the submitted policy.
- OpenReview poster paper (group NeurIPS.cc/2026/Workshop/SB26_Challenge) by 2026-11-13: fill in
  name/affiliation in `paper/main.tex` (author block), rebuild (`bash experiments/src/finalize.sh`
  or the three pdflatex passes), check the Overleaf template
  (https://www.overleaf.com/project/6ace893ebb021a3e1807b140) for the page limit (the main text is
  six pages), upload `paper/main.pdf`.
- Optional before the January final paper: more generated held-out buildings (the Mac does a
  10-scenario set in 12 min), a diagnosis of the larger generated building (building_0502, ratio
  0.36 vs 0.14 on building_0501), and the Kaggle score once available.

## Risks
- Model selection used the public set at full length: the public number (0.00831) is optimistic;
  the held-out number (0.01109) is the honest estimate and the Kaggle test buildings may differ
  further (the policy degrades gracefully if plant constants differ: PI loops still regulate).
- Public leaderboard leaders (0.0058) are 1.4x below our public-set number; most of our remaining
  loss is heating gas in Fairbanks (physics of 30% outside air at -20 C) and cooling electricity
  in Phoenix/Singapore.
- Local-vs-official pid_water gap (-1.7% mean, up to -12.7% on one scenario) means the organizers'
  kit version may differ slightly from the clone used here.
