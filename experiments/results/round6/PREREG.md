# Round 6 pre-registration

## Part 1: harsh-weather sets, Kaggle-match criteria and the ship rule

Written 2026-10-26, about 11:05 UTC (04:05 PDT), on the laptop. At this time **no simulation has run on any round-6
scenario** (only two 12-step load tests of `building_train_7/fairbanks_c1` and `building_train_2/denver_c1`, total 0.00,
to check that the new configs load), and the only Kaggle kernel running is the reproduction test `sb26-r6-t01`
(v8 / v7 on three public scenarios and one r5m scenario, all of which have laptop results).
Part 2 (candidates) is appended after the v8 loss decomposition, before any candidate runs.

### What is known
- Kaggle public (about 10 of the 30 hidden scenarios): v8 0.01074, v7 0.01088, v6 0.01116, v5 0.01161, pid_water 0.06404.
- Round 5: the hidden buildings behave like the shipped six (v5/v7 Kaggle 1.067 vs public 1.058, default-size 1.169);
  the gap is weather. v7 on public-30 0.00786 (level 0.72 of Kaggle), on M (shipped six x Minneapolis, 12) 0.01119
  (1.03), P+M 0.00881 (0.81); pid_water/v7 Kaggle 5.89, public 7.00, M 4.30, P+M 6.02. On M, gas is 78% of v7's loss.

### Sets (all with the shipped six buildings; `experiments/src/make_sets_r6.py`, list in `sets_r6.json`)
Scenarios are built as in round 5 (copy of a shipped strip with the weather lines rewritten; the 120-rewrite
self-check passes byte for byte). **Cold-month strips** are new 30-day windows of the shipped station CSVs that no
shipped strip covers, starting on a Sunday at 06:00 like every shipped strip, with the station's convection coefficient:
fairbanks_c1 2023-11-26 (mean -20.1 C, min -38.9), fairbanks_c2 2023-01-15 (-21.7 / -41.1), minneapolis_c1
2023-11-26 (-4.4 / -20.0), denver_c1 2023-01-22 (-3.1 / -21.1; the coldest Sunday-start Denver window).

| name | n | content | use |
|---|---|---|---|
| **HC** = `heldout_scenarios_r6hc` | 48 | Minneapolis: the 24 building x strip pairs used by neither r5m nor r5ms (all 8 strips, 3 times each); Fairbanks shipped cold strips 1/2/8, one per building, none public or r5x; denver_1 x 6 (no set has used Denver strip 1); fairbanks_c1 x 6; minneapolis_c1 x 6 | **harsh confirmation set, never used before** |
| **HS** = `heldout_scenarios_r6hs` | 18 | r5ms's colder strip of each building (6); the other Fairbanks cold pairs (6); fairbanks_c2 x (train_1, 5, 8); denver_c1 x (train_2, 4, 7) | harsh screening set; v8 loss decomposition |
| H | 66 | HC + HS | reported |
| P | 30 | public-30 | ship guard |
| M, P+M, FD | 12, 42, 20 | round-5 sets (v8 runs exist from round 5) | secondary |

Disjointness (asserted by `make_sets_r6.py`): HC and HS share no scenario; neither contains a public scenario; HC
contains no round-5 scenario (r5m, r5ms, r5x); HS overlaps round 5 only in its 6 r5ms scenarios.

### Compute
Simulations run as private Kaggle script kernels (`experiments/src/kaggle_sim/`), with the laptop's kit and runner
uploaded as a private dataset. Before any Kaggle number is used, the reproduction test must match the laptop result
of the same (policy, scenario) to < 0.1% (expected: identical). All runs are 8,640 steps (30 days).

### Kaggle-match criteria (as round 5, with v8 as the reference policy)
Reference policies on HC and HS: v8 (shipped), v7, pid_water; v6 and v5 if compute allows (v5 is ~3x slower).
1. **Level** L_S(v8) / 0.01074 (closest to 1 is best).
2. **Shape** E_S = mean over probe policies p with runs on S of |ln(L_S(p)/L_S(v8)) - ln(K(p)/K(v8))|, Kaggle ratios
   v7 1.013, v6 1.039, v5 1.081, pid_water 5.963. Sets compared on the policies they share (stated).
3. Also reported: the mixture weight w with w L_HC(v8) + (1 - w) L_P(v8) = 0.01074 and the pid_water/v8 ratio that
   mixture implies, compared with 5.96 (tests "Kaggle = public-like stations + harsh stations").
"Matches Kaggle better" (goal 1) is read as: HC (or H) has a better level than P+M (0.81 for v7) and a shape error not
worse than P+M's by more than 0.02.

### Ship rule (fixed now)
A round-6 candidate C* replaces v8 in `submission/transfer_policy.py` only if, at 8,640 steps, with the paired
bootstrap of the mean per-scenario difference (5,000 resamples, seed 0, 95% percentile CI, metric |mean reward|):
1. **public-30 not worse**: CI not entirely above zero, AND
2. **HC better**: CI entirely below zero.
Reported either way, not required: HS, H, M, P+M, FD (round-5 secondary sets; FD/M v8 runs from round 5), the CI's
stability over bootstrap seeds 0-9, and the worst single scenarios. If no candidate meets the rule, v8 stays.

### Kaggle probes (goal 3)
At most 3 more submissions on 2026-10-26 UTC (1 already used: v8) and at most 4 per later UTC day. Each probe is a
locally screened variant, pushed with `kaggle_build.py`, its interactive run of building_train_1/atlanta_2 checked
against the local total, then submitted. Public-LB differences below 0.0005 are read as noise. Probes inform the
Kaggle-match analysis; they do not decide shipping (the rule above does).

## Part 2: candidates (written 2026-10-26, 12:10 UTC, after the v8 decomposition on HS; no candidate has run)

### What the decomposition shows (v8 on HS, 18 Kaggle diagnostic runs, `decomp_v8_r6hs.json`, `decompose_r6.py`)
- Metric 0.02243; **gas 95.3%** of the loss, fan 2.4%, comfort 1.5%, pump 0.4%, cooling 0.3%.
- Gas by policy mode and day type: occupied weekday 63.9%, preconditioning weekday 24.3%, preconditioning on
  weekend days (Sunday evening for Monday) 3.5%, setback weekday 1.4%, setback weekend 7.0%. By hour: 05:00-06:00
  14.5%, 06:00-07:00 12.2%, 04:00-05:00 7.2%.
- Outside-air (ventilation) load of running handlers = 0.49 of the gas: 0.43 through heated zones (the reheat that
  brings their own supply air up to zone temperature, 1 + (T - T_mix)/(T_disch - T) J of gas per J of net heat),
  0.04 through idle zones at the damper floor. The AHU only cools, the mixed air is 30% outside air at the
  recirculation cap, so in occupied hours this overhead is set by physics; the levers are when and how heat is
  delivered outside occupied hours.
- Morning recovery: zones heat for 2-3 h each before 06:00; time spent holding at the preconditioning target is
  small (2-10 zone-hours per morning against 50-260 recovering).
- **Frost**: the coldest weekend zone reaches -2.9 C (v8's weekend floor is about 2 C, 275 K; burst cycling at
  -38 C outside dips below it); 2.4% of all zone-steps are below 5 C.
- Recovery-rate fit (`recovery_fit_v8_r6hs.json`, `fit_recovery_r6.py`, 18,254 zone-mornings): within a zone the
  heating-step temperature rise *increases* with the lift (target - outside air), slope +0.027 K/h per K
  (95% CI +0.008 to +0.050). An outdoor-temperature-aware optimum start that predicts slower recovery in colder
  mornings (the planned `rate_oat_slope` > 0 candidates) contradicts this, so **those two candidates are dropped
  before running**; the per-zone EMA rate that v8 already learns is kept as the fitted thermal-response model.
  Also dropped: a lower occupied heating margin in cold weather (envelope arithmetic: 0.15 K of a ~40 K lift is
  < 0.5% of the heat); a cost-based supply-air temperature (Raftery et al. 2017) and avoiding simultaneous reheat and
  cooling under heating load (the AHU has no heating coil and the mixed air is below any SAT setpoint whenever the
  outside air is below about 10 C, so SAT cannot reduce heating; cooling is 0.3% of the HS loss); a hot-water supply
  reset tied to valve demand (the tank's dissipation at 350 K and -40 C outside is about 0.6 kW, from the kit's tank
  geometry, against 100-180 kW of gas in deep cold: < 1% even if it were removed entirely).

### Code
`experiments/src/policy_candidates/transfer_policy_v9.py` = v8 + round-6 switches, all off by default. Regression:
v9 defaults reproduce v8 bit for bit on building_train_8/fairbanks_c2 (576 steps, laptop); at full length r6_c00
(v9 defaults) runs on three HS scenarios on Kaggle and must equal v8's totals exactly, else nothing below counts.

### Candidates (single changes vs v8; `policy_candidates/r6_*.json`)
| id | change | hypothesis |
|---|---|---|
| r6_c01_boost8 | sb_boost 1, sb_boost_h 8 | in heating season, a set-back zone on a running handler within 8 h of a workday start gets its forced minimum flow reheated to the discharge limit instead of to its own temperature: the outside-air share of that flow is paid anyway, so the extra heat costs 1 J/J against ~1.5-1.9 J/J in its own ventilated recovery |
| r6_c02_boost4 | sb_boost 1, sb_boost_h 4 | same, less heat stored early (less leaks before 06:00) |
| r6_c03_sync08 | sb_sync_k 0.8 | a set-back zone within 0.8 K of its floor joins a heating burst running on its handler: one handler run instead of two |
| r6_c09_bfloor2 | sb_boost_floor_k 2 | a set-back zone within 2 K of its floor, on a handler running for another zone, is boosted through its forced air (1 J/J) instead of waiting for its own burst |
| r6_c06_mpre05 | margin_pre 0.5 | preconditioning target 0.5 K (not 0.8 K) inside the band: less heat before 06:00 (round 3: n.s. on 6+6 scenarios) |
| r6_c07_safe115 | lead_safety 1.15 | shorter leads: less recovery time at the ventilation overhead (comfort is 1.5% of the loss) |
| r6_c08_night10 | night_low_ext 10 | deeper weeknight setback (floor 279 K where the adaptive floor does not bind) |
| r6_c10_frost5 | frost_floor_k 278.15 | **sensible-practice variant**: setback floor never below 5 C; run to report its cost; not eligible as C* or for the composite |

Families (at most one member in the composite): boost {c01, c02}; burst sharing {c03, c09}; recovery {c06, c07};
depth {c08}. c10 is excluded from the composite.

### Screen (8,640 steps, paired vs v8)
HS (18) and **pub12** = the six public Fairbanks scenarios + building_train_1/denver_7, building_train_2/denver_8,
building_train_7/atlanta_8, building_train_8/atlanta_1, building_train_1/phoenix_5, building_train_7/singapore_6
(v8 reference: the laptop's round-5 runs, which the Kaggle runs reproduce bit for bit).
Classification as round 5 (paired bootstrap 95% CI, 5,000 resamples, seed 0): **helps** = HS CI entirely below zero
and pub12 CI not entirely above zero; **public only** = pub12 CI below zero, HS CI not above; **worse** = either CI
entirely above zero; otherwise **n.s.** Composite = every "helps" change, at most one per family (the member with the
lower HS metric), screened on the same sets. **C*** = lowest HS metric among the composite and the helping singles,
if it is classified helps; otherwise v8 stays and nothing is confirmed.

### Confirmation and ship rule
C* at 8,640 steps on HC (48), the remaining 18 public scenarios (to complete public-30), r5m (12) and FD (20);
ship rule of part 1 (public-30 not worse AND HC better). The frost variant's cost is reported on HS + pub12 (and HC if
compute allows). Kaggle probes (goal 3) are spent on screened variants, C* first.

### Notes added during the screen (no rule changed)
- 12:47 UTC: r6_c00 (v9 defaults) reproduces v8's 8,640-step totals exactly on all three HS scenarios
  (building_train_7/fairbanks_8, building_train_8/fairbanks_2, building_train_8/minneapolis_8).
- 12:50 UTC: local 576-step sanity runs of c01, c09 and c03 on building_train_8/fairbanks_c2 (an HS scenario) to check
  that the switches act (totals -18.89, -19.03, -19.37 against v8's -19.36); not used for any decision.
- r6_c02_boost4 is queued after the other singles (compute: the Kaggle account allows 5 concurrent CPU sessions,
  ~40 runs/hour); it still runs before the composite is formed.

### Amendment (13:35 UTC, after the first c01 shard: 9 of its 18 HS scenarios, -0.9% [-1.8, -0.2] vs v8)
c01 lowered the loss in the cold strips and raised it in the two mild April Minneapolis strips (+0.4%, +0.6%).
Added, **post hoc and labelled as such**: r6_c11_boost8cold = c01 + `sb_boost_cold` 1 (boost only while the outside air
is at or below the zone's setback floor, the condition round 4's `sb_neutral_cold` used). Code:
`results/round6/policies/v9_screen2.py` = v9_screen.py + that switch (diff of 5 lines; off = v9_screen). c11 joins the
boost family; its HS screen is not independent of the observation that motivated it, so if it is chosen the
confirmation on HC (never used) is what counts.

### Notes added during the round-6 resume (2026-10-26, after the network outage; no rule changed)
- 18:07 UTC: the Kaggle dispatcher was stopped and restarted with a fix: a push that failed during the outage
  (c06-r6hs-2, c07-r6hs-1, c08-pub12-1; the kernels were never created) had been dropped from the queue. These three
  shards ran on the Mac instead (same kit tarball and runner as the Kaggle dataset, `kaggle_sim/mac_shard_runner_r6.py`;
  a Mac rerun of a Kaggle job, r6_c06 on building_train_8/fairbanks_c2, matches the Kaggle total to 2e-11 relative,
  not bit for bit). c02's HS shards were split between Kaggle and the Mac for time.
- 19:35 UTC: every single except c02 (HS running) and c10 (not eligible) is classified. Unless c02 turns out "helps"
  with a lower HS metric than c11, the composite by the part-2 rule is c11 + c09 + c06 + c08. To save time its screen
  (HS + pub12 + building_train_1/atlanta_2) and its confirmation runs (HC, the other 17 public scenarios, r5m, FD) were
  started **speculatively** under the name `r6_compspec` (`policy_candidates/r6_compspec.json`, identical parameters).
  They are used only if the decision (`compare_r6.py decide`) produces exactly these parameters; the confirmation runs
  are not read before `decision.json` exists. If c02 changes the composite, they are discarded and reported as such.
- 20:44 UTC: `decide --stage composite` wrote r6_comp.json = c11 + c09 + c06 + c08, identical to r6_compspec.json, so
  the speculative runs count as r6_comp's (`compare_r6.sync_comp` mirrors runs/r6_compspec into runs/r6_comp);
  `decide --stage final`: C* = r6_comp (HS metric 0.02191, lowest in the pool).
- 21:10 UTC (after reading the public part of the confirmation): r6_comp is up to +4% on the Singapore and two Atlanta
  public strips; the screen ledger attributes this to c06 (margin_pre 0.5: +2.6% on building_train_7/singapore_6,
  +1.5% on building_train_1/phoenix_5), while c07 (the other recovery-family member, HS metric 0.0000048 higher) was
  -0.6% there. **Post hoc and ledger only:** r6_compb = c11 + c09 + c07 + c08 is run on HS and the public 30 for the
  January plan. It cannot replace C* this round; the ship rule is applied to r6_comp as fixed.
