# Round 12: CMA-ES tuning of SADR v12's continuous constants (pre-registration)

Written 2026-11-07 ~01:30 UTC, before any round-12 run. Top item of `DEEP_DIVE.md` section 4 (expected 2-5% on the
Kaggle score; SADR's constants are physics-set, so far less than the 16% a weaker public controller gained this way).
Compute: private Kaggle CPU kernels only (dispatcher, at most 5 slots); no Mac before Monday Nov 9 (weekend booking).

## Search

- **Start:** the shipped v12 (`submission/transfer_policy.py`, `submission/best_params.json`), sha256 of the policy
  file recorded in `cma_state.json`.
- **Parameters (14), bounds, scale.** Everything else stays at v12's values.

  | parameter | v12 | low | high | scale |
  |---|---|---|---|---|
  | night_low_ext | 10 | 6 | 12 | linear |
  | night_high_ext | 6 | 3 | 9 | linear |
  | wk_ext_lo | 12 | 6 | 14 | linear |
  | sb_boost_floor_k | 2 | 0 | 4 | linear |
  | sb_boost_h | 8 | 4 | 12 | linear |
  | lead_safety | 1.15 | 0.9 | 1.5 | linear |
  | lead_base_h | 0.5 | 0.0 | 1.5 | linear |
  | margin_pre | 0.8 | 0.3 | 1.5 | linear |
  | margin_occ | 0.3 | 0.1 | 0.8 | linear |
  | q_sb_w | 4000 | 1500 | 10000 | log |
  | kq_w_per_k | 400 | 150 | 1000 | log |
  | ki_w_per_k_step | 120 | 40 | 300 | log |
  | valve_target | 0.9 | 0.7 | 0.98 | linear |
  | sat_mix_floor | 292 | 289 | 294 | linear |

  The two setback depths may go at most 2 K deeper than v12, because the reward has no frost cost (paper,
  Limitations). Deeper setbacks would lean further on that gap.
- **Algorithm.** CMA-ES with population 10 and 5 parents, sigma0 = 0.25 in the box scaled to [0, 1] (mirrored at
  the bounds), started at v12. It runs 15 generations or until sigma < 0.02. Seeded (20261107).
- **Objective.** 7-day windows (2,016 steps) on 24 fixed scenarios:
  - 12 harsh: two per shipped building from HS (`heldout_scenarios_r6hs`), the first two in sorted order;
  - 12 public-like: two per building from D10 (`heldout_scenarios_r10dev`), alternating (atlanta, phoenix) and
    (denver, singapore) by building index.

  Score = 1/3 x mean over harsh + 2/3 x mean over public-like of the per-scenario ratio of loss to v12 on the same
  window. This is the Kaggle mixture of `DEEP_DIVE.md` section 3. Lower is better. v12's reference windows run once,
  in generation 0.
- **Not used for tuning:** the public 30, HC3 (`heldout_scenarios_r10hc`), HH (`heldout_scenarios_r10hh`).

## Confirmation and ship rule (fixed now)

- **Candidate:** the CMA mean after the last generation (not the best sample, which would be selected on noise-free
  but window-specific scores).
- **Full-length runs (8,640 steps):** HC3 (40, cold), HH (40, hot) and the public 30. v12's runs on all three exist
  from rounds 10-11. Reusing HC3 and HH, which selected v12 over v11, favours v12, so the test is conservative for
  the candidate.
- **Primary:** the mixture ratio 1/3 x mean ratio on HC3 + 2/3 x mean ratio on HH, minus 1. Its 95% paired bootstrap
  CI over scenarios (2,000 resamples, stratified by set) must lie below 0.
- **Guard:** the mean ratio on the public 30 must not be above 1.000 (not worse).
- **Reported, not part of the rule:**
  - the cluster (building) bootstrap;
  - comfort, energy and carbon terms;
  - the coldest zone temperature and the share of zone-steps below 5 °C on HS. A deeper frost exposure is flagged to
    the user before anything ships.
- **If both pass:** the candidate becomes v13 in a candidate file. Shipping it and a Kaggle probe follow the usual
  checks. The Kaggle probe is reversible and may be submitted. The final Kaggle selections stay the user's.
- **If either fails:** v12 stays, and the result is reported as is.
