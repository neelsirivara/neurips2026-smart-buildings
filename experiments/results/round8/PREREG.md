# Round 8 pre-registration

Written 2026-10-29 ~22:45-22:49 UTC, before any run of the candidate on HC2. Go-ahead from the coordinator after round 7
ended with no candidate chosen (round 7 `decision.json`, 22:17 UTC: all four candidates "public only").

## Candidate (one, fixed)
**r7L_mbr2** = round 7's post-hoc ledger variant, exactly as frozen and as run in round 7's ledger shards:
- code `experiments/results/round6/policies/v10b_screen.py`
  sha256 `2827a88af85a63e84a668099689a277c7cb7c285b13cfd15ab5ddf8ac811f931`
  (identical to `experiments/src/policy_candidates/transfer_policy_v10.py` at the time of writing, md5 296f75d3...);
- parameters `experiments/src/policy_candidates/r7L_mbr2.json`
  sha256 `79857dd13b2ed8beb935bf5fd58d3b5307b02a21025dff26564fe21d42277bbe`
  = {sb_boost 1, sb_boost_h 8, sb_boost_cold 1, sb_boost_floor_k 2, lead_safety 1.15, night_low_ext 10, mbr_on 1,
  mbr_lead_cap 1}; every other parameter at the v10b defaults (mbr_safety 1.1, mbr_min_n 36, mbr_lambda 0.998).
- What it is: v9 with the shorter lead (c07, lead_safety 1.15) in place of the nearer preconditioning target (c06),
  plus the per-zone first-order model (online RLS) that may only *shorten* the learned-rate start lead and is ignored
  where the model says the target is unreachable at the discharge cap (the "latest feasible start" of the round-7
  analysis). With `mbr_on` 0 the code reproduces v9 bit for bit (round 7 `regress/`).

No other candidate, no parameter change, no re-tuning after this point.

## What was seen before this was written (so HC2 is the only clean test)
- The candidate was defined post hoc in round 7 (PREREG round 7, note 18:59 UTC), after the first r7_mb HS shard
  showed building_train_7 losing 4-5% to an over-long model lead; one 7-day development run on
  building_train_7/denver_c1 (`results/round7/dev7d/r7L_mbr2`).
- **HS and public-30 were seen**: round 7 screened r7_base (= the same code path with mbr_on 0) and r7_mbr (the model
  start without the cap) on HS (18) and the full public-30; the candidate's own ledger shards on HS and public-30 are
  running; at the time of writing 9 of 18 HS scenarios are back (-0.93% [-1.05, -0.82] against v9, 9/9 wins) and no
  public-30 scenario is. These sets are therefore not clean evidence for this candidate; the paper will say so.
- **HC2 is clean**: `heldout_scenarios_r7hc` (44 scenarios: the shipped six under six cold-month 30-day windows of
  the shipped station CSVs, plus nine cross pairs; `results/round7/sets_r7.json`, built before any round-7 candidate
  ran). Only v9 has run on it (Kaggle shards v9-r7hc-1..4, `results/round6/runs/r6_comp/r7hc`, 44 summaries); no
  candidate of any round, no Mac job and no development run touched it (checked: `runs/*/r7hc`, `kaggle_jobs/*`,
  `mac_jobs/*`, `mac_registry.json`). Its windows overlap earlier windows of the same stations by 9-16 days, but no
  building x strip pair of HC2 was run before.

## Reference and ship rule (as rounds 6 and 7)
Reference: the shipped v9 (`submission/transfer_policy.py`, sha256 02c1c2c6...; its runs = `runs/r6_comp/<set>`).
At 8,640 steps, paired bootstrap of the mean per-scenario difference of |mean reward| (5,000 resamples, seed 0, 95%
percentile CI):
1. **public-30 not worse**: CI not entirely above zero (from the candidate's ledger shards r7Lmbr2-pub30-1..3, all 30);
2. **HC2 better**: CI entirely below zero (all 44).
Ship as **v10** (`submission/transfer_policy.py` = v10b code with the r7L_mbr2 overrides baked in; v9 kept as
`submission/transfer_policy_v9_shipped_before_round8.py`) only if both hold. Otherwise v9 stays.
Reported either way: HS (18), M (12, r5m) and FD (20, r4c fresh default-range buildings) as secondaries if they finish
(they cannot change the decision), CI stability over bootstrap seeds 0-9, wins, worst single scenarios.

## Compute and Kaggle
Private Kaggle CPU kernels only (dispatcher `kaggle_sim.py`, dataset `neelsiri/sb26-sim-r6`, which already contains
r7hc); no Mac. HC2 shards first, then M, then FD. If v10 ships: one private Kaggle probe of v10 (the shipped file), and
v10 and v9 become the two final Kaggle selections (replacing v8). If it does not ship: no probe; v9 and v8 stay.

## Notes added after registration (no rule changed)
- 22:49 UTC: job files `round6/kaggle_jobs/r8-r7hc-1..4` (HC2, 44), `r8-r5m-1..2` (M, 12), `r8-r4c-1..3` (FD, 20) built with `jobs_r6.py make --variant r7L_mbr2 --policy-file round6/policies/v10b_screen.py --params policy_candidates/r7L_mbr2.json` (checked: every job carries those exact parameters and code, 8,640 steps) and enqueued, HC2 at the front; no HC2 run of the candidate existed before this line.
- 20:30 UTC 2026-10-30, **decision** (`compare_r8.py`, `confirm_r7L_mbr2.json`): the dispatcher had stalled from 2026-10-29 23:52 UTC to 2026-10-30 20:21 UTC (no log lines; the kernels finished on Kaggle meanwhile) and then fetched all four HC2 shards (44 summaries, code md5 296f75d3... = v10b_screen.py, params hash d449045d9a, 8,640 steps). HC2 (44): 0.02171 -> 0.02152, -0.88% [-0.98, -0.77], wins 43/44, CI below zero for bootstrap seeds 0-9; public-30: -1.62% [-2.02, -1.26], wins 30/30 (not worse for seeds 0-9). **Rule MET**: ship as v10. Secondaries at this point: HS (18) -0.80% [-0.93, -0.64], 17/18; M 6 of 12 back; FD running.
- 20:49 UTC 2026-10-30: shipped as v10 (`ship_round8.py`; `submission/transfer_policy.py` md5 7d7f6899..., sha256 dc606dbc...; v9 kept as `submission/transfer_policy_v9_shipped_before_round8.py`); shipped file = Kaggle confirmation runs bit for bit on building_train_8/{minneapolis_c2, denver_c1} at 8,640 steps (`xcheck_shipped_v10.json`); the one probe: private notebook neelsiri/sadr-v10-smart-buildings v1 (building_train_1/atlanta_2 -33.10639 on Kaggle vs -33.10215 local, 0.013%), submitted 20:48:56 UTC, ref 57816757 (`kaggle_feedback.json`).
- 22:50 UTC 2026-10-30: secondaries complete: M (12) -1.09% [-1.51, -0.67], 12/12; FD (20) -1.30% [-1.66, -0.90], 17/20 (`confirm_r7L_mbr2.json`); dispatcher stopped; probe ref 57816757 still pending.
