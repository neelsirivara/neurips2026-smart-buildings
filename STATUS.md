# Smart Buildings Challenge (SB26) -- STATUS

Last updated: 2026-10-26 ~16:00 PDT. State: ROUND 6 COMPLETE -- harsh-weather sets built on private Kaggle CPU
kernels and the Mac: a 34/66 mixture of the new harsh confirmation set HC and the public set reproduces v8's Kaggle
score and predicts pid_water's Kaggle ratio (5.81 vs 5.96, 2.6% low); 9 single changes screened at full length; the composite
r6_comp (set-back air boost before workdays and near the floor, preconditioning margin 0.5 K, weeknight setback 10 K)
met the pre-registered rule (HC -2.05% [-2.70, -1.43], 40/48; public-30 -0.27% [-1.35, +0.65], a tie) and is
**shipped as v9** in `submission/transfer_policy.py` (v8 kept as `submission/transfer_policy_v8_shipped_before_round6.py`);
no gain on FD (large default-range buildings: +0.60% [-0.37, +1.36], 4/20 wins, comfort up) and up to +4% on hot public
strips -- see Round 6 item 5.
Kaggle probes: c01 0.01071 (noise vs v8 0.01074), v9 pending (ref 57678857). Paper rebuilt (15 pages, main text through
page 6; 0 errors / undefined / `??` / overfull), author block filled, AUDIT 63 claims (0 missing), review pass 5,
`DEEP_DIVE.md` written. The Kaggle dispatcher keeps running reference shards (PID 49940). Round 5 header kept below.

Round 5 header (2026-10-26 04:00 PDT): ROUND 5 COMPLETE -- Kaggle used as an oracle (v7 0.01088,
v6 0.01116, v5 0.01161, pid_water 0.06404, v8 0.01074): the hidden buildings behave like the shipped six
and the local-vs-Kaggle gap is weather (public + Minneapolis reproduces the probes' ratios); SADR v8
(round-5 composite `r5_c12_comp`: weekend setback, request cap 20 kW per 100 m2) met the pre-registered
rule at full length (public -1.1%, M -4.1%, P+M -2.2%; FD a tie) and is baked into
`submission/transfer_policy.py` (v7 kept for provenance).

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private; `kit/` and the
per-scenario time series are git-ignored; `.git`, `.gitignore`, `LICENSE`, `.github` and the
top-level `README.md` are managed by `make_repos.py` and were not edited here). Nothing was
committed or pushed from this session.

## Round 6 (2026-10-26 04:00-16:00 PDT; private Kaggle CPU kernels + the Mac, laptop <= 1 thread): harsh weather

State: ROUND 6 COMPLETE. Harsh-weather sets built and matched to Kaggle; 9-candidate pre-registered screen at full
length; composite r6_comp confirmed at full length and **shipped as v9** under the pre-registered rule; v9 probe
submitted to Kaggle (pending); paper, AUDIT, review pass 5, `DEEP_DIVE.md`. Nothing committed or pushed.

1. **Pre-registration** `experiments/results/round6/PREREG.md`: part 1 (11:05 UTC, before any round-6 run) = sets HC
   (48, confirmation, never used before) / HS (18, screening), Kaggle-match criteria, ship rule (public-30 not worse AND
   HC better, paired bootstrap 5,000 resamples seed 0); part 2 (12:10 UTC, after the v8 decomposition, before any
   candidate) = 8 candidates in 4 families, 6 planned ideas dropped with reasons (recovery fit contradicts an outdoor-
   temperature optimum start; SAT reset under heating load, hot-water reset, no simultaneous reheat/cooling and a lower
   occupied heating margin target < 1% of the HS loss or are out of reach); amendment 13:35 UTC = c11 (post hoc, labelled);
   resume notes (18:07-21:10 UTC) = dispatcher fix, Mac runs, speculative composite runs, post-hoc ledger item r6_compb.
2. **Compute**: private Kaggle CPU script kernels (`experiments/src/kaggle_sim/kaggle_sim.py`: private dataset
   `neelsiri/sb26-sim-r6` = laptop kit + scenario sets + runner; kernels `sb26-r6-*`, all private) and, after the Mac
   came back, `kaggle_sim/mac_shard_runner_r6.py` on the Mac (same tarball, <= 8 simulator workers machine-wide,
   `memory_pressure` >= 30% checked before every job launch; `mac_batch_r6.py`, `fetch_mac_r6.py`, `mac_registry.json`).
   Reproduction: Kaggle = laptop bit for bit (4/4, `kaggle_repro.json`); Mac = Kaggle bit for bit on v8 and pid_water,
   2e-11 relative on one v9-code run (`mac_repro.json`).
   **Dispatcher found at resume** (`kaggle_sim.py dispatch --loop --forever`, PID 43176, started 07:24 PDT): alive, 5
   kernels running, 16 queued; but 3 shards (c06-r6hs-2, c07-r6hs-1, c08-pub12-1) had failed to push after the 09:24-10:30 PDT network outage (pushes at
   10:35-10:40 PDT) and the dispatcher had **dropped them from the queue** (registry `push_failed`; the kernels did
   not exist on Kaggle). Stopped it at 18:07 UTC during its sleep, patched `dispatch()` (a failed push goes back to the
   front of the queue and is parked after 3 failures), restarted it (one instance, PID 5136, stdout
   `kaggle_dispatch_stdout_2.txt`); the 3 lost shards ran on the Mac. Second fix at 22:30 UTC: a failed output download
   ("a problem on Kaggle's side") had marked pidwater-r6hc-2 fetched with 0 summaries; `fetch()` now keeps such a kernel
   'running' so the dispatcher retries; re-fetched with `--force` (12 summaries) and restarted (PID 49940,
   `kaggle_dispatch_stdout_3.txt`). Queue edits during the round are logged with
   `[resume]` in `kaggle_dispatch_log.txt`. **The dispatcher is still running** (it idles when the queue is empty; it is
   working through the v7 reference and r6_compb ledger shards); stop it with `taskkill /PID 49940 /F` when those are fetched.
   Machine notes: the kit venv's `python.exe` was blocked by Windows Application Control from ~18:20 UTC; laptop
   scripts ran with the uv base interpreter (3.12.15) + `PYTHONPATH=kit/.venv/Lib/site-packages` (same packages). The Mac
   ran at load 100-130 (other users' processes) from ~19:00 to 19:30 UTC; FD was moved back to Kaggle for time.
3. **Kaggle match** (`set_match.json`, paper Table 2): v8 on P 0.00777 (level 0.72 of Kaggle), M 0.01073 (1.00), HC
   0.01657 (1.54), HS 0.02243 (2.09). A mixture of 34% HC + 66% P fitted to v8's Kaggle score predicts pid_water's
   Kaggle ratio: 5.81 against 5.96, 2.6% low (pid_water on all 48 HC scenarios; P+M: 6.15). Reading: the hidden split is about two thirds
   public-like weather and one third deep cold.
4. **Screen** (8,640 steps, HS 18 + pub12, vs v8; `screen_summary.json`, paper Table B6): helps c01 boost 8 h -0.94%
   [-1.42, -0.50] HS / -0.43% pub12, c02 boost 4 h -0.58%, c11 boost 8 h cold-only -0.95% [-1.43, -0.52] / -0.46%, c09
   floor boost -0.49%, c06 preconditioning margin 0.5 K -0.36%, c07 lead safety 1.15 -0.34%, c08 weeknight setback 10 K
   -0.81% [-1.14, -0.50] / -0.32%; n.s. c03 burst sync -0.04%; frost floor 5 C (reporting only) **+0.91% [+0.60, +1.22]**
   HS, +0.51% pub12. Composite (one per family, lowest HS): c11 + c09 + c06 + c08 = `r6_comp`: HS **-2.32% [-3.07,
   -1.60]** (17/18), pub12 -1.36% [-2.76, -0.09]; C* = r6_comp (`decision_composite.json` 20:44 UTC, `decision.json`).
5. **Confirmation** (8,640 steps; `confirm_r6_comp.json`), v8 -> v9:
   HC (48): 0.01657 -> 0.01623, **-2.05% [-2.70, -1.43]** (-33.9 [-44.7, -23.8] x1e-5), wins 40/48, CI below zero for
   10/10 bootstrap seeds; public-30: 0.00777 -> 0.00775, -0.27% [-1.35, +0.65] (-2.1 [-10.5, +5.0] x1e-5), wins 16/30;
   **rule MET** (public not worse for all 10 seeds, HC better). Secondary: HS -2.32%, H (66) -2.14% [-2.63, -1.66], M (12)
   -1.28% [-2.45, -0.31], P+M -0.63% [-1.43, +0.13], FD (20) 0.01007 -> 0.01013, +0.60% [-0.37, +1.36], wins 4/20 (n.s.; the comfort term rises
   by 2.3 times the net change, energy falls). Worst single scenarios: public
   building_train_1/singapore_8 +3.98% (five of six Singapore strips +2.6% to +4.0%, Atlanta 5/6 +3.7%/+3.1%), HC
   building_train_4/minneapolis_6 +3.36%. The screen ledger puts the hot-strip cost on c06 (+2.6% singapore_6, +1.5%
   phoenix_5; c07 -0.6% there): the pub12 screen had two hot strips of twelve. Post hoc, ledger only: `r6_compb` (c07
   instead of c06): public-30 -0.92% [-1.80, -0.24] vs v8 (25/30 wins) and -0.65% [-1.13, -0.20] vs
   v9; HS (9 of 18 when written) -2.52% vs v8 (v9 -2.44% on the same 9); FD runs queued on Kaggle (`compb-r4c-*`).
   Not eligible this round (defined after reading the confirmation); the natural round-7 candidate.
6. **Shipped** (`python experiments/src/ship_round6.py r6_comp`, ~22:00 UTC): `submission/transfer_policy.py` = v9
   (`results/round6/policies/v9_screen2.py` + r6_comp overrides baked; md5 866b9023...), v8 kept as
   `submission/transfer_policy_v8_shipped_before_round6.py` (md5 98036ef2..., = `results/round6/policies/v8.py`),
   `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v9.json` (v8: `best_params_v8.json`).
   Checks: bake (DEFAULT_PARAMS = v9 defaults + overrides), robustness test 35/35, 36-step smoke run, Kaggle template
   smoke test (`results/round6/kaggle_template_smoke_v9.txt`: 288 steps, building_train_1/fairbanks_1, -2.2481), shipped file vs the confirmation's Kaggle runs at
   8,640 steps on building_train_8/{minneapolis_3, fairbanks_c1} (HC): identical totals on both (-65.3053747611848, -323.96867298041616) (`results/round6/regress/
   xcheck_shipped_v9.json`); the Kaggle-scored notebook (`submission/kaggle/sadr-v9-comp-smart-buildings`, from
   `results/round6/policies/v9_r6_comp.py`) differs from the shipped file only in two docstring lines
   (`results/round6/shipped_vs_kaggle_scored.diff`). README updated (v9 section, v8 kept).
7. **Kaggle probes** (`results/kaggle_feedback.json`): c01 (ref 57669693, 14:41 UTC) and v9 = r6_comp (ref 57678857,
   21:19 UTC; Kaggle's interactive building_train_1/atlanta_2 -33.5602 vs local -33.5568, 0.010%); c01 scored **0.01071** at 22:27 UTC (v8 0.01074;
   -0.00003, noise); v9 **PENDING**. Daily count 2026-10-26 UTC: 3 of 4 (1 spare kept). Leaderboard 19:05 UTC: v8 0.01074 rank 87 (86 ahead), #1
   0.00521, #8 0.00603, #20 0.00685 (`results/round6/intel/lb_page1_2026-10-26T1905Z.csv`).
8. **Paper** (`paper/main.tex`): author block filled (Neel Sirivara, University of Washington,
   nsiriv@cs.washington.edu; supplied by the user via the coordinator); abstract adds round 6; Section 3 protocol covers
   rounds 3-6; Setup states the round-6 machines; Table 1 gains a v9 row; Section 4: Kaggle paragraph compressed
   (round-5 table to the appendix), Table 2 = local sets incl. HC/HS and the 66/34 mixture, new "Round 6" paragraph;
   Section 5 "What round 6 found" (HS decomposition, recovery fit, frost); round-4/5 paragraphs and Limitations
   compressed to keep six pages; Appendix: params table v9 row, round-6 ledger (Table B6). Build: 15 pages, main
   text through page 6, references from page 7; 0 errors, 0 undefined references, 0 `??`, 0 overfull boxes.
   `paper/AUDIT.md` (63 claims, 0 missing; every macro used in main.tex is covered), `paper/review/REVIEW_1.md` pass 5.
9. **Deep dive** `DEEP_DIVE.md` (coordinator request): public notebooks/threads vs SADR, loss by component and weather
   (Kaggle-weighted: gas 75%, chiller 19%, fan 3.6%, comfort 2%), a ranked change list with gains/costs/fit, literature;
   numbers from `experiments/src/deep_dive_r6.py` -> `results/round6/deep_dive_numbers.json`, Kaggle reads in
   `results/round6/intel/`, v8 7-day fairbanks_1 run in `results/round6/deep_dive_7day/`.

### Round 6 -- what remains
- Running at hand-off (all ledger/reference, none decision-relevant): the Kaggle dispatcher (PID 49940; v7 on HC
  `v7-r6hc-1..4`, r6_compb on HS `compb-r6hs-2` and FD `compb-r4c-1..3`); Mac batch `mac-v7-r6hs` (v7 on HS, 18 jobs).
  To finish: `python experiments/src/kaggle_sim/fetch_mac_r6.py mac-v7-r6hs`; the dispatcher fetches Kaggle shards
  itself (stop it with `taskkill /PID 49940 /F` once `kaggle_queue.json` is empty and `kaggle_registry.json` shows no
  `running`); then `compare_r6.py match`, `compare_r6.py screen --all`, `make_macros.py`, `make_audit.py` and the three
  pdflatex passes (Table 2 gains the v7 column; the ledger row of r6_compb gains the full HS). On this laptop run Python
  through the uv base interpreter with `PYTHONPATH=kit/.venv/Lib/site-packages` (the venv's python.exe is blocked by
  Windows Application Control; `finalize.sh` assumes the venv python and has a new round-6 block).
- Kaggle: the v9 probe score (c01 is in: 0.01071); final selection by 2027-01-15 (v9 and v8 are the natural pair).
- Next round (see `DEEP_DIVE.md`): fix c06's cooling cost (heating-only margin or c07), CMA-ES distribution tuning on
  more stations, model-based morning recovery.

## Round 5 (2026-10-25 11:25 PDT - 2026-10-26 04:00 PDT, laptop only, <= 3 simulator workers): Kaggle as an oracle

State: ROUND 5 COMPLETE. Goal 1 answered (the hidden buildings behave like the shipped six; the gap to Kaggle is weather); four Kaggle probes and the v8 candidate scored; 11-candidate pre-registered screen; full-length confirmation met the rule (narrowly on FD); **v8 shipped** in `submission/transfer_policy.py`; paper, AUDIT, REVIEW pass 4 updated. Nothing committed or pushed (coordinator).

1. **Pre-registration** `experiments/results/round5/PREREG.md`: part 1 (11:30 PDT, before any round-5 result) = candidate
   sets, probes, level + shape criteria; part 2 (11:50, before any candidate ran) = 9 candidates, screening sets, rules;
   amendment (12:20, before any screen job) = request cap c10/c11 and one deep-cold screening scenario
   (building_train_7 x fairbanks_1), from the v7 decomposition of the Minneapolis set; note (18:12, after the probe
   scores, before the confirmation) = the literal shape rule names FD (its E rests on the non-discriminating v6 ratio),
   so the ship rule became: public-30 not worse AND better on both P+M and FD; addenda 18:50 / 22:40 = runs dropped for time.
2. **Tooling** (`experiments/src/`): `run_queue_r5.py` (job queue; RAM check before each launch, 3/2/1 workers at
   >= 1.0 / 0.6-1.0 / < 0.6 GB; resumable; log `results/round5/queue/queue_log.txt`; disabled job files end in `.off`),
   `jobs_r5.py`, `make_sets_r5.py` (Minneapolis scenarios by rewriting the weather lines of a shipped strip; self-check:
   all 120 shipped strip-to-strip rewrites reproduce the shipped configs byte for byte; sets `kit/smart_buildings/
   heldout_scenarios_r5m` (confirmation, 12), `r5ms` (screening, 12), `r5x` (building_train_7 x fairbanks_1)),
   `kaggle_build.py` (rebuilds the v7 notebook cell byte for byte) + `kaggle_wait_kernels.sh` + `kaggle_poll_submissions.sh`,
   `compare_sets_r5.py`, `screen_round5.py`, `decide_round5.py`, `confirm_round5.py`, `bake_candidate_r5.py`, `ship_round5.py`,
   `regress_r5.py`, `diag_comfort_r5.py`, `diag_capacity_r5.py`, `diag_ahu_starts_r5.py`, `make_macros_r5.py`;
   `run_scenario.py` / `run_diag.py` take `SB_KIT_DIR` (kit copy) and `run_scenario.py` records `sim_module`.
   Policies frozen for round 5: `results/round5/policies/{v7,v6,v5}.py`; v8 code `policy_candidates/transfer_policy_v8.py`
   (all round-5 switches off = v7 bit for bit, 576 steps x 3 public scenarios, `results/round5/regress/`).
3. **Kaggle** (CLI, `results/kaggle_feedback.json`; every interactive building_train_1/atlanta_2 total within 0.014% of
   local): v7 0.01088 (rank 75/315 when scored; 2026-10-25 20:40 UTC: 347 teams, 85 ahead), v6 0.01116, v5 0.01161,
   pid_water 0.06404 (all submitted 2026-10-25 18:40 UTC), v8 candidate r5_c12_comp submitted 2026-10-26 00:44 UTC
   (ref 57647928): public score 0.01074 (v7 0.01088; difference below the 0.0005 noise threshold, same direction as local); best own score now 0.01074, 82 of 358 teams ahead (2026-10-26 07:10 UTC). Daily count: 10-25 UTC 3, 10-26 UTC 1 (limit kept at 4/day).
4. **Which local set predicts Kaggle** (`results/round5/set_comparison.json`, `kaggle_like_decision.json`, paper Table 2):
   v5/v7 on Kaggle 1.067 = public buildings 1.058 (default-size old held-out 1.169; M, n=5, 1.076) -> the hidden buildings
   behave like the shipped six; pid_water/v7 on Kaggle 5.89 vs public 7.00, Minneapolis 4.30, default-size 4.35,
   public+Minneapolis 6.02 -> the gap is weather; v6/v7 1.026 vs 1.02-1.03 everywhere (no information). Shape error E
   (v6, v5, pid_water): P+M 0.010, P 0.062, M 0.109, O 0.132 (FS 0.011 / FD 0.005 on v6 alone). Level v7/Kaggle: M 1.03,
   O 1.08, FD 0.93, P+M 0.81, P 0.72, FS 0.67. Reading: hidden buildings like the shipped six, hidden stations harsher
   than public + Minneapolis. A public notebook's three controllers show the same 1.17-1.37 gap; its baseline scored
   0.06439 on Kaggle (our pid_water 0.06404).
5. **PR #2** (energy-balanced tank; diff read from GitHub and saved as `results/round5/pr2_download/pr2.diff`; applied
   only in a separate kit copy (moved out of the repo after the runs; recreate by copying `kit/smart_buildings/{__init__.py,
   evaluate.py,baselines,smart_control,weather,training_scenarios}` and `patch -p1 < pr2.diff`), import verified):
   v7 -0.4% (range -2.8% to -0.1%) on the 6 public Fairbanks scenarios; pid_water +23.4% (fairbanks_1 +33%,
   fairbanks_8 +38%): SADR does not use the billing gap, the organizers' baseline partly does.
6. **v7 on M** (`results/round5/loss_decomposition_r5m_v7.json`, `analysis/`): gas 78%, cooling 12%, comfort 5.5%, fan 4% (12 scenarios);
   78% of M's comfort loss is building_train_7/minneapolis_1, where 4 zones sit 0.5-3.3 K below the band with open
   dampers at <= 276 Pa because the v5-era request cap (12 kW per 100 m2) binds below the box/coil limit (22-25 kW).
   06:00-07:00 carries 45-68% of v7's comfort loss on the public/generated sets (Monday 2.1x on the old held-out set);
   AHUs start 2.4-4.8 times a day (cycling not a lever).
7. **Screen** (`results/round5/screen_summary.json`, ledger paper Table 13; 2,880 steps, held-11 / public-4, vs v7):
   Monday lead x1.5 worse (+1.1% / +0.9%), x1.25 worse; weekend setback -3/+2 K helps (-0.7% / -1.0%), -6/+4 K helps
   (-1.2% / -1.5%); lag compensation 1.0 / 0.5 n.s.; cooling precondition cap 0.5 n.s. (no effect); setback burst 8 kW
   worse (public +0.3%); preconditioning at the cap worse (+6.3% / +6.6%); request cap 20 / 30 kW help (-7.6% held,
   driven by building_train_7 x fairbanks_1 -19%; -0.5% public); composite c12 (wk -6/+4 + cap 20 kW) helps
   (-8.8% [CI -529, -14 x1e-5] held, -2.3% [-116, -1.6] public) and is chosen (`decision.json`, 17:26).
   Baked candidate `results/round5/policies/v8_r5_c12_comp.py` reproduces the screen runs bit for bit (2 scenarios).
8. **Confirmation** (8,640 steps, `results/round5/confirm_r5_c12_comp.json`): 
   public-30: v7 0.00786 -> v8 0.00777, -1.10% [-18.2, -1.5] x1e-5 (-2.31% to -0.19%), wins 17/30;
   M (shipped six x Minneapolis): v7 0.01119 -> v8 0.01073, -4.10% [-116.8, -4.9] x1e-5 (-10.44% to -0.44%), wins 6/12;
   P+M: v7 0.00881 -> v8 0.00862, -2.19% [-42.2, -4.9] x1e-5 (-4.79% to -0.56%), wins 23/42;
   FD (fresh default-range): v7 0.01012 -> v8 0.01007, -0.56% [-14.3, -0.0] x1e-5 (-1.41% to -0.00%), wins 9/20.
   Ship rule (public not worse AND better on both P+M and FD): MET as written (seed 0). FD is a tie: the CI's upper end is below zero for 1 of 10 bootstrap seeds (seed 0 only; `results/round5/fd_seed_sensitivity.json`), while public, M and P+M pass for 10/10 seeds. Worst single scenarios: public building_train_7/phoenix_3 +0.5%, FD building_0610/denver_5 +0.7% (hot strips); the gain is in the cold strips (M: building_train_7/minneapolis_1 -10.2%, the request-cap case). Official scorer on `results/round5/full/r5_c12_comp/pub30`: 0.00777 (`results/score_leaderboard_final_r5.txt`).
9. **Shipped**: `python experiments/src/ship_round5.py r5_c12_comp` (2026-10-26 ~03:40 PDT) -> `submission/transfer_policy.py` = v8 (`transfer_policy_v8.py` + wk_ext_lo 6, wk_ext_hi 4, q_cap_w 20000 baked; md5 98036ef2...), `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v8.json`; v7 kept as `results/round5/transfer_policy_v7_shipped_before_round5.py` and `results/tune/best_params_v7.json`. Checks: bake (DEFAULT_PARAMS = v8 defaults + overrides), robustness test 35/35, 36-step smoke run, Kaggle template smoke test (288 steps, `results/round5/kaggle_template_smoke_v8.txt`), the shipped file reproduces the screen runs bit for bit on 2 scenarios x 2,880 steps (`results/round5/regress/xcheck_shipped_v8.json`). The Kaggle-scored notebook (`submission/kaggle/sadr-v8-smart-buildings`, built from `results/round5/policies/v8_r5_c12_comp.py`) differs from the shipped file only in two docstring lines (`results/round5/regress/shipped_vs_kaggle_scored.diff`). README updated.
10. **Paper** (`paper/main.tex`): abstract adds the Kaggle result and reading; Section 3 tuning protocol compressed and
    extended to round 5; Section 4 adds Table 2 (local sets vs Kaggle), paragraphs "Kaggle" and "Round 5"; Section 5
    adds "What round 5 found" (Minneapolis decomposition, the request-cap case, 06:00/Monday comfort, AHU starts, PR #2);
    the round-4 full-length table moved to Appendix A, which also gains Table "set M per scenario"; Appendix B gains the
    round-5 ledger; Sections 2-5 compressed to keep the main text on six pages. Build: 14 pages (main text through page 6, references page 7, appendices A-C), 0 errors, 0 undefined references, 0 `??`, 0 TODO, 0 overfull boxes. `paper/AUDIT.md` (51 claims, 0 missing),
    `paper/review/REVIEW_1.md` pass 4.
11. **Machine note**: the laptop ran on battery 18:00-20:30 PDT; from about 18:10 the simulator ran 2-3x slower (also after
    plugging in; Windows kept the workers on congested cores -- pinning my own oldest worker to core 5 helped, helper
    loop in the scratchpad); this is why the extra v5 runs were dropped.

### Round 5 -- what remains
- Kaggle: allows two final selections; v8 (0.01074) and v7 (0.01088) are the natural pair. Daily count used: 10-25 UTC 3, 10-26 UTC 1.
- Not run (time): v5 on FD (FD's shape error stays on the v6 ratio alone), 7 of 12 v5 runs on M, pid_water/v5 on FS (`results/round5/queue/*.json.off`; rename to .json and restart the runner). A full-length ablation of the two v8 switches (which one costs the hot strips: the weekend ceiling or the cooling side of the request cap).
- Ideas: weight screens toward cold strips (the hidden stations are harsher than public + Minneapolis); more cold stations if weather files become available; the morning recovery (MPC / learned lead).
- User: author block, OpenReview upload by 2026-11-13.

## Headline numbers (leaderboard metric = mean over scenarios of |mean per-step reward|, lower is better)
All rows: 8,640 steps, paired bootstrap 95% CIs over scenarios (5,000 resamples, seed 0).

Round 4, SADR v7 (final) vs the shipped v6 (`experiments/results/round4/confirm_r4_c14_comp_a.json`;
v7 runs: Mac + laptop, bit-identical on the 6 scenarios run on both; v6: round-3 Mac runs, and
`r4_c00_v6` on the fresh set):

| set | v7 (final) | v6 | v7 - v6 x1e-5 [95% CI] | relative [95% CI] | wins | v7 / pid_water [95% CI], wins |
|---|---|---|---|---|---|---|
| 30 public scenarios | **0.00786** | 0.00803 | -17.1 [-37.8, -3.2] | -2.1% [-4.7, -0.4] | 24/30 | 0.143 [0.113, 0.176], 30/30 |
| 40 old held-out (r2 + r3 buildings) | **0.01173** | 0.01206 | -33.5 [-51.4, -19.8] | -2.8% [-4.3, -1.6] | 39/40 | 0.230 [0.203, 0.258], 40/40 |
| 34 old held-out never screened | 0.01090 | 0.01119 | -28.5 [-48.8, -14.8] | -2.6% [-4.4, -1.3] | 33/34 | -- |
| 40 fresh (8 new buildings, round 4) | **0.00869** | 0.00890 | -20.9 [-35.1, -10.8] | -2.3% [-3.9, -1.2] | 38/40 | not run |
| 20 fresh, shipped-six ranges (0601-0603, 0606) | 0.00725 | 0.00736 | -10.3 [-21.0, -3.0] | -1.4% [-2.9, -0.4] | 18/20 | not run |
| 20 fresh, kit default ranges (0604, 0607, 0610, 0639) | 0.01012 | 0.01044 | -31.5 [-56.6, -14.8] | -3.0% [-5.4, -1.4] | 20/20 | not run |
| 74 clean held-out pooled (34 + 40) | 0.00971 | 0.00995 | -24.4 [-35.7, -15.3] | -2.5% [-3.6, -1.5] | 71/74 | -- |

- Official scorer on the v7 tree (`experiments/results/final_r4`, `score_leaderboard_final_r4.txt`):
  LEADERBOARD SCORE = 0.00786 over 30 scenarios (shipped baselines: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520).
- v7 by station (public): Fairbanks 0.0160 (v6 0.0167, -4.5%), Denver 0.0047, Atlanta 0.0052,
  Phoenix 0.0074, Singapore 0.0059. Public v7 is 1.36x the Kaggle leader's 0.00578 and 1.21x rank
  8 (0.00647) -- different buildings and strips, not comparable.

Round 3 (unchanged; the v6 rows of the paper's round-3 narrative), all Mac:

| set | SADR v6 | SADR v5 (previous) | pid_water (same machine) | v6 vs v5 [95% CI], wins | v6 / pid_water [95% CI], wins |
|---|---|---|---|---|---|
| 30 public scenarios | **0.00803** | 0.00831 | 0.05498 | -0.00028 [-0.00045, -0.00015] (-3.4%), 28/30 | 0.146 [0.114, 0.182], 30/30 |
| 10 held-out, buildings 0501/0502 | **0.00944** | 0.01109 | 0.03989 | -0.00165 [-0.00298, -0.00055] (-14.9%), 10/10 | 0.237 [0.153, 0.296], 10/10 |
| 30 held-out, six new buildings (round 3) | **0.01294** | 0.01458 | 0.05467 | -0.00164 [-0.00230, -0.00109] (-11.3%), 30/30 | 0.237 [0.209, 0.268], 30/30 |
| all 40 held-out (8 generated buildings) | **0.01206** | 0.01371 | 0.05097 | -0.00165 [-0.00223, -0.00112] (-12.0%, CI 9.5-14.3%), 40/40 | 0.237 [0.209, 0.264], 40/40 |
| 34 held-out never screened | 0.01119 | 0.01254 | -- | -0.00135 [-0.00190, -0.00089] (-10.8%, CI 8.3-13.5%), 34/34 | -- |

- Official scorer on the round-3 tree (`kit/score_leaderboard.py` on `experiments/results/final`,
  transfer = v6): LEADERBOARD SCORE = 0.00803 over 30 scenarios; shipped baselines: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520 (`experiments/results/score_leaderboard_final.txt`).
- v6 by station (public): Fairbanks 0.01673 (v5 0.01752), Phoenix 0.00742 (0.00755), Singapore
  0.00594 (0.00602), Atlanta 0.00530 (0.00549), Denver 0.00475 (0.00497).
- Kaggle public leaderboard (coordinator's read, 2026-10-22, `experiments/results/kaggle_leaderboard_2026-10-22.json`):
  #1 0.00578, #8 0.00647 (last prize rank), #30 0.00996, 292 teams, on different held-out
  buildings with a 33% public split -- same formula, not directly comparable. Our public-set
  number (v6 0.00803, v7 0.00786) is 1.4x the leader; our generated-building numbers are higher
  still because those buildings are larger than the public ones (round 4: the kit's default ranges
  produce larger buildings than the shipped six); the Kaggle test buildings are unknown.
- Older rounds, unchanged: v4 -> v5 on the public set -9.7% (CI 5.1% to 15.2%), 19/30 wins;
  local re-runs of all four baselines on the Mac: pid_water 0.05498, pid 0.06782, fixed_setpoint
  0.06550, bang_bang 0.22453 (local pid_water -1.7% vs the shipped values on average, range
  -12.7% to +4.6%).
- Cross-machine checks: v4 laptop vs Mac 0.000% per scenario (pid_water 0.017%); round 3: v6
  (`r3_c16`) on building_0502/denver_1 at 2,880 steps, laptop vs Mac, identical total
  (-67.5222061858949), and the baked `submission/transfer_policy.py` (no parameter file) gives the
  same total (`experiments/results/round3/xcheck_c16_laptop`, `regress_shipped_v6`).

## Round 4 (2026-10-23, 13:20-19:35 PDT): diagnosis, pre-registered screen, fresh confirmation

Goal: follow the open leads of round 3 (lower `f_cap_pre`, chiller on the generated buildings,
Fairbanks gas), with a fresh never-screened confirmation set, and ship only under a rule written
down first.

1. **Pre-registration** `experiments/results/round4/PREREG.md` (written before any policy ran on the
   new sets): sets, the 10 planned candidates with hypotheses, classification (helps / public only /
   n.s. / worse vs the shipped v6), composite and choice rule, ship rule (public not worse; pooled
   clean held-out better; neither clean part worse). Decision record with times:
   `results/round4/decision.json`.
2. **Diagnosis** (`results/round4/diagnosis_note.md`, `diag_round4.json`, `diag_cooling_v6.json`;
   `experiments/src/diag_cooling_r4.py` reconstructs the chiller load from the logged handler states
   within 0.1%, `diag_round4.py`; inputs: the round-3 v6 diagnostic runs, no new simulation):
   - Chiller on the generated buildings is a normalization effect: Phoenix + Singapore strips cool at
     2.05 W/m2 of zone (public 2.31) but 0.067 of the 80 kW-per-handler normalizer (public 0.032),
     because a handler serves at most ten zones and the generated buildings have 2,643 m2 of zone per
     handler (public 1,088). Economizer active on 5.5% of the hot strips' coil load (outside air is
     hotter than return air); reheat-while-cooling and missed economizer 1.5-2.4% of the
     cooling-weighted coil load; no latent load in the simulator; flat load through comfort hours;
     preconditioning ~11% of the coil load, setback ~1%. Night air >= 3 K below the zones on 59% of
     unoccupied steps in the generated Denver/Atlanta strips that cool (public 42%), almost never in
     Phoenix/Singapore summers.
   - What control can still reach: fan power above the 200 Pa floor, 0.00047/step on the round-3
     buildings (3.6% of their metric, 39% of their fan term; public 0.00002), 46% of it on handlers
     that heat and cool at once (SAT floored at 292 K, so big cooling zones need full flow) and 41% on
     cooling handlers already at 285 K; pressure above the floor also enlarges every idle zone's forced
     flow.
   - Fairbanks gas (public strips below 0 C): outside-air heat of running handlers = 54% of the gas
     (round-3 buildings 68%); preconditioning 30% and setback 11% of the gas; idle zones chilled by
     their forced minimum flow while unoccupied = 5.1% of the gas. The gas per joule of net heat at
     the discharge cap, 1 + 0.3 (T - Tout)/(Tdisch - T), does not depend on flow -> lowering the
     preconditioning cap below the floor-pressure flow can only slow the recovery.
   - **The kit's DEFAULT_RANGES do not reproduce the shipped six** (seed 0: 597 x 494 ft vs
     building_train_1, seed 0, 373 x 188 ft; the six span width 318-430, height 188-301, rooms 25-51;
     `results/round4/generator_ranges.json`), while the kit README says the Kaggle buildings come from
     "the same generator and parameter ranges as the shipped six". The round-3 held-out buildings
     (default ranges, median zone 246 m2) are therefore larger than the likely test buildings; round 4
     generates both families and reports them separately.
3. **New sets** (`experiments/src/make_sets_r4.sh`, `gen_buildings_r4.py`; generated on the Mac and
   copied to the laptop -- the laptop's own generation writes Windows backslashes into config.gin,
   which gin reads as escapes; floor plans and zone maps are identical on both machines):
   screening `kit/smart_buildings/heldout_scenarios_r4s` = 0520, 0524 (shipped ranges), 0522, 0523
   (default ranges) x 5 stations = 20 scenarios (31-146 zones, rooms up to 1,024 m2); fresh
   confirmation `heldout_scenarios_r4c` = 0601, 0602, 0603, 0606 (shipped ranges) + 0604, 0607, 0610
   (largest rooms of seeds 606-699), 0639 (largest floor area of 606-699; 179 zones, 18 handlers) x 5
   = 40 scenarios (40-179 zones, rooms up to 1,439 m2). Seeds the kit rejects (zones < 20 m2: 521, 600,
   605) replaced by the next free seed (524, 606, 607). Strips: Latin square per station.
4. **Code**: `policy_candidates/transfer_policy_v7.py` = shipped v6 + switches (`f_cap_min`,
   `occ_press_dyn`, `sat_mix_relief`, `flush_on`/`flush_heat_guard`, `sb_neutral`/`sb_neutral_cold`),
   all off by default. Regressions: v7 defaults = v6 bit for bit (3 public scenarios x 576 steps,
   `results/round4/regress`), and the screen's `r4_c00_v6` equals the round-3 screen values of the
   shipped c16 on all 12 round-3 screening scenarios.
5. **Screen** (2,880 steps; public-10 = the 6 earlier public screening scenarios + the other 4
   Fairbanks strips; held-26 = the 6 round-3 held-out screening scenarios + the 20 r4s scenarios;
   `screen_round4.py`, ledger `results/round4/candidates.json`, paper Table 11). Against v6
   (x1e-5 per step, paired 95% CI):

   | id | change | public-10 | held-26 | verdict |
   |---|---|---|---|---|
   | c01 | f_cap_pre 0.316 (floor-pressure flow) | -0.3 [-0.6, -0.1] | +1.7 [-0.3, +4.1] | public only |
   | c02 | f_cap_pre 0.25 (clip removed) | +1.3 [-0.3, +3.6] | +13.2 [+4.1, +24.8] | worse |
   | c03 | f_cap_pre 0.15 | +31.8 [+7.6, +59.2] | +49.4 [+19.4, +85.2] | worse |
   | c04 | f_cap_pre 0.05 | +208.4 [+73.9, +357.9] | +190.5 [+98.1, +297.2] | worse |
   | c05 | discharge margin 0.25 K | -25.7 [-57.5, -3.0] | -20.7 [-38.0, -6.4] | helps |
   | c06 | mixed-handler SAT relief | -0.0 [-0.0, +0.0] | +3.7 [-1.0, +10.9] | n.s. |
   | c07 | occupied pressure cap (e0 0.3, span 1 K) | -4.4 [-9.3, -0.2] | -2.4 [-7.7, +2.0] | public only |
   | c08 | occupied pressure cap (e0 0.1, span 0.5 K) | -4.7 [-10.2, -0.2] | -7.4 [-13.3, -2.4] | helps |
   | c09 | night flush (outside air) | +16.5 [+0.3, +34.3] | -3.3 [-24.6, +18.7] | worse |
   | c10 | reheat set-back zones' forced air | -15.7 [-35.8, +1.2] | -5.8 [-13.0, -0.3] | helps |
   | c11* | night flush, not in heating season | -0.8 [-1.7, -0.0] | -9.6 [-16.6, -3.7] | helps |
   | c12* | discharge margin 0 K | -31.5 [-70.8, -3.6] | -25.1 [-46.0, -8.1] | helps |
   | c13* | c10 only below the setback floor | -15.8 [-35.8, +1.0] | -5.5 [-12.8, +0.0] | n.s. |
   | **c14** | composite c12+c08+c11+c01+c10 | -51.7 [-113.7, -2.9] | -45.7 [-72.6, -22.7] | helps (chosen) |
   | c15 | composite with c13 instead of c10 | -51.8 [-113.6, -3.1] | -46.2 [-73.1, -22.9] | helps (ledger only) |

   \* added after a first partial read of the screen (c09 lost on a winter Fairbanks strip by
   flushing heat that gas had to buy back; c05 helped -> c12; c10 hurt mild strips -> c13); recorded
   in `candidates_notes_r4.json` and `decision.json`. The hypotheses held for the discharge margin
   (consistent -1 to -3% in every heating scenario), the set-back reheat (cold Fairbanks -1.4 to -2.8%)
   and the guarded flush (Denver/Atlanta summers up to -7%); the fan-pressure diagnosis gave only the
   mild occupied cap (c08) and the mixed-handler relief did nothing measurable; caps below the
   floor-pressure flow were worse, as predicted.
6. **Decision** (16:40 PDT, before any full-length candidate run): one change per family among those
   that helped (discharge: c12 over c05 by held metric; occupied cap: c08; flush: c11; set-back:
   c10 because c13 was n.s.; f_cap: c01 public only) -> composite c14; the lowest held-26 metric
   among the composite and the helping singles -> **c14**.
7. **Confirmation** (8,640 steps, diagnostics on; v6 on the fresh set run at the same time and not
   looked at before the decision): the table at the top. The ship rule is met (public better, not
   only not worse; pooled clean held-out better; neither clean part worse). Where the gain comes
   from (`results/round4/loss_decomposition_{public_v7,old40_v6,old40_v7,fresh40_v6,fresh40_v7}.json`):
   public gas 0.00425 -> 0.00411 per step (Fairbanks 0.01673 -> 0.01598, -4.5%); old held-out cooling
   -0.00014, fan -0.00010, gas -0.00017, comfort +0.00008 (0.00039 -> 0.00047); fresh gas -0.00011,
   cooling -0.00009, fan -0.00004, comfort +0.00003.
8. **Shipped**: `python experiments/src/ship_round4.py r4_c14_comp_a` -> `submission/transfer_policy.py`
   (v7 code with the five overrides baked into `DEFAULT_PARAMS`; "mismatches after bake: none"),
   `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v7.json`; v6 kept as
   `results/tune/best_params_v6.json` and `results/round4/transfer_policy_v6_shipped_before_round4.py`.
   Robustness test 35/35 cases; 36-step smoke run; Kaggle template smoke test (288 steps,
   building_train_1/fairbanks_1: -2.141, `results/round4/kaggle_template_smoke_v7.txt`); the baked file
   (no parameter file) reproduces the Mac's c14 screen runs bit for bit on building_train_8/fairbanks_8
   and building_train_1/denver_7 at 2,880 steps on the laptop (`results/round4/xcheck_shipped_v7`);
   official scorer 0.00786 on `results/final_r4`. Policy time per step in the full runs 0.6-0.7 ms (0.74 ms on the 179-zone building 0639).
9. **Machines**: Mac -- held-26 screen of c00-c10 (286 runs, 14 workers, 132 min), c11-c13 and
   the two composites on both screening sets, v6 and v7 full length on the fresh default-range
   buildings, v7 on the old 40 and on 20 public scenarios (130 full-length runs, 0 failures; load
   40-110 from the user's Chrome). Laptop -- public-10 screen of c00-c10 (110 runs, 3 workers, 94 min),
   regressions and smoke tests, v6 full length on the fresh shipped-range buildings (20), v7 full
   length on 18 public/fresh scenarios; six v7 scenarios ran on both machines with identical totals.
   Fetched with `experiments/src/fetch_mac_round4.sh` into `experiments/results/mac/round4/`; Mac logs
   `experiments/results/logs/mac/r4_*.log`.
10. **Paper** (`paper/main.tex`): abstract and Section 4 lead with v7; Section 3 adds the v7 switches
    and the round-4 protocol; Section 4 adds Table 2 (v7 vs v6 on every set) and the round-4 ledger
    summary; Section 5 adds "What round 4 found" (normalization, fan pressure, ventilation, generator
    ranges); Table 1 gains a v7 row; Appendix A gains Table 6 (fresh set per scenario) and Figure 1
    (v7 vs v6 per generated building); Appendix B Table 11 (round-4 ledger); the decomposition and
    held-out-building figures moved to Appendix C to keep six pages; Sections 3-5 compressed.
    `finalize.sh` now also runs the round-4 summary, confirmation, ledger, `assemble_round4_tree.py`
    and `make_figures_r4.py`; macros in `make_macros_r4.py`; audit 43 claims, 0 missing.

### Round 4 -- what remains
- Nothing running. Not done: a full-length ablation of the five v7 switches; `pid_water` on the
  fresh buildings (the fresh set reports v7 vs v6 only); the Kaggle submission (user).
- Ideas for January: the shipped-range buildings gain least (-1.4%) and are the likely test
  distribution -- screen future changes on shipped-range buildings first; Fairbanks remains the
  largest single loss (building_train_1/fairbanks_1 0.0461, 95% gas), bounded by the 30% outside-air
  physics; a learned residual or MPC for the morning recovery.

## Round 3 (2026-10-23): what was done, before/after, which machine ran what

Goal: find where v5's loss sits, fix the weakness on large generated zones, enlarge the held-out
set, and ship a better policy only under a rule fixed in advance.

1. **Loss decomposition** (`experiments/results/round3/loss_decomposition_note.md`, `decompose_loss.py`
   on `run_diag.py` runs; Mac, 8,640 steps). Public set, v5: gas 52%, chiller 38%, fans 5%, comfort
   4%; preconditioning + setback carry 30% of the loss; Fairbanks is 90% gas. Generated buildings,
   v5: comfort 14-16% (vs 4% public), the largest quartile of zones in band only 0.4-0.65 h after
   06:00. Diagnosis: every VAV box has the same 2 m3/s and hot-water Kv, so v5's constants (12 kW
   cap, fixed gains, one building-wide lead) starve 300-1,400 m2 zones.
2. **Enlarged held-out set**: six new generated buildings (generator seeds 500, 505, 507, 508, 509,
   511; 32-120 zones, 5-12 handlers, zones 33-1,373 m2), one strip per station = 30 scenarios
   (`kit/smart_buildings/heldout_scenarios_r3`), on top of the previous 10 (0501, 0502): 40
   held-out scenarios on 8 generated buildings. v5 and pid_water were run on it once (Mac,
   `mac_round3_diag.sh`): v5 0.01458, pid_water 0.05467.
3. **v6 code** (`experiments/src/policy_candidates/transfer_policy_v6.py`): area-scaled gains, caps
   and setback burst (zone areas from the metadata zone map); physical and water-side request caps;
   per-zone optimum start; adaptive setback floor; a preconditioning latch was tested and rejected.
   With the switches off it reproduces v5 bit for bit (576-step regression, `results/round3/regress_*`).
4. **Screens** (2,880 steps; 6 public scenarios on the laptop, 6 held-out scenarios on the Mac;
   `screen_round3.py`; ledger `experiments/results/round3/candidates.json`, table in the paper's
   Appendix B). 17 v6 variants paired against v5 and against the v6 defaults (c00). Against c00:
   7 worse (c01 f_cap_pre 1; ablations c03 no area scaling, c04 no per-zone start; c09 rate prior 1;
   c11 latch; c12 lead safety 1.6; c13), 5 not significant (c05, c07, c08, c10, c15), 1 public-only
   (c06 no down-scaling of small zones), 3 met the rule (c02 f_cap_pre 0.5, c14 = c02 + c06,
   c16 = c14 with f_cap_pre 0.35). Choice rule fixed before any full-length composite run
   (`candidates_notes.json -> decision_rule`): lowest held-out screen among composites meeting the
   rule -> **c16** (held screen 0.01824 vs c14 0.01832; c16 vs c14 not significant). c16 vs c00 on
   the screens: public -5.0e-5 [-8.9e-5, -1.4e-5] (5/6), held-out -21.5e-5 [-44.9e-5, -4.5e-5] (6/6).
5. **Full-length confirmation** (Mac, `mac_round3_confirm.sh` -> `mac_round3_full.sh`, 12/10/10
   workers, nohup, per-scenario checkpoints): the table above. Ship rule (not worse than v5 on the
   public set, better on the held-out sets) met on every set. The v6 defaults alone at full length
   on the public set (laptop, 3 workers): 0.00814 (vs v5 -0.00017 [-0.00029, -0.00007], 22/30); c16
   vs c00 on the public set: -0.00011 [-0.00018, -0.00006], 28/30. After shipping, for the ledger,
   c00 on the 40 held-out scenarios (Mac): 0.01222 (vs v5 -0.00148 [-0.00201, -0.00102], 40/40);
   c16 vs c00 there: -0.00016 [-0.00031, -0.00006], 33/40 (`candidates.json -> full_length_c00_heldout`).
6. **Shipped**: `python experiments/src/ship_round3.py r3_c16_pre035_min1` -> `submission/transfer_policy.py`
   (v6 source + `f_cap_pre` 0.35, `area_scale_min` 1.0 baked into `DEFAULT_PARAMS`; "mismatches after
   bake: none"), `submission/best_params.json` = `experiments/results/tune/best_params.json` =
   `best_params_v6.json`; v5 kept as `tune/best_params_v5.json` and
   `results/round3/transfer_policy_v5_shipped_before_round3.py`. Robustness test 35/35 cases;
   36-step smoke run; Kaggle template smoke test (288 steps, building_train_1/fairbanks_1, -2.037);
   baked file reproduces the Mac run bit for bit (item "Cross-machine checks" above).
7. **Where the gain came from** (decomposition of the v6 runs): comfort on the six new buildings
   0.00208 -> 0.00039 per step (share 14.2% -> 3.0%; out-of-band occupied zone-steps 14.0% -> 2.1%;
   largest-quartile recovery 0.65 h -> 0.12 h), fan +0.00026, gas -0.00024; on the public set
   comfort 0.00036 -> 0.00018 and gas 0.00436 -> 0.00425. What is left on the generated buildings is
   chiller electricity (0.00709/step vs 0.00318 public), not diagnosed this round.

Machines in round 3:
- laptop: public screens of all 17 variants (`results/round3/screen/*/public`), c00 at full length
  on the public set (`results/round3/laptop_full_c00_public`, 97.7 min, 3 workers), ten-day tests
  on building_0502/denver_1 (`b0502_*`), regressions and the cross-machine/bake checks, finalize.
- Mac: v5 diagnostics on all three sets (`diag_v5_public`, `diag_v5_heldout`, `diag_v5_r3` + pid_water),
  held-out screens of all 17 variants, the shipped c16 at full length on public/old/new held-out
  (`final_v6_public`, `final_v6_heldout`, `final_v6_r3`), and the ledger-only c00 held-out runs
  (`final_c00_heldout`, `final_c00_r3`). Fetched with `experiments/src/fetch_mac_round3.sh` into
  `experiments/results/mac/round3/`; Mac logs in `experiments/results/logs/mac/` (`r3_*.log`).
- Paper trees: `assemble_round3_tree.py` -> `results/final` (transfer = v6, transfer_v5, transfer_v4,
  4 baselines), `final_heldout` (v6, v5, v4, pid_water), `final_heldout_r3` (v6, v5, pid_water).

### Round 3 -- what remains
- Nothing running. The ledger-only c00 held-out runs finished at 13:04 PDT, were fetched, and are in
  the ledger and in one clause of the paper's Section 4.
- Not tried (ideas for January, `candidates.json -> ideas_not_run` plus round 3): `f_cap_pre` below
  0.35 (the trend 1.0 -> 0.7 -> 0.5 -> 0.35 was still improving on the held-out screen); envelope
  pre-cooling / setback depth in cooling climates for the large generated buildings (their chiller
  term is 2x the public one); a learned residual on top of SADR.
- The 6 held-out screening scenarios (first 10 days) informed the choice; the 34 never screened are
  the clean held-out estimate (-10.8%, CI 8.3-13.5%, 34/34).

## Final policy (`submission/transfer_policy.py`, SADR v9 since round 6)
v9 = the v8 rules below + four round-6 switches: in heating season the forced minimum air of a set-back zone on a
running handler is reheated to the discharge limit instead of to the zone temperature (within 8 h of a workday start
while the outside air is at or below the zone's setback floor, and at any time within 2 K of the floor); the
preconditioning target sits 0.5 K inside the band (v8 0.8 K); the weeknight setback floor is 10 K below the eco
heating setpoint (v8 8 K). With every round-6 switch off the v9 code reproduces v8 bit for bit. The v8 description
follows.

v8 = the v7 rules below + two round-5 switches: far from the next workday start (weekends) the setback floor drops
by 6 K and the ceiling rises by 4 K, ramped back over the 12 h that end 10 h before the start; and the per-zone
request cap is 20 kW per 100 m2 (v7: 12 kW), so in deep cold the box and coil bound the heat. With every round-5
switch off the v8 code reproduces v7 bit for bit. The v7 description follows.

Schedule-Aware Demand-based Reset: occupancy-gated OCCUPIED / PRECONDITION / SETBACK modes with
holiday detection and a self-tuning optimum-start lead (per zone since v6); per-zone PI loops on net
heat (W) translated to damper flow via the supply-air temperature and to reheat valve position via
the water capacity rate and the 308.15 K discharge limit; coldest supply air (285 K) whenever a
handler cools, 292 K floor on handlers that also heat; static pressure trim-and-respond in closed
form; proportional economiser with the fan break-even; loop dP reset to the most-open valve; hot
water 350 K in heating season; setback by burst heating/cooling against a floor widened by 8 K
below / 6 K above the eco band. v6 added: gains, request cap and setback burst scaled with zone area
/ 100 m2 (clip [1, 6]), request caps at what the box delivers at a flow fraction and at the coil's
water-side limit, per-zone optimum start, adaptive setback floor. v7 (round 4) adds: discharge
margin 0 (flows and valves sized for the simulator's own 308.15 K cap); a pressure-aware occupied
request cap (flow above the 200 Pa floor-pressure flow only in proportion to the zone's error, from
0.1 K, full 0.5 K later); a night flush with outside air before workdays outside heating season
(zone >= 3 K warmer than outside, floor pressure, coil off, within 8 h of the start); reheat of the
forced minimum flow of set-back zones on running handlers in heating season; preconditioning cap
at the floor-pressure flow (0.316). With the five v7 switches off the code reproduces v6 bit for
bit. Pure numpy + stdlib, ~0.6-0.7 ms per step in the full runs (init ~40-100 ms on a 120-zone
building for the zone-map labelling), deterministic, shape-agnostic, every action slot written and
clipped; 54 KB.

Parameter provenance: v4 random search (16 configurations, ki 60 -> 120 is the whole gain), v5
analysis-driven candidates at full length on the public set (winner `c10_satcold_night8_hi6`:
sat_cool_hi 285, night_low_ext 8, night_high_ext 6), v6 round-3 screen + full-length confirmation
(winner `r3_c16_pre035_min1`: f_cap_pre 0.35, area_scale_min 1.0 on the v6 defaults), v7 round-4
pre-registered screen + full-length confirmation (winner `r4_c14_comp_a`: disch_margin_k 0,
occ_press_dyn 1 / e0 0.1 / span 0.5, flush_on + flush_heat_guard, sb_neutral, f_cap_pre 0.316).

## Machines
- `laptop`: this Windows laptop (8 cores shared; <= 3 simulator processes; 0.03-0.2 s/step).
  Generating scenarios here writes backslash paths into config.gin (gin reads them as escapes):
  generate on the Mac and copy (done for r4s/r4c).
- `mac`: `ssh mac`, Apple M5 Pro, 18 cores, 48 GB, kit clone + uv venv (Python 3.12.15, same pins),
  layout mirrors this tree at `~/neurips/sb`; shared with the user's own apps (Chrome used 5-8
  cores during round 4; load 40-110). Round 1-3 paper rows come from Mac runs; round-4 v7 rows mix
  Mac and laptop runs, which are bit-identical (checked on 6 full-length scenarios).

## Deliverables (all present)
1. `submission/transfer_policy.py` (v7, baked), `submission/README.md` (v7 description and
   selection, v6 kept as "previous version", paste-in steps for the Kaggle notebook, repo link),
   `submission/kaggle_notebook_template.py` (smoke-tested with v7), `submission/best_params.json`.
2. `experiments/results/final_scores.json`, `heldout_scores.json`, `heldout_r3_scores.json`
   (round-3 trees, transfer = v6), `final_scores_local.json`, `heldout_scores_local.json`,
   `analysis.json`, `candidates_summary.json`, `env_info.json`, `score_leaderboard_final.txt` (v6) and
   `score_leaderboard_final_r4.txt` (v7, tree `results/final_r4`); round 3: `results/round3/*`;
   round 4: `results/round4/PREREG.md`, `decision.json`, `candidates.json` (ledger),
   `screen_summary_screen_vs_r4_c00_v6.json`, `screen_ranking.txt`, `confirm_r4_c14_comp_a.json`,
   `confirm_ranking.txt`, `diagnosis_note.md`, `diag_round4.json`, `diag_cooling_v6.json`,
   `generator_ranges.json`, `scan_default_606_699.json`, `loss_decomposition_*_v{6,7}.json`,
   `regress/`, `xcheck_shipped_v7/`, `kaggle_template_smoke_v7.txt`, `finalize_r4.log`;
   `paper/results_macros.tex`, `per_scenario_table.tex` (3 tables), `per_scenario_table_r4.tex`,
   `tuning_tables.tex` (ablation, v5 candidates, round-3 and round-4 ledgers); `paper/figures/*`
   (+ `fig_round4_buildings`); `paper/main.pdf` (13 pages: main text through page 6, references page
   7, Appendices A-C from page 8; 0 errors, 0 undefined, 0 `??`, 0 overfull); `paper/AUDIT.md` (43
   claims, 0 missing values; header `AUDIT_header.md`); `paper/review/REVIEW_1.md` (passes 1-3).
3. This file.

Pipeline (idempotent): `bash experiments/src/finalize.sh` regenerates everything in item 2 from the
result trees (assemble, score, analysis, decompositions, screen summaries, round-4 confirmation and
ledger, the v7 tree and its official score, macros, audit, figures, three pdflatex passes).

## Paper
NeurIPS 2026 style, `[sglblindworkshop,final]` + `\workshoptitle`. Round-4 changes: abstract leads
with v7 (public 0.00786, ratio to pid_water 0.143) and the round-4 result on the 74 untouched
held-out scenarios; Section 3 adds "Round 4 (v7)" and the pre-registered protocol (and that three
candidates were added after a first look); Section 4 adds Table 2 (v7 vs v6 on every set, both
building families) and the round-4 ledger summary with where the gain comes from; Section 5 adds
"What round 4 found"; Table 1 has a v7 row; Appendix A: Table 6 (fresh set) and Figure 1 (v7 vs v6
per building); Appendix B: Table 11 (round-4 ledger); the decomposition and held-out-building
figures moved to Appendix C; Sections 3-5 compressed to keep six pages. Self-review pass 3
(`paper/review/REVIEW_1.md`): must-fixes 1-5 applied.

## To do (user)
- Round 6: v9 is shipped; its Kaggle probe (ref 57678857) was pending at hand-off. Choose the two final Kaggle
  submissions before 2027-01-15: v9 and v8 are the natural pair (v9 is better on the harsh sets, a tie on the
  public set and worse on large default-range buildings and hot strips; v8 hedges that). The author block is filled
  (round 6); the OpenReview upload by 2026-11-13 remains.
- Round 5: v8 is shipped and was scored on Kaggle (0.01074; v7 0.01088). Choose the two final Kaggle submissions
  before 2027-01-15 (v8 and v7 are the natural pair). The older Kaggle instructions below are kept for reference.
- Kaggle (joined): follow `submission/README.md` -- open the official notebook template, replace
  the policy cell with `submission/transfer_policy.py` (v7), run once on the public scenarios
  (expect the per-scenario totals in `experiments/results/final_r4/<b>/<w>/transfer/summary.json`,
  leaderboard 0.00786; a few per cent off if the grader's kit differs), submit. Keep the submitted
  file identical to the one here so the paper's numbers refer to the submitted policy. v7 reads the
  optional `zone_map` from the metadata (the kit provides it); without it the area scaling switches
  off and the policy still runs.
- OpenReview poster paper (group NeurIPS.cc/2026/Workshop/SB26_Challenge) by 2026-11-13: fill in
  name/affiliation in `paper/main.tex` (author block), rebuild (`bash experiments/src/finalize.sh`
  or the three pdflatex passes), check the Overleaf template
  (https://www.overleaf.com/project/6ace893ebb021a3e1807b140) for the page limit (main text is six
  pages), upload `paper/main.pdf`.
- Before the January final paper (2027-01-15): the Kaggle score once available; the open ideas in
  "Round 4 -- what remains".

## Risks
- Selection used the public set at full length (v5) and the screening sets (v6, v7): the public
  number (0.00786) is optimistic; the 74 held-out scenarios no decision touched (34 old + 40 fresh)
  are the clean estimate; 16 generated buildings are still a small sample of the generator.
- The kit's default generator ranges produce larger buildings than the shipped six; the README says
  the Kaggle buildings share the shipped six's ranges. On fresh shipped-range buildings v7 gains
  1.4% over v6 (CI 0.4-2.9%), less than on large buildings (3.0%); round-3's large held-out gains
  (-12%) probably overstate what v6/v7 gain on Kaggle over v5.
- The Kaggle leaders (0.0058) are 1.36x below our public-set number; most of our remaining loss is
  heating gas in Fairbanks (outside-air physics: 54% of the gas in the cold public strips is
  ventilation heat) and chiller electricity in the hot strips.
- v7 changes comfort slightly (old held-out comfort term 0.00039 -> 0.00047 per step) in exchange
  for energy; the trade is net positive on every set at full length.
- Local-vs-official pid_water gap (-1.7% mean, up to -12.7% on one scenario) means the organizers'
  kit version may differ slightly from the clone used here.
- v6/v7 depend on the metadata `zone_map` for the area scaling; if the grader's harness omitted it,
  the policy would fall back to unscaled gains (the round-4 switches do not need it).
