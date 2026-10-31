# Round 7 pre-registration

## Part 1: sets and ship rule (written 2026-10-29 ~17:45 UTC, before any round-7 candidate has run)

### What has run in round 7 before this was written (analysis only, no candidate)
- `check_identities_r7.py`: 576-step runs of the shipped v9 on two harsh screening scenarios (HS) with the simulator's
  own methods wrapped (identity check of the heating cost; ANALYSIS.md section 1).
- `zone_log_r7.py`: 14-day runs of v9 on six HS scenarios on the Mac, per-zone net heat logged; first-order zone
  models fitted (`fit_zone_model_r7.py`, `zone_model_fit.json`) and the lever predictions (`analysis_r7.py`).
- `r7chk-1` (Kaggle, 7-day `run_diag.py` runs on three HS scenarios): v9 and v9 with night_low_ext 12 / 14 and
  lead_safety 1.15 / 1.0, to check the analysis's predictions against the simulator. These are fixed parameter changes
  of v9, not round-7 candidates; HS scenarios only.
- v10 code (`policy_candidates/transfer_policy_v10.py`, built by `make_v10_r7.py` from the frozen v9 code
  `results/round6/policies/v9_screen2.py`): with the round-7 switches off it reproduces v9 bit for bit (576 steps,
  building_train_8/fairbanks_c2, `results/round7/regress/`); one 7-day development run of the model with both switches
  on (`debug_mbr_r7.py`, building_train_8/fairbanks_c2; total reward printed only, not a result).
- Known before this was written, from round 6 (post hoc there): r6_compb (= v9 with c07 lead safety 1.15 instead of c06
  preconditioning margin 0.5) against v9: public-30 -0.65% [-1.13, -0.20], HS +0.04% [-0.04, +0.13], FD -0.94%
  [-1.38, -0.46].

### Sets
| name | n | content | use |
|---|---|---|---|
| **HC2** = `heldout_scenarios_r7hc` | 44 | the shipped six under six new 30-day cold-month windows of the shipped station CSVs (fairbanks_c3 2023-01-29, fairbanks_c4 2023-11-05, minneapolis_c2 2023-01-22, minneapolis_c3 2023-02-05, denver_c2 2023-01-01, denver_c3 2023-02-05; Sunday 06:00 starts; each overlaps an earlier window by 9-16 days), fairbanks_c2 x (train_2, 4, 7), denver_c1 x (train_1, 5, 8), train_4/fairbanks_8, train_5/fairbanks_2 (`make_sets_r7.py`, `sets_r7.json`); **no building x strip pair of HC2 has been run in any earlier round** (asserted) | **confirmation, never used before** |
| HS | 18 | round 6's harsh screening set | screen |
| P | 30 | public-30 | screen and ship guard |
| HC, M, FD | 48, 12, 20 | round 6 / 5 / 4 sets | secondary, reported |

### Reference and ship rule (as round 6)
Reference: the shipped v9 (`submission/transfer_policy.py`; runs = round 6's r6_comp runs, plus v9 on HC2 run for this
round). A round-7 candidate C* replaces v9 in `submission/transfer_policy.py` only if, at 8,640 steps, paired bootstrap of
the mean per-scenario difference (5,000 resamples, seed 0, 95% percentile CI, metric |mean reward|):
1. **public-30 not worse**: CI not entirely above zero, AND
2. **HC2 better**: CI entirely below zero.
Reported either way: HS, HC, M, FD, CI stability over bootstrap seeds 0-9, worst single scenarios. If no candidate
meets the rule, v9 stays; the two Kaggle selections stay v9 and v8 unless the rule picks a new one.

Kaggle: at most one probe per UTC day, private notebook, C* first.

Part 2 (candidates and the screen rule) is appended after the analysis checks, before any candidate runs.

## Part 2: candidates and the screen rule (written 2026-10-29 ~18:10 UTC, after the analysis checks; no candidate has run)

### What the analysis and the checks showed (`analysis_r7.json`, `checks_r7.json`; no candidate involved)
- Heating cost identity g = (T_d - T_sa)/(T_d - T) holds in the simulator to 2e-12; recirculation sits at its 0.7 cap,
  82% of the net heat goes in at the 308.15 K discharge cap: the outside-air and discharge levers are exhausted; what
  is left is *when* and *at what zone temperature* heat is delivered.
- First-order zone fits: tau median 33 h, C median 1.35 kWh/K; R^2 0.41 on 30-min windows; recovery time predicted to
  within 27% (median). At the cap the recovery rate falls by 0.60 K/h per K of zone temperature (median).
- Depth: deeper floors never cost gas in the model when reached and recoverable; the v9 floor binds on 1-47% of
  unoccupied zone periods. Checks (7 days, measured vs predicted gas): floor -2 K: -1.14 vs -1.00 % (train_8 /
  fairbanks_c2), -0.90 vs -0.87 % (train_7 / denver_c1), +0.05 vs -0.43 % (train_1 / fairbanks_c2); floor -4 K:
  -2.27 vs -1.78, -1.07 vs -1.32, +0.21 vs -0.80 %. Right size where the floor binds, wrong sign in the heavy
  building_train_1.
- Start: the hold at the target before 06:00 averages 0.36 h per recovery and carries 2.6% of the gas. Checks: lead
  safety 1.15: -0.73 vs -1.62, -1.17 vs -1.43, -0.13 vs -1.52 % gas; 1.0: -1.44 vs -2.03, -2.17 vs -1.98, -0.96 vs
  -2.51 % gas, with part of the gas saving returned as comfort (loss -1.26, -1.16, -0.32 %). The prediction is an upper
  bound (it assumes every hold is removable), as section 6 of the analysis says.

### Candidates (v10 code, frozen as `results/round6/policies/v10_screen.py`, md5 c21e1c65...; parameters in
`experiments/src/policy_candidates/`)
| id | parameters | hypothesis |
|---|---|---|
| r7_base | v9 with c07 (lead safety 1.15) instead of c06 (preconditioning margin 0.5) | removes v9's hot-strip / large-building comfort cost (round 6 ledger, post hoc there; its HS and public runs already exist as r6_compb) |
| r7_mbr | r7_base + `mbr_on` (model-based start, safety 1.1) | a start from a per-zone first-order model that knows the rate falls as the zone warms removes part of the 2.6% hold without late arrivals |
| r7_mbf | r7_base + `mbr_floor` (model-chosen floor, down to eco band - 16 K, safety 1.1) | deeper floors where the model says the zone reaches them and recovers in time: the analysis predicts -0.0 to -1.7% of gas per cold week, most in light buildings |
| r7_mb | r7_base + both | the two are complementary (start vs depth) |
No other candidate; no post-hoc additions to the eligible pool (anything added later is ledger only).

### Screen (8,640 steps, paired against v9 = r6_comp)
Sets: HS (18) and the **full public-30** (round 6's twelve-scenario public screen under-sampled the hot strips).
Classification as round 6 (5,000 resamples, seed 0): helps = HS CI entirely below zero and public CI not entirely above
zero; worse = either CI entirely above zero; public only = public CI below zero and HS CI not above; else n.s.
**C\*** = the lowest HS metric among the candidates classified *helps*. If none helps, v9 stays and nothing is confirmed
(r7_base is classified like the others; its public-only gain does not make it C\*).

### Confirmation and ship rule (part 1)
C\* and v9 at 8,640 steps on HC2 (44, never used); public-30 from the screen; HC, M, FD reported. Ship only if public-30
not worse AND HC2 better (paired bootstrap as above). Kaggle: one probe of C\* at most per UTC day.

### Notes added during the screen (no rule changed)
- 18:59 UTC, after the first r7_mb HS shard (9 of 18 scenarios, +1.0% [-0.6, +3.0] against v9): building_train_7 uses
  4-5% more energy (comfort better), because the model-based start uses the model's lead also where the model says the
  target is unreachable at the cap (lead -> 8 h) and where the model's lead exceeds the learned-rate lead. **Post hoc and
  ledger only:** switch `mbr_lead_cap` (v10b code, `results/round6/policies/v10b_screen.py`; off = v10): the model may
  only shorten the learned-rate lead and is ignored where its target is unreachable -- the "latest feasible start" of
  the analysis. Variants with it are reported in the ledger and cannot be C* this round.
- 22:17 UTC, decision (`compare_r7.py screen` + `decide`, `decision.json`): all four candidates complete (HS 18,
  public-30 30) and classified **public only** (no HS CI entirely below zero); the classes are the same for bootstrap
  seeds 0-9 (`screen_seed_classes.json`). No C*: nothing confirmed, v9 stays shipped, HC2 stays unused by any
  candidate, no Kaggle probe this round. The ledger variant r7L_mbr2 (mbr_lead_cap) is reported post hoc only.
