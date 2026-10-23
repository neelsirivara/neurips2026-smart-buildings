# Smart Buildings Challenge (SB26) -- STATUS

Last updated: 2026-10-22 21:55 PDT (INTERIM snapshot: final evaluation running in the background;
see "If this session dies" below)

## Environment
- Kit copy: `kit/` (clone of the official starter kit, untouched except for `.venv` and the two
  generated held-out buildings under `kit/smart_buildings/heldout_buildings|heldout_scenarios`).
- Python 3.12.15 venv at `kit/.venv` (uv-managed CPython; `uv` itself is not on PATH), pins from
  `kit/pyproject.toml` (numpy 2.0.2, numba 0.60.0, gymnasium 1.2.0, pandas 2.3.3 ...).
- Simulator speed (this laptop, other jobs running): 0.07 s/step (30 zones) to 0.23 s/step (85 zones);
  a full 8,640-step scenario takes 10-35 min. All long runs write per-scenario `summary.json`
  checkpoints and resume; `run_eval_parallel.py --retries 2` re-runs a scenario whose process
  died (one transient `cv2.connectedComponentsWithStats` "Unknown C++ exception" was seen when
  several workers started at once).
- Determinism: occupancy RNG seeded (17321) and convection seeded (5) in the kit, so a given
  (policy, scenario) run is reproducible locally. Local pid_water re-runs are 1-4% more negative
  than the organizers' `baseline_returns.json`, so the local-vs-official gap is reported explicitly
  and paired comparisons use local re-runs.

## Policy (submission/transfer_policy.py) -- SADR v4, tuned parameters BAKED
Schedule-Aware Demand-based Reset: occupancy-gated OCCUPIED / PRECONDITION / SETBACK modes with
holiday detection and a self-tuning optimum-start lead; per-zone PI loops on net heat (W)
translated to damper flow via the supply-air temperature and to reheat valve position via the
water capacity rate and the 308.15 K discharge limit; SAT reset from the coldest supply any
cooling zone needs at floor pressure; static pressure trim-and-respond; proportional economiser
with fan break-even; loop dP reset to the most-open valve; hot water held hot in heating season;
setback handled by burst heating/cooling with hysteresis (v4) instead of PI-held floors (v3).

Tuning (P2) is COMPLETE: seeded random search, 16 distinct configurations (default + 15 random
perturbations; one of the 16 draws reproduced the default) on 6 screening scenarios x 1,440
steps (`experiments/results/tune/tune_log.json`). Best = `89f4d5a115`, screening score 0.00849 vs
default 0.00947; it differs from the default in ki_w_per_k_step 60->120, margin_pre 0.5->0.8,
sat_mix_floor 290->292, sb_hyst_k 1.5->1.0. The three best configurations all have ki=120.
Coordinate descent was NOT run (compute went to the full evaluation). The best values are baked
into `DEFAULT_PARAMS` (`bake_params.py`, verified "mismatches after bake: none"); provenance copy
in `submission/best_params.json` and `experiments/results/tune/best_params.json`.

## Runs
- RUNNING (started 2026-10-22 21:42 PDT, `experiments/src/run_final_eval.sh`, 4 workers,
  log `experiments/results/logs/final_full.log` then `final_heldout.log`, chain log
  `final_chain.log`):
  1. `experiments/results/full/`: transfer (baked) + pid_water on all 30 public scenarios at
     8,640 steps with timeseries (pid_water already done for 6 scenarios from 2026-10-21).
  2. `experiments/results/heldout/`: transfer + pid_water on the 10 generated held-out scenarios
     (building_0501: 5 AHUs, 2 floors, 1 occupant/zone; building_0502: 4 AHUs, 3 floors; weather
     strips atlanta_7, denver_4, fairbanks_6, phoenix_7, singapore_5 / atlanta_4, denver_1,
     fairbanks_3, phoenix_2, singapore_2 -- none of them in the public set).
- NEXT (`experiments/src/run_post_chain.sh`): pid_water on the 6 screening scenarios at 1,440
  steps (`results/tune_baseline`), ablation of the 4 tuned parameters on the screening set
  (`ablation.py` -> `results/tune/ablation.json`), optionally the other three baselines at full
  length (`RUN_OTHER_BASELINES=1`, ~8 h).
- Then: `score_all.py` (full -> final_scores.json; heldout -> heldout_scores.json), `env_info.py`,
  `make_macros.py`, `make_figures.py --trace building_train_8/fairbanks_8 --trace-day 8`,
  `kit/score_leaderboard.py` for the official number, paper build, AUDIT.md, REVIEW_1.md.
- Earlier: `experiments/results/dev_full/` (v3 snapshot, b8/fairbanks_8: -244.9 vs organizer
  pid_water -667.3), `dev576/` (2-day shakedowns), `tune/` (sweep), `smoke*/`.

## If this session dies
Everything resumes: re-run `bash experiments/src/run_final_eval.sh` (skips finished scenarios),
then `bash experiments/src/run_post_chain.sh`, then the scoring/paper commands above. Do not
re-tune; do not change `submission/transfer_policy.py` (baked, final).

## Paper
- `paper/main.tex` drafted (NeurIPS 2026 style, `[sglblindworkshop,final]` + `\workshoptitle`
  because `[final]` alone leaves the track name undefined in the official .sty); compiles with
  placeholder macros (`\textbf{??}`) until results exist. Table 1 = ours, local pid_water, and the
  four organizer-provided baselines; Appendix A = per-scenario table (auto-generated).
  `paper/refs.bib` holds only entries verified in `paper/bib_verification_log.json`.

## To do (user)
- Join the Kaggle competition (https://www.kaggle.com/competitions/neurips-2026-smart-buildings),
  read the official notebook template (not readable without login), paste `submission/transfer_policy.py`
  as described in `submission/README.md`, run once on the public scenarios, submit.
- Poster-round paper on OpenReview (group NeurIPS.cc/2026/Workshop/SB26_Challenge) by 2026-11-13:
  fill in name/affiliation in `paper/main.tex`, check the Overleaf template
  (https://www.overleaf.com/project/6ace893ebb021a3e1807b140) for any page limit, upload `paper/main.pdf`.

## Risks
- Kaggle's held-out buildings may use different valve/plant constants than the kit (the policy
  degrades gracefully: PI loops still regulate, proportional path mis-scaled).
- Local-vs-official gap (1-4% on pid_water) means Kaggle numbers will differ slightly.
- Compute: ~45 core-hours of simulation planned; interruptions resume from per-scenario checkpoints.
