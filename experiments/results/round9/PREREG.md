# Round 9 pre-registration

## Part 1: sets, reference and ship rule (written 2026-11-01 ~02:35 UTC, before any round-9 candidate has run on a
## screening or confirmation set)

### What has run in round 9 before this was written (analysis of v10 only; no candidate)
- Kaggle shards `r9-v10diag-1..5`: the shipped v10 with `run_diag.py` on the public 30 and HC2 (44), for the loss
  decomposition the coordinator asked for (v10's HC2 *summaries* were already known from round 8; the per-step split
  is new).
- Mac batch `v10_diag12` (paused by the GPU lock at the time of writing): v10 with `run_diag_r9.py` on 6 public and
  6 HC2 scenarios, for the delivery bound.
- Code: `policy_candidates/transfer_policy_v11.py` (built by `make_v11_r9.py` from the shipped v10 file) with two
  switches, off by default; with both off it reproduces v10 bit for bit (700 steps, building_train_1/fairbanks_1,
  laptop, `results/round9/regress/`).
- Development runs (7 days, building_train_1/fairbanks_1, public, laptop): v10 -85.98; `obr_on` (occupied band
  riding) -178.56, a comfort collapse (diagnosed in `results/round9/dbg/obr`: with the handler off the zone air falls
  to the slab temperature within one 5-minute step, so occupied heat cannot be delivered in bursts). `obr_on` is
  dropped and will not be screened.

### Sets
| name | n | content | use |
|---|---|---|---|
| HS = `heldout_scenarios_r6hs` | 18 | round 6's harsh screening set (seen in rounds 6-8) | screen |
| P = public 30 | 30 | the shipped scenarios (seen in every round) | screen and ship guard |
| **HC2** = `heldout_scenarios_r7hc` | 44 | round 7's cold-window set; used once, in round 8, for v10 vs v9; no round-9 candidate has run on it | confirmation |
| M = `heldout_scenarios_r5m`, FD = `heldout_scenarios_r4c` (FD_B buildings) | 12, 20 | rounds 4-5 sets | secondary, reported |

Dev runs of candidates are limited to public and HS scenarios (7-day windows), never HC2.

### Reference and ship rule (as rounds 6-8)
Reference: the shipped v10 (`submission/transfer_policy.py`, md5 7d7f6899...; its runs = round 8's
`results/round6/runs/r7L_mbr2/<set>`). A round-9 candidate C* replaces v10 in `submission/transfer_policy.py` only if,
at 8,640 steps, paired bootstrap of the mean per-scenario difference of |mean reward| (5,000 resamples, seed 0, 95%
percentile CI; `compare_r9.py confirm`):
1. **public-30 not worse**: CI not entirely above zero, AND
2. **HC2 better**: CI entirely below zero.
Reported either way: HS, M, FD, CI stability over bootstrap seeds 0-9, wins, worst single scenarios. If no candidate
meets the rule, v10 stays. If one ships it becomes v11 beside v10 (v10 kept as
`submission/transfer_policy_v10_shipped_before_round9.py`; v9 / v8 copies untouched). No Kaggle submission in this
round without the coordinator.

Part 2 (candidates and the screen rule) is appended after the decomposition and bounds, before any candidate runs
on HS or P.

## Part 2: candidate(s) and the screen rule (written 2026-11-01 ~03:05 UTC; no candidate has run on HS, P, HC2, M or FD)

### What the analysis showed before this was written (v10 only; `bound_r9_v10.json`, `decomp_mac12.json`)
- 12 v10 runs with plant internals (`run_diag_r9.py`; 6 public, 6 HC2): occupied heat is delivered at the
  instantaneous lower bound (coil duty above "net need at the cap, or need + the forced air's outside-air share while
  the handler runs" = 0.2-0.5% of the gas); unoccupied delivery 0.8-1.8%; the hot-water loop (tank charging,
  dissipation, the flow term billed at the setpoint while a warming tank lags it) 0.4-0.7% of the gas in the cold
  scenarios and 1.1-3.6% in the mild ones (Denver, Atlanta: 3-5 loop re-warms of 1.5 m3 by 40 K each per month).
- The occupied band-riding idea (handler off between bursts) is infeasible: the zone air relaxes to the slab within
  one step (dev run in Part 1). Not a candidate.
- HC2 note: six HC2 scenarios of v10 were among the 12 diagnosed runs and the loop shares above use them; no
  candidate code has run on HC2.

### Candidate B = `r9_hwl` (hot-water loop management), fixed
- code `results/round9/policies/v11_screen.py` (= `src/policy_candidates/transfer_policy_v11.py`, built by
  `make_v11_r9.py` from the shipped v10), md5 1384db600fbf580bd8f195b898c528cd,
  sha256 c3a58277340bf718fc577b5030f8b3775eafe1ce50d1cfad5f04fbc271eb106b;
- parameters `results/round9/params/r9_hwl.json` = {"heat_season_steps": 2016, "tw_ramp_k": 2.5},
  sha256 8196ac2e478a7b9b8843c64baa8067d621eedc58a2b30bf1e2d8c5fee2c5c6d5; every other parameter at v10.
- What it is: (1) the loop stays hot for 7 days after the last heating demand (v10: 1 day), so a mild spell no
  longer cools 1.5 m3 of water by 40 K only to reheat it; (2) while the pump runs the setpoint is kept within
  [tank, tank + 2.5 K] (the tank rises 0.5 K/min = 2.5 K per step anyway, so warm-ups are as fast as before), so the
  shipped boiler no longer bills the loop flow for a setpoint the tank has not reached, and the setpoint never goes
  below the tank while water flows (well clear of the under-billing quirk, which needs the opposite). Under PR #2's
  energy-balanced tank (2) changes nothing and (1) still saves the re-warms.
- Hypothesis: about -1 to -2% of the gas on mild public strips (Denver, Atlanta), about 0 on hot strips, -0.05 to
  -0.2% on cold ones. Dev run before registration: building_train_7/atlanta_8, 7 days: -12.44 vs v10 -12.50
  (`results/round9/dev7d`).

### Screen (as rounds 6-7) and the path to confirmation
- Runs: 8,640 steps on HS (18) and P (30), private Kaggle kernels (`jobs_r6.py make --variant r9_hwl --policy-file
  results/round9/policies/v11_screen.py --params results/round9/params/r9_hwl.json`), compared with v10's runs
  (`compare_r9.py screen`).
- A candidate goes to the HC2 confirmation if its HS mean change is below zero and its public-30 CI is not entirely
  above zero. The ship rule of Part 1 then decides (public-30 not worse AND HC2 CI entirely below zero).
- A further candidate may be added from the LP bound (`lp_bound_r9.py`, P/HS scenarios only) as a dated amendment
  below, before it runs on any of these sets; it gets the same screen and rule.

### Amendment 1 (2026-11-01 ~03:15 UTC): candidate C = `r9_mprs`, before it ran on HS, P, HC2, M or FD
- Prototype C is model-predictive recovery (`mpr_on`): each zone's air temperature gets a second-order model fitted
  online by RLS on its unoccupied 5-minute history (T(k+1)-T(k) = a (T(k)-T(k-1)) + b Q(k) - c (T(k)-T_out) + d);
  before a workday the zone starts at the latest step from which the model, heating at the preconditioning request
  cap, reaches the preconditioning target, times `mpr_safety`; as v10's model start, it may only shorten the
  learned-rate lead. Code `results/round9/policies/v11c_screen.py` (= `transfer_policy_v11.py` regenerated by
  `make_v11_r9.py` with the mpr switch; all round-9 switches off = v10 bit for bit, 700 steps,
  building_train_1/fairbanks_1, `results/round9/regress/v11off_b`), md5 97c1b27db4a1a10f6753ce299d0f3a96, sha256
  1ce2157d0f56cbce047e9ea992526f9bdce6651dd93b43a15207b95c8a259ca2.
- Development runs (7 days, building_train_1/fairbanks_1, public; v10 -85.98): with burst recovery at the cap
  (`mpr_burst` 1, safety 1.1) -91.86, comfort regret -10.09 vs -2.25 (the air reaches the target fast, the slab does
  not: zones fall back after 06:00) -- the burst form is dropped; start model only (`mpr_burst` 0, safety 1.3)
  -85.32 (-0.8%). These two dev runs used a public scenario, so the public screen is not clean for C.
- Candidate C, fixed: parameters `results/round9/params/r9_mprs.json` = {"mpr_on": 1.0, "mpr_burst": 0.0,
  "mpr_safety": 1.3}, sha256 4afbab26765b5f6000f797e3ddf07f624870dc4a809a5b7077321be44a2273b6; everything else v10.
- Same screen, same path to confirmation, same ship rule as candidate B. If both B and C go to confirmation, each is
  confirmed separately against v10; if both meet the rule, the one with the lower HC2 mean ships (no composite
  without a further registered test).

### Amendment 2 (2026-11-01 ~03:45 UTC): candidate D = `r9_dow` (a bug fix), before it ran on HS, P, HC2, M or FD
- Found while reading v10's weekend trajectories (12 diagnosed runs, public and HC2, `results/round9/mac/v10_diag`):
  v10 preconditions **every Saturday morning** (about 02:00-06:00, a full recovery, then back to setback at 06:15),
  1.5-5.1% of the gas in every one of the 12 runs, Sunday mornings never. Cause (`src/debug_saturday_r9.py`): the
  day-of-week observation is an integer day sent as float32 sin/cos; v10 decodes it with atan2 and compares the raw
  float, `workday_ahead = day_next < 5.0`; Saturday decodes to 4.999999999 (and the day after Sunday to
  6.99999998, so on Sunday evening the Monday recovery may not start before midnight).
- Candidate D, fixed: `dow_snap` = round the decoded day to the nearest integer (no tunable parameter). Code
  `results/round9/policies/v11d_screen.py` (= `transfer_policy_v11.py` regenerated with the dow_snap switch; all
  round-9 switches off = v10 bit for bit, 700 steps, `results/round9/regress/v11off_d`), md5
  e6a6f6aaa212c6cdbfb065a13cf84e09, sha256 88e92f969033e4c6bce07c91a133c610e1a5d6161e492ed266ece47e3c86f179;
  parameters `results/round9/params/r9_dow.json` = {"dow_snap": 1.0}, sha256
  14b9c2c47a25796788888ed846bbca343e9c81cde52a7f3b1d8431d006ca4e61.
- Dev run before registration: building_train_8/fairbanks_8 (public), 14 days: -78.05 vs v10 -81.18 (-3.9%; energy
  -4.1%, carbon -3.9%, comfort regret -1.22 vs -1.12).
- Same screen, path to confirmation and ship rule as B and C. D is screened and confirmed first (Kaggle queue
  order). If more than one candidate meets the rule, the one with the lowest HC2 mean ships; a composite (e.g. D + B)
  would need its own registered confirmation.
- Note (03:50 UTC): D's confirmation shards (`r9dow-r7hc-1..4`, `r9dow-r5m-1`, `r9dow-r4c-1..2`) are queued right
  behind its screen to save time; their results are not read before the screen decision is recorded here.
- **Screen decision for D (2026-11-01 ~05:35 UTC, `compare_r9.py screen`, `screen_summary.json`), recorded before any
  confirmation run of D was read**: HS (18) 0.02173 -> 0.02139, -1.59% [-1.96, -1.24], 18/18 wins; public-30
  0.00762 -> 0.00753, -1.23% [-1.88, -0.69], 28/30 wins; class "helps" -> D goes to the HC2 confirmation (its shards
  are already running). B and C screens incomplete at this time.
- **Decision for D (2026-11-01 ~06:30 UTC, `compare_r9.py confirm --cand r9_dow`, `confirm_r9_dow.json`)**: HC2 (44)
  0.02152 -> 0.02120, **-1.50% [-1.71, -1.30]**, wins 44/44 (worst building_train_1/denver_c2 -0.84%), CI below zero
  for bootstrap seeds 0-9; public-30 0.00762 -> 0.00753, -1.23% [-1.88, -0.69], 28/30 (worst building_train_7/denver_5
  +0.41%), not worse for seeds 0-9. **Rule MET: ship D as v11.** B and C are still in their screens; D is the only
  confirmed candidate, so it ships alone (amendment 2: a composite would need its own registered confirmation).
- Note (2026-11-01 ~08:05 UTC): B's screen so far (HS 18/18 -0.15% [-0.23, -0.07]; public 19/30 -0.34% [-0.60,
  -0.11]) points to "helps", but its HC2 confirmation is not run: under amendment 2 a second confirmed candidate ships
  only with a lower HC2 mean than D's (0.02120), which needs about -1.5% on HC2 against B's -0.15% on the harsher HS;
  B (and C) are kept for the ledger and for a January composite with v11, which would need its own registration.
- Note (2026-11-01 ~08:10 UTC, `compare_r9.py screen`): B's public screen is complete: public-30 0.00762 -> 0.00758,
  -0.55% [-0.82, -0.30], 18/30 wins (HS unchanged, -0.15% [-0.23, -0.07], 18/18): class "helps"; still not confirmed,
  for the reason above (ledger only; January composite candidate).
- Note (2026-11-01 ~09:25 UTC, `compare_r9.py confirm --cand r9_dow`, `confirm_r9_dow.json`): D's FD secondary
  (outside the rule) is in: FD (20) 0.01000 -> 0.00994, -0.59% [-1.33, +0.07], 13/20 wins; worst
  building_0639/denver_6 +2.76% (energy, comfort unchanged); the losses sit on the two default-range buildings with
  the largest rooms (0610, 0639). Decision unchanged (the rule does not include FD).
- Note (2026-11-01 ~09:55 UTC, `compare_r9.py screen`, `screen_summary.json`): C's screen is complete: HS (18) -0.42%
  [-0.59, -0.26], 16/18; public-30 -0.14% [-0.33, +0.02], 14/30: class "helps"; not confirmed for the same reason as
  B (ledger only). Round 9 is closed: every registered candidate has its screen recorded; only D shipped.
