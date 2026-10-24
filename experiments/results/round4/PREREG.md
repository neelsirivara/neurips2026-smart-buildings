# Round 4 pre-registration (written 2026-10-23 before any policy was run on the new sets)

Reference policy: the shipped SADR v6 (`submission/transfer_policy.py`). Candidate code:
`experiments/src/policy_candidates/transfer_policy_v7.py` = the shipped file + round-4 switches that
default to off; `r4_c00_v6` (empty parameter file) must reproduce the shipped v6 bit for bit
(regression check before any screen; if it does not, nothing below is run).

## Sets

| name | scenarios | role |
|---|---|---|
| public-10 | the 6 public screening scenarios of rounds 2-3 + the other 4 Fairbanks public scenarios (train_1/fairbanks_1, train_2/fairbanks_2, train_4/fairbanks_4, train_7/fairbanks_7) | screen |
| held-26 | the 6 held-out screening scenarios of round 3 (already used for selection) + 20 new scenarios `heldout_scenarios_r4s` (buildings 0520, 0524 in the shipped six's parameter ranges; 0522, 0523 in the kit's DEFAULT_RANGES; one strip per station) | screen |
| public-30 | all public scenarios | confirmation (not worse) |
| old-34 | the 34 never-screened scenarios of the 40 old held-out (buildings 0501, 0502 and the six round-3 buildings) | confirmation (clean) |
| fresh-40 | `heldout_scenarios_r4c`, 8 new buildings x 5 stations: 0601, 0602, 0603, 0606 (shipped ranges), 0604, 0607 (default ranges), 0610 (largest rooms of seeds 606-699), 0639 (largest gross area of seeds 606-699) | confirmation (clean, never screened) |

Building generation: `experiments/src/make_sets_r4.sh` (`gen_buildings_r4.py`; materials stratified
per batch as in the kit's `run_floor_generator.py`). Seeds the kit rejects (zones < 20 m2: 521, 600,
605) are replaced by the next free seed that passes (524, 606, 607). Weather strips: Latin square,
building i, station s -> strip (i + 2s + offset) mod 8 + 1 (offset 0 for r4s, 4 for r4c).

Why two parameter-range families: the kit's DEFAULT_RANGES (used for the round-3 buildings) do not
reproduce the six shipped buildings (seed 0 -> 597 x 494 ft vs building_train_1, seed 0, 373 x 188 ft;
the shipped six span width 318-430, height 188-301, rooms 25-51), while the kit README says the
Kaggle evaluation buildings come from "the same generator and parameter ranges as the shipped six".
The shipped-range buildings are the closer proxy for the leaderboard; the default-range ones keep
the large-zone stress test. Results are reported for both subsets of fresh-40.

## Candidates (single changes vs r4_c00_v6; `policy_candidates/r4_*.json`)

| id | change | hypothesis (from the round-4 diagnosis, `results/round4/diag_*.json`) |
|---|---|---|
| r4_c01_fcap_floor | f_cap_pre 0.316 (= the floor-pressure flow; any value <= 0.316 is clipped here in v6) | continues the round-3 trend; gain via lower preconditioning pressure |
| r4_c02_fcap025 | f_cap_pre 0.25, f_cap_min 0 | below the floor no pressure is saved; expected neutral or worse (slower recovery) |
| r4_c03_fcap015 | f_cap_pre 0.15, f_cap_min 0 | same |
| r4_c04_fcap005 | f_cap_pre 0.05, f_cap_min 0 | same, extreme |
| r4_c05_disch025 | disch_margin_k 1.0 -> 0.25 | the simulator caps the discharge at 308.15 K itself; a hotter assumed discharge needs ~6% less flow per J, so less ventilation air to heat (gas) and less fan |
| r4_c06_mix_relief | sat_mix_relief 1 | on handlers that heat and cool the 292 K supply floor forces big cooling zones to full flow and the handler to high pressure (40% of the above-floor fan power on the round-3 buildings); serve them at floor pressure with colder air instead |
| r4_c07_occ_dyn | occ_press_dyn 1, e0 0.3 K, span 1.0 K | above-floor fan power is 26% of fan energy on the round-3 buildings (0.00047/step) and raises every zone's forced flow; comfort is per occupant (1-2 per zone, whatever the area); allow pressure above the floor only in proportion to the zone's error |
| r4_c08_occ_dyn_mild | occ_press_dyn 1, e0 0.1 K, span 0.5 K | milder version of c07 |
| r4_c09_flush | flush_on 1 (dT 3 K, target hi_pre - 1 K but >= lo_pre + 0.5 K, window 8 h before a workday) | Denver/Atlanta summer nights have OAT >= 3 K below the zones on 30-98% of unoccupied steps; outside-air flushing at floor pressure moves heat at ~8-14 J/J vs the chiller's 3.5 at 18-20 c/kWh |
| r4_c10_sb_neutral | sb_neutral 1 | in heating season the forced minimum flow of set-back zones on a running handler chills them; reheating it now costs 1 J/J vs ~1.9 J/J in the ventilated recovery later (Fairbanks) |

## Screen (2,880 steps, both screening sets, paired vs r4_c00_v6)

Paired bootstrap 95% CI of the per-scenario metric difference over scenarios (4,000 resamples, seed 0).
Classification per change: **helps** = held-26 CI entirely below zero and public-10 CI not entirely
above zero; **public only** = public-10 CI below zero and held-26 CI not above zero; **worse** = either
CI entirely above zero; otherwise **n.s.**

Composite: all changes classified helps or public only, at most one per family (f_cap_pre values:
c01-c04; occupied cap: c07/c08), the family member with the lowest held-26 metric among those that
help. The composite is screened too. **Choice C\***: among the composite and the single changes
classified helps, the lowest held-26 screen metric whose classification vs c00 is helps. If nothing
helps, v6 stays and nothing is confirmed at full length.

## Confirmation (8,640 steps) and ship rule

C\* and v6 at full length on fresh-40 (v6 on public-30 and on the old 40 is the round-3 run of the
same code, re-used only if the r4_c00 regression is bit-identical); C\* on public-30 and the old 40.
Paired bootstrap 95% CIs over scenarios (5,000 resamples, seed 0).

**C\* ships iff** (1) public-30: CI of C\* - v6 not entirely above zero (not worse); (2) the pooled 74
never-touched held-out scenarios (old-34 + fresh-40): CI entirely below zero (better); (3) neither
old-34 nor fresh-40 alone has its CI entirely above zero. Otherwise v6 stays and the ledger says so.
The shipped-range subset of fresh-40 (20 scenarios, the closest proxy for Kaggle) is reported with
its own CI but is not a ship condition. Numbers only from result files; a non-significant difference
is reported as such.
