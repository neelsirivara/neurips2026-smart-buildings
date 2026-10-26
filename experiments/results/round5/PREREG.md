# Round 5 pre-registration

Written 2026-10-25, 11:30 PDT (18:30 UTC), on the laptop, while the first round-5 jobs were being queued. At this time no round-5 simulation has finished
(only two 288-step smoke runs of the Kaggle cells), and no Kaggle score exists for v6, v5 or pid_water.
Part 2 (controller candidates) is appended later, before the screen starts, with its own time stamp.

## Part 1: which local scenario set predicts Kaggle

### What was known when this was written
- Kaggle public score of v7 (ref 57580485): **0.01088**, rank 75/315. The public split is about 10 of the 30
  hidden scenarios (6 hidden buildings x 5 hidden weather stations).
- Local v7 at 8,640 steps: public-30 0.00786; fresh shipped-range buildings (20) 0.00725; fresh default-range
  buildings (20) 0.01012; old held-out (40, default ranges) 0.01173; untouched held-out (74) 0.00971.
- Local v7/pid_water ratio: public-30 0.143; old held-out 40 0.230.
- Third-party calibration (public notebook `malyshevdanil/smart-buildings-probe-zt-best`, read for this
  round): the author reports local public-30 means and Kaggle public scores for three controllers built on the
  organizers' `PIDWaterResetPolicy`. Local -> Kaggle: 0.05493 -> 0.06439 (x1.17; only if their "v3" is the
  "transfer" baseline row, which is not certain), 0.04703 -> 0.05882 (x1.25), 0.03791 -> 0.05195 (x1.37).
  Ours: v7 0.00786 -> 0.01088 (x1.38). The author's local numbers were computed with the pre-PR #1 tracker
  (their building_train_1/atlanta_2 baseline 0.02418 equals the buggy local value quoted in Kaggle topic 749896).

### Candidate local sets
| name | scenarios | status |
|---|---|---|
| P | public-30 (shipped six x 5 public stations) | exists for v7, v6, v5, pid_water |
| M | **new** `heldout_scenarios_r5m`: shipped six x Minneapolis (unused station), 12 scenarios; building i of (1, 2, 4, 5, 7, 8) gets strips (i mod 8)+1 and ((i+4) mod 8)+1, so every strip of the year appears | to run: v7, pid_water, v6, v5 |
| P+M | the 42 together | derived |
| FS | fresh shipped-range buildings, round 4 (20) | exists for v7, v6 |
| FD | fresh default-range buildings, round 4 (20) | exists for v7, v6 |
| O | old held-out, default ranges (40) | exists for v7, v6, v5, pid_water |

M is built by `experiments/src/make_sets_r5.py` (copy of a shipped strip of the building with the weather lines
rewritten; self-check: rewriting every shipped scenario into every other shipped strip of its building
reproduces all 120 config files byte for byte).

### Kaggle probes (notebooks pushed 2026-10-25 18:25 UTC, submitted once their interactive run completes, before any local round-5 result)
v6 (round-3 policy), v5 (round-2 policy), pid_water (organizers' baseline), each pushed like v7 (one-cell
notebook, `experiments/src/kaggle_build.py`, which rebuilds the v7 cell byte for byte).

### Match criteria (fixed now)
1. **Level**: L_S(v7) / 0.01088; closest to 1 matches best.
2. **Shape** (primary once at least one more Kaggle score is in): for each policy p with a Kaggle score,
   r_S(p) = L_S(p)/L_S(v7) and r_K(p) = K(p)/K(v7); error E_S = mean over p of |ln r_S(p) - ln r_K(p)|.
   The lowest E_S predicts best; if two sets are within 0.02 of each other in E_S, the better level match wins.
   Sets lacking a policy are compared on the policies they have, and that is stated.
3. Probe readings (public LB about 10 scenarios; differences below 0.0005 are treated as noise):
   - |K(v6) - K(v7)| < 0.0005: no detectable effect of the round-4 switches on Kaggle.
   - K(v5) - K(v6) >= 0.0008 (about 7%): consistent with large (default-range) hidden buildings (local v5 -> v6:
     -12% on O, -3.4% on P); below 0.0005: consistent with shipped-range buildings.
   - K(v7)/K(pid_water) compared with P 0.143 and O 0.230 (and M once run).

### Kit PR #2 check (gas-billing fix)
v7 and pid_water at 8,640 steps on the 6 public Fairbanks scenarios, in a separate kit copy
(`results/round5/kit_pr2`, only `smart_buildings/{evaluate.py, baselines, smart_control, weather,
training_scenarios, heldout_scenarios_r5m}` copied) with the PR #2 diff (head ec27d9e, read from GitHub on
2026-10-25) applied; compared with the unpatched runs of the same scenarios. Expectation: v7 moves by less than
2% (it holds the hot-water setpoint steady); recorded either way. The gas-billing quirk itself is never used.

## Part 2: controller candidates (written 2026-10-25 11:50 PDT, before any candidate ran)

Known at this time: only two finished round-5 scenarios (v7 on building_train_1 x minneapolis_1/_5; nothing
else), the existing v7 diagnostics (`results/round5/analysis/comfort_*.json`: hour 06:00-07:00 carries 45-63% of
v7's comfort loss on every set, and on the old held-out set the Monday 06:00 hour costs twice any other weekday),
and the Kaggle probe submissions above (no scores yet).

Code: `experiments/src/policy_candidates/transfer_policy_v8.py` = v7 + round-5 switches, all off by default.
Regression before any screen: v8 with no parameter file must reproduce the frozen v7 file bit for bit
(576 steps on building_train_1/phoenix_5, building_train_2/denver_8, building_train_8/fairbanks_8); if it does
not, nothing below runs.

### Candidates (single changes vs v8 defaults = v7; `policy_candidates/r5_*.json`)
| id | change | hypothesis |
|---|---|---|
| r5_c01_mon15 | mon_lead_mult 1.5, mon_lead_max_h 12, mon_no_learn 1 | after a 60 h weekend setback the fabric is colder/warmer than after a night, so the lead learned from weekday mornings is short on Mondays (Monday 06:00 comfort 2x other days on the old held-out set); no learning from Monday recoveries keeps the weekday rates clean |
| r5_c02_mon125 | mon_lead_mult 1.25, mon_lead_max_h 10, mon_no_learn 1 | milder version |
| r5_c03_wk3 | wk_ext_lo 3 K, wk_ext_hi 2 K (ramped out 10-22 h before the next workday start) | lower weekend fabric temperature cuts envelope and ventilation-burst gas in cold weather (higher ceiling: chiller in hot weather); the ramp keeps Monday recovery unchanged |
| r5_c04_wk6 | wk_ext_lo 6 K, wk_ext_hi 4 K | deeper version |
| r5_c05_lag10 | lag_comp 1.0 | the zone sensor lags one step (host, topic 749945); extrapolating one step in the PI errors reduces overshoot |
| r5_c06_lag05 | lag_comp 0.5 | milder version |
| r5_c07_fcapc05 | f_cap_pre_c 0.5 | summer preconditioning of large zones is flow-capped at the floor-pressure flow; the hot share of 06:00 comfort (on every set) may come from that cap |
| r5_c08_qsb8k | q_sb_w 8000 | setback bursts run below the floor-pressure cap; a faster burst shortens handler run time, and with it the forced ventilation of the handler's other zones |
| r5_c09_preburst | pre_burst_h 1 (e0 0.3 K) | same argument for morning recovery: request the floor-pressure cap from the start instead of ramping through the integral |

**Amendment (2026-10-25 12:20 PDT, still before any screen job ran).** The v7 decomposition on r5m
(`results/round5/loss_decomposition_r5m_v7.json`, 11 of 12 scenarios; gas 77%, cooling 13%, comfort 6%) shows
that 80% of r5m's summed comfort loss is one scenario, building_train_7/minneapolis_1 (comfort 0.0057 per step of its
0.0410): four of its zones spend 458-1,150 occupied steps below the band (mean 0.5-3.3 K below 294 K) with
dampers at 84-100% and the handler near the pressure floor (240-280 Pa), consistent with the request cap `q_cap_w` binding (12 kW per 100 m2, 13.4 kW for the 112 m2 zone)
while the box and coil could deliver about 23 kW at the water-side limit (350 K water, 20 bar, -13 C outside). No public scenario puts building_train_7 in deep
cold. Added before any data on them:
| r5_c10_qcap20k | q_cap_w 20000 | lift the request cap where the box and coil can deliver more (round 3: n.s. on milder screens) |
| r5_c11_qcap30k | q_cap_w 30000 | effectively leaves the physical (box and water-side) caps binding |
and one screening scenario, building_train_7/fairbanks_1 (`heldout_scenarios_r5x`, the public building in the
January Fairbanks strip; not part of any confirmation set), added to held-10, which becomes **held-11**. The rules
below are unchanged (q_cap c10/c11 form one family).

### Screening sets (2,880 steps, paired vs r5_c00_v7 = v8 defaults)
- held-10: six scenarios of the new Minneapolis screening set `heldout_scenarios_r5ms` (shipped six x the Minneapolis
  strips that r5m does not use; one per building: train_1/minneapolis_7, train_2/minneapolis_8, train_4/minneapolis_1,
  train_5/minneapolis_2, train_7/minneapolis_3, train_8/minneapolis_4) + four round-4 screening scenarios
  (building_0520/fairbanks_1, building_0522/fairbanks_3, building_0523/denver_6, building_0524/phoenix_8).
- public-4: building_train_1/fairbanks_1, building_train_8/fairbanks_8, building_train_2/denver_8,
  building_train_1/phoenix_5.
r5m (the 12 Minneapolis scenarios of part 1) stays out of the screen, so it is a clean confirmation set.

### Classification, composite, choice (as in round 4)
Paired bootstrap 95% CI of the mean per-scenario difference (5,000 resamples, seed 0). helps = held-10 CI entirely
below zero and public-4 CI not entirely above zero; public only = public-4 CI below zero, held-10 CI not above;
worse = either CI entirely above zero; otherwise n.s. Composite = every change classified helps, at most one per
family (Monday c01/c02, weekend c03/c04, lag c05/c06, request cap c10/c11; others single), the member with the lower held-10 metric.
Choice C* = lowest held-10 screen metric among the composite and the helping singles, if its classification is
helps. If nothing helps, v7 stays and nothing is confirmed.

### Confirmation (8,640 steps) and ship rule
C* on public-30, r5m (12) and the set that part 1 finds most Kaggle-like (if that is a default-size set, its v7
runs exist; C* runs there too). Ship rule: public-30 not worse (CI not entirely above zero) AND better on the
Kaggle-like set (CI entirely below zero); r5m is reported either way. If part 1 has no shape result when the
confirmation must start, the Kaggle-like set is chosen by the level criterion. C* is then submitted to Kaggle as
one probe (public-LB difference vs v7 below 0.0005 = no detectable change; the local rule decides shipping).

## Note added 2026-10-25 18:12 PDT (after the four Kaggle probe scores; of the full-length confirmation only the building_train_1/atlanta_2 run of C*, used for the Kaggle cross-check, had finished)
Kaggle public: v7 0.01088, v6 0.01116, v5 0.01161, pid_water 0.06404. Applying part 1 literally ("sets lacking a
policy are compared on the policies they have"): E is lowest for FD (0.005) because FD (and FS) have only the v6
ratio, which every set matches within 0.004 (public 1.022, old held-out 1.029, M 1.031 vs Kaggle 1.026); FS and P+M
are within 0.02 (0.011 each) and FD has the best level (0.93), so the literal rule names **FD**. On the three probes
that only P, O, M and P+M have (v6, v5, pid_water), **P+M** is best (E 0.011; P 0.062, O 0.132, M 0.160); the
discriminating ratios are v5/v7 (Kaggle 1.067; public 1.058, default-size old held-out 1.169) and pid_water/v7
(Kaggle 5.89; public 7.00, M 4.30, P+M 6.02). Because the literal reading rests on the one non-discriminating
ratio, both readings are kept: v5 is run on part of FD (buildings 0604, 0607) to make FD comparable, and the ship
rule is applied conservatively: C* ships only if it is not worse on public-30 AND better (CI entirely below zero) on
**both** P+M and FD. r5m alone and old-40 (default size) are reported, not required.
(18:50 PDT: for time, the FD v5 runs were trimmed to building 0604 (5 scenarios); v5 runs about 3x slower in the simulator than v7.)
(22:40 PDT: the simulator ran about 2-3x slower from 18:10 on; the FD v5 runs and the remaining v5 runs on M were dropped from the queue so that the FD confirmation of C*, which the ship rule needs, runs right after public-30. FD's shape error therefore stays on the v6 ratio alone.)
