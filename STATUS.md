# Smart Buildings Challenge (SB26) -- STATUS

Last updated: 2026-10-23 13:10 PDT. State: ROUND 3 COMPLETE for the poster round -- SADR v6
(round-3 composite `r3_c16_pre035_min1`) confirmed at full length on 30 public + 40 held-out
scenarios, baked into `submission/transfer_policy.py`, paper rebuilt (0 errors, 0 undefined refs,
0 `??`, 0 overfull boxes, main text ends on page 6), audit and self-review pass 2 written. All
Mac jobs finished (the Mac is idle). Open items are the user's (Kaggle submission, OpenReview
upload with name).

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private; `kit/` and the
per-scenario time series are git-ignored; `.git`, `.gitignore`, `LICENSE`, `.github` and the
top-level `README.md` are managed by `make_repos.py` and were not edited here). Nothing was
committed or pushed from this session.

## Headline numbers (leaderboard metric = mean over scenarios of |mean per-step reward|, lower is better)
All rows: 8,640 steps, Mac, paired bootstrap 95% CIs over scenarios (5,000 resamples).

| set | SADR v6 (final) | SADR v5 (previous) | pid_water (same machine) | v6 vs v5 [95% CI], wins | v6 / pid_water [95% CI], wins |
|---|---|---|---|---|---|
| 30 public scenarios | **0.00803** | 0.00831 | 0.05498 | -0.00028 [-0.00045, -0.00015] (-3.4%), 28/30 | 0.146 [0.114, 0.182], 30/30 |
| 10 held-out, buildings 0501/0502 | **0.00944** | 0.01109 | 0.03989 | -0.00165 [-0.00298, -0.00055] (-14.9%), 10/10 | 0.237 [0.153, 0.296], 10/10 |
| 30 held-out, six new buildings (round 3) | **0.01294** | 0.01458 | 0.05467 | -0.00164 [-0.00230, -0.00109] (-11.3%), 30/30 | 0.237 [0.209, 0.268], 30/30 |
| all 40 held-out (8 generated buildings) | **0.01206** | 0.01371 | 0.05097 | -0.00165 [-0.00223, -0.00112] (-12.0%, CI 9.5-14.3%), 40/40 | 0.237 [0.209, 0.264], 40/40 |
| 34 held-out never screened | 0.01119 | 0.01254 | -- | -0.00135 [-0.00190, -0.00089] (-10.8%, CI 8.3-13.5%), 34/34 | -- |

- Official scorer (`kit/score_leaderboard.py` on `experiments/results/final`): LEADERBOARD SCORE =
  0.00803 over 30 scenarios; shipped baselines on the same scenarios: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520 (`experiments/results/score_leaderboard_final.txt`).
- v6 by station (public): Fairbanks 0.01673 (v5 0.01752), Phoenix 0.00742 (0.00755), Singapore
  0.00594 (0.00602), Atlanta 0.00530 (0.00549), Denver 0.00475 (0.00497).
- Kaggle public leaderboard (coordinator's read, 2026-10-22, `experiments/results/kaggle_leaderboard_2026-10-22.json`):
  #1 0.00578, #8 0.00647 (last prize rank), #30 0.00996, 292 teams, on different held-out
  buildings with a 33% public split -- same formula, not directly comparable. Our public-set
  0.00803 is 1.4x the leader; our generated-building number (0.01206) is higher still because those
  buildings are larger than the public ones; the Kaggle test buildings are unknown.
- Older rounds, unchanged: v4 -> v5 on the public set -9.7% (CI 5.1% to 15.2%), 19/30 wins;
  local re-runs of all four baselines on the Mac: pid_water 0.05498, pid 0.06782, fixed_setpoint
  0.06550, bang_bang 0.22453 (local pid_water -1.7% vs the shipped values on average, range
  -12.7% to +4.6%).
- Cross-machine checks: v4 laptop vs Mac 0.000% per scenario (pid_water 0.017%); round 3: v6
  (`r3_c16`) on building_0502/denver_1 at 2,880 steps, laptop vs Mac, identical total
  (-67.5222061858949), and the baked `submission/transfer_policy.py` (no parameter file) gives the
  same total (`experiments/results/round3/xcheck_c16_laptop`, `regress_shipped_v6`).

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

## Final policy (`submission/transfer_policy.py`, SADR v6)
Schedule-Aware Demand-based Reset: occupancy-gated OCCUPIED / PRECONDITION / SETBACK modes with
holiday detection and a self-tuning optimum-start lead (v6: per zone); per-zone PI loops on net
heat (W) translated to damper flow via the supply-air temperature and to reheat valve position via
the water capacity rate and the 308.15 K discharge limit; coldest supply air (285 K) whenever a
handler cools, 292 K floor on handlers that also heat; static pressure trim-and-respond in closed
form; proportional economiser with the fan break-even; loop dP reset to the most-open valve; hot
water 350 K in heating season; setback by burst heating/cooling against a floor widened by 8 K
below / 6 K above the eco band. v6 adds: gains, request cap and setback burst scaled with zone area
/ 100 m2 (clip [1, 6], i.e. only upwards), request caps at what the box delivers at flow fraction
0.35 (preconditioning/setback) or 1.0 (occupied) and at the coil's water-side limit, per-zone
optimum start, adaptive setback floor. Pure numpy + stdlib, ~0.35-0.5 ms per step (init ~40 ms on
a 120-zone building for the zone-map labelling), deterministic, shape-agnostic, every action slot
written and clipped; 48 KB.

Parameter provenance: v4 random search (16 configurations, ki 60 -> 120 is the whole gain), v5
analysis-driven candidates at full length on the public set (winner `c10_satcold_night8_hi6`:
sat_cool_hi 285, night_low_ext 8, night_high_ext 6), v6 round-3 screen + full-length confirmation
(winner `r3_c16_pre035_min1`: f_cap_pre 0.35, area_scale_min 1.0 on the v6 defaults).

## Machines
- `laptop`: this Windows laptop (8 cores shared; <= 3-4 simulator processes; 0.05-0.23 s/step).
- `mac`: `ssh mac`, Apple M5 Pro, 18 cores, 48 GB, kit clone + uv venv (Python 3.12.15, same pins),
  layout mirrors this tree at `~/neurips/sb`; shared with the user's own apps (load 12-24 during
  round 3). All paper rows come from Mac runs (one machine for every policy).

## Deliverables (all present)
1. `submission/transfer_policy.py` (v6, baked), `submission/README.md` (v6 description, paste-in
   steps for the Kaggle notebook, repo link), `submission/kaggle_notebook_template.py` (smoke-tested
   with the v6 policy), `submission/best_params.json`.
2. `experiments/results/final_scores.json`, `heldout_scores.json`, `heldout_r3_scores.json`,
   `final_scores_local.json`, `heldout_scores_local.json`, `analysis.json`, `candidates_summary.json`,
   `env_info.json`, `score_leaderboard_final.txt`; round 3: `results/round3/candidates.json`
   (ledger), `screen_summary.json` (vs v5), `screen_summary_vs_r3_c00_v6_default.json` (vs c00),
   `loss_decomposition_{public,heldout,heldout_r3}_{v5,v6}.json`, `loss_decomposition_note.md`,
   `finalize_r3.log`; `paper/results_macros.tex`, `per_scenario_table.tex` (3 tables),
   `tuning_tables.tex` (ablation, v5 candidates, round-3 ledger); `paper/figures/*` (loss
   decomposition v5/v6, held-out buildings, per-scenario scores, loss by hour, trace, tuning);
   `paper/main.pdf` (12 pages: main text through page 6, references page 7, Appendices A-C from
   page 8; 0 errors, 0 undefined, 0 `??`, 0 overfull); `paper/AUDIT.md` (34 claims, 0 missing
   values; header `AUDIT_header.md`); `paper/review/REVIEW_1.md` (pass 1 + pass 2).
3. This file.

Pipeline (idempotent): `bash experiments/src/finalize.sh` regenerates everything in item 2 from the
result trees (assemble, score, analysis, decompositions, screen summaries, ledger, macros, audit,
figures, official scorer, three pdflatex passes).

## Paper
NeurIPS 2026 style, `[sglblindworkshop,final]` + `\workshoptitle`. Round-3 changes: abstract and
results report the pooled 40-scenario held-out set (and the 34 never screened); Section 3 states the
v6 mechanisms with the shipped values as macros and the round-3 protocol (screens vs v5 and vs c00,
composites, choice rule fixed in advance); Section 4 has the loss decomposition (Figure 1, v5 vs
v6), the held-out-buildings figure (8 buildings), v5 -> v6 with CIs on every set, the ledger
summary including failures, and the Kaggle leaderboard caveat; the per-scenario figure moved to
Appendix A to keep the main text at six pages; Appendix B Table 8 is the full round-3 ledger.
Self-review pass 2 (`paper/review/REVIEW_1.md`): see the file; must-fixes applied.

## To do (user)
- Kaggle (joined): follow `submission/README.md` -- open the official notebook template, replace
  the policy cell with `submission/transfer_policy.py` (v6), run once on the public scenarios
  (expect the per-scenario totals in `experiments/results/final_scores.json` ->
  `policies.transfer.per_scenario`, a few per cent off if the grader's kit differs), submit. Keep
  the submitted file identical to the one here so the paper's numbers refer to the submitted policy.
  v6 reads the optional `zone_map` from the metadata (the kit provides it); without it the area
  scaling switches off and the policy still runs.
- OpenReview poster paper (group NeurIPS.cc/2026/Workshop/SB26_Challenge) by 2026-11-13: fill in
  name/affiliation in `paper/main.tex` (author block), rebuild (`bash experiments/src/finalize.sh`
  or the three pdflatex passes), check the Overleaf template
  (https://www.overleaf.com/project/6ace893ebb021a3e1807b140) for the page limit (main text is six
  pages), upload `paper/main.pdf`.
- Before the January final paper (2027-01-15): the Kaggle score once available; the open ideas in
  "Round 3 -- what remains".

## Risks
- Selection used the public set at full length (v5) and both screening sets (v6): the public number
  (0.00803) is optimistic; the 34 never-screened held-out scenarios are the clean estimate, and
  eight generated buildings are still a small sample of the generator.
- The Kaggle leaders (0.0058) are 1.4x below our public-set number; most of our remaining loss is
  heating gas in Fairbanks and chiller electricity in the hot strips (2x the public level on the
  large generated buildings).
- Local-vs-official pid_water gap (-1.7% mean, up to -12.7% on one scenario) means the organizers'
  kit version may differ slightly from the clone used here.
- v6 depends on the metadata `zone_map` for its main gain; if the grader's harness omitted it, v6
  would fall back to unscaled gains (still with the per-zone start and the physical caps).
