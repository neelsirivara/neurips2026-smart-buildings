# SB26 improvement deep dive (round 6, 2026-10-26; updated after rounds 7-8, 2026-10-30; round 9, 2026-11-01)

## R10. Round 10 (2026-11-02): v12 shipped

v12 = v11 + deeper weekend setback + second-order start model + 7-day heating season gated at 15 C. HC3 (fresh, 40 cold) -1.41% [-1.75, -1.11], 40/40; public-30 -0.97% [-1.40, -0.59], 21/30; HH (fresh, 40 hot) +0.04% [-0.02, +0.11]. Comfort regret +20% on HC3, April Phoenix slightly worse. The setpoint ramp is left out as billing-related; a cooling integral x3 is worse. Details: `STATUS.md` (round 10), `experiments/results/round10/PREREG.md`. The sections below predate this.

## R9. Round 9 (2026-11-01): is there a large legitimate gain? (v11 shipped; all screens complete; round-10 dev added)

Question (coordinator): v10 is 0.01055 on Kaggle; #10 needs about -45%. Where could that come from?

**Five-line summary**
1. v10's loss is heating gas (HC2 94%, public 51%, Kaggle mixture ~79%) and, on hot strips, chiller electricity
   (public 41%); comfort is 2.7-2.8%, fans 2.5-4.9%.
2. Heat delivery is already at the physical minimum (occupied coil duty within 0.5% of the instantaneous bound;
   the zone air follows the slab within one step, so the handlers cannot be cycled off in occupied hours); the
   remaining legitimate slack is *when* zones are heated: a perfect-foresight LP on the kit's own linear building
   model finds 10.5-15.1% of v10's loss (mean 12%) on seven heating scenarios, about 11% after v11 -- mostly
   weekends and weeknight recovery timing. That bound is loose: its largest piece, the weekend free-float, tested
   directly in the simulator (round-10 dev, 6 cold HC2 scenarios) gives -0.3 to -0.45%, not 4-9%.
3. A quarter of that is a v10 bug: the float32 day-of-week feature decodes to 4.999999999 on Saturdays, so v10
   recovers the building every Saturday morning (2.9% of HC2's loss, 1.7% of the public 30's). Fix = candidate D.
4. The top of the leaderboard is the billing quirk: the simple published saw-tooth alone takes v10 to ~0.0069
   (rank ~37), a tuned one to ~0.0058 (rank ~10); no legitimate lever comes within a factor of three of the 45%.
5. Prototypes: band riding and burst recovery fail physically; the Saturday fix (D) met the pre-registered rule
   (HC2 -1.50% [-1.71, -1.30], 44/44; public -1.23%) and is **shipped as v11**; the hot-water loop (B: HS -0.15%,
   public -0.55%), the second-order start model (C: HS -0.42%, public -0.14%) and the weekend free-float (E, dev:
   -0.3 to -0.45%) are small (ledger only).

**Leaderboard read (2026-11-01 ~03:00 UTC, read-only CLI, `experiments/results/round9/intel/lb_p{1,2}_*.csv`)**:
#1 0.00470, #3 0.00514, #10 0.00588, #20 0.00612, #30 0.00647, #50 0.00781, #100 0.01037; v10 0.01055 is #113 of
400 shown. The top moved from 0.00521 (10-26) to 0.00470; 39 teams are below 0.007.

**What v10's loss is made of** (all 74 scenarios: v10 with `run_diag.py` on private Kaggle kernels, totals identical
to round 8's runs; `results/round9/decomp_v10_{pub30,hc2}.json`, `src/decomp_r9.py`):

| set | loss | gas | chiller | fan | comfort | pump |
|---|---|---|---|---|---|---|
| HC2 (44) | 0.02152 | 94.2% | 0.1% | 2.5% | 2.8% | 0.5% |
| public 30 | 0.00762 | 51.0% | 41.2% | 4.9% | 2.7% | 0.2% |
| public Fairbanks / Denver / Atlanta | 0.01516 / 0.00456 / 0.00512 | 92 / 57 / 45% | 3 / 30 / 46% | 3 / 6 / 6% | 2 / 6 / 2% | 0 |
| public Phoenix / Singapore | 0.00733 / 0.00593 | 8 / 1% | 84 / 91% | 6 / 6% | 3 / 2% | 0 |
| Kaggle mixture (66% public, 34% HC2) | | ~79% | ~17% | ~3.6% | ~2.8% | ~0.3% |

By the score's own terms: HC2 carbon 70% / energy cost 27% / comfort 2.8%; public 30 energy 51% / carbon 47% /
comfort 2.7%. By mode on HC2: occupied hours 68% of the loss, preconditioning 25%, setback 7%. Comfort: on cold sets
below the band (6-8 am: 68% of it), on hot strips above it (slow cooling PI, see the bounds table).

**Bounds, lever by lever** (share of the gas or of the loss that any controller paying for its gas could still remove):

| lever | bound | evidence |
|---|---|---|
| occupied heat delivery | 0.2-0.5% of gas | coil duty vs the instantaneous minimum (need at the 308.15 K cap, or need + the forced air's outside-air share while the handler runs), 12 runs, `bound_r9_v10.json` |
| handler off between occupied bursts | infeasible | the zone air relaxes to the slab within one 5-min step; band riding: -178.56 vs -85.98 (7 days, fairbanks_1) |
| unoccupied delivery | 0.8-1.8% of gas | same instantaneous bound on night bursts / recovery |
| hot-water loop (tank charging, dissipation, flow billed at a setpoint the tank has not reached) | 0.4-0.7% of gas cold, 1.1-3.6% mild | `bound_r9_v10.json`; candidate B |
| heating cost per joule g = (T_cap - T_sa)/(T_cap - T) | physics | 30% outside air at the 0.7 recirculation cap; median g 1.75 |
| chiller per joule of net cooling | physics | 1.14 (Singapore) - 1.33 (Phoenix) = the outside-air share at 285 K supply air |
| comfort | <= 2.8% of loss, partly physical | building_train_7 deep cold: perimeter boxes at the coil's water-side limit (~20 kW at -24 C); on hot strips a control gap: the occupied cooling PI's integral adds only 30-60 W per step, so on mild Phoenix mornings zones drift 0.1-0.3 K above 297 K for hours with dampers 20-35% open (building_train_7/phoenix_3: comfort 10% of its loss; `experiments/src/debug_cooling_pi_r9.py`) |
| trajectory (when and how deep zones are heated) | independent per-zone LP: 12-16% of gas, 17-20% of loss (optimistic: each zone free-rides on neighbours held at v10's temperatures); **coordinated (16 damped Gauss-Seidel sweeps over the cross-zone responses, scored jointly): 10.5-15.1% of the loss, mean 12.2% over seven heating scenarios** (HS building_train_8/fairbanks_c2 11.2%, building_train_4/minneapolis_1 10.6%, building_train_7/denver_c1 15.1%; public building_train_1/fairbanks_1 10.5%, building_train_2/fairbanks_2 11.6%, building_train_7/fairbanks_7 11.9%, building_train_4/denver_2 14.2%; `results/round9/lp_summary.json`), of which the Saturday bug is about 2-3 points. Check with v11 as the base: public building_train_8/fairbanks_8 from v10 (0.02248) -12.7%, from v11 (0.02194) -10.6%, both to the same optimum 0.0196; building_train_1/fairbanks_1 from v10 (0.04434) -10.5%, from v11 (0.04384) -9.4%, both to 0.0397; HS building_train_7/denver_c1 from v10 (0.02388) -15.1%, from v11 (0.02324) -13.2%, both to 0.0202. So **after v11 about 9-13% (mean 11%) of the loss remains for a perfect-foresight controller** on heating scenarios (`results/round9/mac/lp_bound_dow`). **Realisability check (round-10 dev, below): the LP's biggest piece does not transfer** -- free-floating the weekend in the real simulator gives -0.3 to -0.45% of the loss (the Monday recovery costs nearly what the weekend saves, and Monday comfort pays the rest), so the LP is an order of magnitude looser than what a causal controller can reach | perfect-foresight LP on the exact linear building model (`lp_bound_r9.py`: v10's logged heat replayed through the kit's own solver, RMSE 0.14-0.51 K; 1 kW impulse responses; 30-min blocks; comfort hard or score-priced at the expected occupancy share 1/V; holiday mornings kept until 06:15). Where it saves (HS building_train_8/fairbanks_c2): **Saturday 0-7 h -1,406 kWh (the Saturday bug, candidate D)**, Saturday 7 h-Sunday -4,643 kWh with +1,091 kWh more Monday recovery (free-float the weekend instead of re-heating to the floor on Sunday afternoon), weeknights -821, occupied hours -242 kWh |

**Prototypes** (all in `experiments/src/policy_candidates/transfer_policy_v11.py`, built by `make_v11_r9.py` from the
shipped v10; every round-9 switch off = v10 bit for bit):

| id | idea (aimed at) | dev run (7 days, building_train_1/fairbanks_1, v10 -85.98) | status |
|---|---|---|---|
| A `obr_on` | occupied band riding: bursts at the cap, handlers off between (the forced-air share of occupied gas) | -178.56 (comfort regret -106.8 vs -2.25) | dropped: the zone air follows the slab within one step |
| B `r9_hwl` | hot-water loop kept hot 7 days, setpoint within [tank, tank + 2.5 K] (loop re-warms, warm-up over-billing) | building_train_7/atlanta_8: -12.44 vs -12.50 | screen HS -0.15% [-0.23, -0.07] 18/18, public-30 -0.55% [-0.82, -0.30] 18/30 ("helps"); not confirmed: it cannot displace D under amendment 2; January composite with v11 |
| C `mpr_on` + burst | model-predictive recovery: second-order online zone model, latest start, recovery at the cap (morning gas) | -91.86 (comfort -10.09) | dropped: the air reaches the target, the slab does not |
| C `r9_mprs` | the same model, start only (may only shorten v10's lead), safety 1.3 | -85.32 (-0.8%) | screen HS -0.42% [-0.59, -0.26] 16/18, public-30 -0.14% [-0.33, +0.02] 14/30 ("helps"); not confirmed (ledger only) |
| E `wk_free` (round-10 dev, not registered) | weekend free-float: no heating floor from Friday evening to Monday's lead, Monday lead cap 8/12/16 h, with or without the model lead (aimed at the LP's largest piece) | 6 cold HC2 scenarios, 30 days, vs v11: **-0.34% mean / -0.42% pooled** (5/6; energy + carbon -1.3%, comfort +0.9%); 16 h cap = 12 h cap; learned-rate lead only -0.24% / -0.45% (4/6); deeper weekend setback alone (`wk_ext_lo` 12, the round-5 parameter) -0.37% / -0.45%, 6/6, comfort-neutral | not pursued this year: far below the LP's 4-9%; `wk_ext_lo` 12 joins B in a January composite (`results/round10/dev/dev_table.json`) |
| **D `r9_dow`** | **bug fix**: v10 decodes the float32 day-of-week feature as 4.999999999 on Saturdays and compares it with 5, so it runs a full morning recovery every Saturday (1.5-5.1% of the gas in all 12 diagnosed runs) and cannot start Monday's recovery before midnight on Sunday; `dow_snap` rounds the day | building_train_8/fairbanks_8, 14 days: -78.05 vs -81.18 (**-3.9%**) | **shipped as v11**: screen HS -1.59% [-1.96, -1.24] 18/18, public-30 -1.23% [-1.88, -0.69] 28/30; confirmation **HC2 -1.50% [-1.71, -1.30], 44/44**; M -1.70% [-2.75, -0.76] 11/12; FD -0.59% [-1.33, +0.07] 13/20 (losses on the two largest-room generated buildings, worst +2.8%) |

**The billing quirk, measured** (analysis only: `quirk_probe_r9.py` overrides v10's hot-water setpoint in the harness
with the saw-tooth published in topic 752142; never in a policy file, nothing submitted; Mac, 10 probes + 1 harness
check, `results/round9/quirk_summary.json`): the harness without the override reproduces the official v10 run on
building_train_1/atlanta_2 (-33.1021529 vs -33.1021527). With it, loss x0.54-0.62 on the Fairbanks, Minneapolis and
Denver scenarios with comfort unchanged, x0.83 Atlanta, x1.00 Phoenix and Singapore (no heating). Scaled by station
to the public 30 (x0.77) and HC2 (x0.58) and through the 66/34 Kaggle mixture (calibrated on v10's 0.01055):
**v10 + the simple published saw-tooth = 0.0069 (-35%, about rank 37)**. PR #2 reports 0.38x billing for a tuned
saw-tooth (round 6's estimate 0.0058, about rank 10); the leader's 0.0047 needs about 0.27x. The top of the board is
what this quirk produces on a controller of v10's class; no legitimate lever in the table comes close.


**Why the leaders are ahead, and what that means for us.**
- Legitimate ceiling. Through the 66/34 Kaggle mixture (calibrated on v10's 0.01055), v11 should score about
  **0.0104** (HC2 -1.50%, public -1.23%; below the public split's ~0.0005 resolution). A perfect-foresight controller
  on the kit's exact linear model would remove another ~9-13% (mean 11%) on heating scenarios (and less on hot strips, where
  the chiller's outside-air share is physics), i.e. roughly **0.0094-0.0097**: about rank 80-90 on today's board.
  About 70 teams are below that. That LP ceiling is loose: its largest piece (the weekend) realises about a tenth of
  its value in the simulator (round-10 dev), so the reachable legitimate score is more like **0.0102-0.0103**.
- The billing quirk explains the board: the published simple saw-tooth alone takes v10 to ~0.0069 (rank ~37);
  PR #2's tuned saw-tooth (0.38x billing) to ~0.0058 (rank ~10); the leader's 0.0047 needs ~0.27x. The quirk's
  reproduction code has been public in topic 752142 since 10-23.
- So the ranking we can influence is the one after a fix: if the hosts re-run with PR #2-style billing (v7 moved
  -0.4% under PR #2 in round 5), quirk users lose 30-50% and a v11-class controller should rank near the top of the
  legitimate field. Whether to ask the hosts for the ruling is the coordinator's call (no posting from this round).

**Next steps (ranked)**
1. Final selections v11 + v10 (coordinator); optional private probe of v11 (`src/kaggle_probe_r9.py build/push/check`;
   submit only with the coordinator's go-ahead).
2. Weekends: tested (round-10 dev, prototype E): a weekend free-float gives -0.3 to -0.45% on cold scenarios, a
   deeper weekend setback (`wk_ext_lo` 12) -0.37% with no comfort cost. The LP's weekend slack is mostly not
   realisable; a 2-node (air + slab) recovery model is the only route left to more of it. January composite
   (B + `wk_ext_lo` 12) needs a fresh confirmation set: `src/make_sets_r10.py` builds one (8 new shipped-range
   buildings x 5 cold strips = 40; written, not yet run).
3. Hot strips: the occupied cooling PI's integral is too slow at the morning load ramp (zones 0.1-0.3 K above 297 K
   for hours; comfort 2-10% of hot-strip loss). A faster cooling integral or a drift feed-forward is cheap, but the
   cold HC2 rule cannot confirm it: it needs a hot-window confirmation set.
4. Hot-water loop (B): -0.15% on HS (18/18), -0.55% on the public 30 (18/30); fold into a January composite.
5. CMA-ES distribution tuning (section 4, item 3) on top of v11.

## R6. Round 6 deep dive (2026-10-26) and updates after rounds 7-8

Scope: how to lower SADR's Kaggle score before the poster deadline (Nov 13, 2026) and the final deadline (Jan 15,
2027) without the gas-billing quirk. Every number below comes from a result file named next to it; third-party numbers
(discussion posts, public notebooks) are quoted as their authors state them and were not reproduced unless noted.
Numbers file: `experiments/results/round6/deep_dive_numbers.json` (`experiments/src/deep_dive_r6.py`); Kaggle reads
(read-only CLI, 2026-10-26 ~19:05 UTC): `experiments/results/round6/intel/`.

**Five-line summary**
1. v8 is 0.01074 on Kaggle (rank 87); the leaders' 0.00521 is about what a v8-like controller would score if gas were
   billed at the quirk's 0.38x (estimate 0.0058), so distance to #1 is not a usable target; #20 (0.00685) and a
   third-party physics-consistent controller (-7% vs v8 on the coldest public week) are.
2. The hidden split behaves like 2/3 public-like weather + 1/3 deep cold; there, gas is ~75% of our loss, the chiller
   ~19%, comfort ~2%: the remaining levers are when and how heat is delivered outside occupied hours.
3. Round 6 shipped v9 (-2.0% on 48 unseen harsh scenarios, a tie on the public 30, no gain on large default-range
   buildings); its flaw is a comfort/cooling-side cost of the preconditioning-margin change on hot strips (up to +4%), which the shorter-lead change seems
   to avoid: the post-hoc ledger composite r6_compb is -0.9% on the public 30 (CI -1.8% to -0.2%) and as good on the
   half of the harsh screen run so far (not a confirmation).
4. The best next steps: (a) a round-7 screen that fixes that cost and pushes the setback/boost settings (0.5-1.5%,
   Nov 13); (b) CMA-ES tuning of SADR's constants over many generated buildings and NOAA stations (2-5%, Jan 15);
   (c) a model-based morning recovery (1-3%, Jan 15).
5. Public notebooks (best 0.0142) offer nothing SADR lacks except distribution tuning; never use the billing quirk or
   the occupancy-seed replay.

## 0. Update after rounds 7-8 (2026-10-30)

**Five-line summary (rounds 7-8)**
1. Analysis (paper Sec. 5): heat costs g = 1 + (T - T_sa)/(T_d - T) J of gas per J (checked in the kit to 1e-11);
   recirculation sits at its 0.7 cap and 82% of the heat enters at the 308.15 K discharge cap, so outside air and
   discharge temperature are spent levers; only *when* and *at which zone temperature* heat goes in remain.
2. Bounds: a deeper floor pays only where it binds (1-47% of unoccupied zone periods under v9); a start rule saves at
   most the hold before 06:00 (2.6% of the gas). First-order zone models are weak (R^2 0.41), right-sized where the
   floor binds, wrong-signed in slow buildings.
3. Round 7: base (c07 for c06), model start, model floor and both were all "public only" against v9 (model start
   public -1.4%, 29/30, but HS +0.4%, n.s.: it lengthened leads on building_train_7); nothing shipped.
4. Round 8: the fix (the model may only shorten the learned lead), registered before its only clean test, met the
   rule: HC2 (44) -0.88% [-0.98, -0.77], 43/44; public-30 -1.62% [-2.02, -1.26], 30/30; FD -1.30% (17/20), M -1.09% (12/12); **shipped as v10**.
5. Ranked items 2 (c06's cost) and 4 (model-based recovery) are done; 5 (deeper setback) is answered by the analysis
   (depth pays only where the floor binds; the 7-day checks give -1% gas there, ~0 elsewhere); the remaining large
   item is 3 (distribution tuning, Jan 15).

| ranked item (section 4) | status after rounds 7-8 |
|---|---|
| 1 ship v9 | done (round 6); v9 is now the second final selection |
| 2 fix c06's cost | done: v10 uses c07 (lead safety 1.15) instead of c06 |
| 3 CMA-ES distribution tuning | open (Jan 15); the lever analysis narrows it to timing constants (lead, boosts, floor depth where it binds) |
| 4 model-based morning recovery | done in its bounded form (v10); a full planner can gain at most the hold (2.6% of gas) and the zone models are too weak for it |
| 5 deeper setback / boost sweep | answered: the model floor is a tie (HS -0.03% vs the base); depth only helps light zones that reach the floor |
| 6 selection hygiene | applied (HC2 built before any round-7 candidate; seen vs clean sets stated) |
| 7 chiller side | open |
| 8 learned residual | open, low priority |

## 1. Where we stand

| | score | source |
|---|---|---|
| SADR v8 (round 5; best scored file) | 0.01074, rank 87 (86 teams ahead; 82 on 10-26 07:10 UTC) | `results/kaggle_feedback.json`, `round6/intel/lb_page1_2026-10-26T1905Z.csv` |
| SADR v9 (shipped in round 6) | 0.01070 (probe 57678857) | `results/kaggle_feedback.json` |
| SADR v10 (shipped in round 8) | 0.01055 (probe 57816757; read 2026-10-31) | `results/kaggle_feedback.json` |
| round-6 single c01 (probe) | 0.01071 (v8 0.01074: noise) | same |
| #1-#2 (Joe Penn, Pardheev Krishna) | 0.00521 | same CSV |
| #8 (last leaderboard prize) | 0.00603 | same CSV |
| #20 | 0.00685 | same CSV |
| best public notebook | 0.01420 (probe-zt-best); 0.01500 for the CMA-ES-tuned K07 constants (topic 752324) | notebook text / topic |

The leaders are at 0.49x our score. The public split is about ten scenarios, so differences below about 0.0005 are noise.

## 2. What the top public notebooks and threads do that SADR does not

The 22 public notebooks are unchanged since 10-22 (`intel/kernels_*_2026-10-26.csv`); all are rule-based and the best
reports 0.0142, worse than every SADR version since v5. None of the top-20 teams has published code. What is new or
relevant, with our assessment:

| source | what it does | SADR today | worth doing? |
|---|---|---|---|
| Topic 752324 (A. Pacheco Bobillo, 10-24) + dataset `alepacheco/smart-buildings-distribution-tuning` | **CMA-ES tuning of 15 constants** of the public K07 controller over buildings from the kit's generator under **2023 NOAA weather from twelve airports**; no shipped scenario used for tuning; -13.5% / -16.9% on two held-out building sets, **0.01788 -> 0.01500 on the public LB (-16.1%)** | SADR's ~60 constants were set by physics, a 16-configuration random search (v4) and one-at-a-time screens (rounds 3-6); never tuned jointly over a distribution | **Yes (top Jan-15 item).** The K07 controller had far more headroom than SADR, so expect much less than 16%; but it is the only published method with an LB-verified gain, and its two ingredients (external weather stations, distribution-level objective) also fix our selection problem (section 3) |
| Topic 752142, comment by H. Alayet (10-26) | reports a **"twin-based LP planner"** at -85.4 on building_train_1/fairbanks_1, first 7 days, shipped simulator (their plant-inversion baseline -102.4; the PR #2 author's "physically consistent controller" -81.9) | **v8: -88.42** on the same window (`round6/deep_dive_7day/`, laptop, 2016 steps; v7 -94.18 from `results/final_r4` time series) | **Yes, as evidence of headroom:** two independent physics-consistent controllers are 3.4% and 7.4% better than v8 on SADR's worst public scenario. A planner with a plant twin is the January direction (item 4 below) |
| probe-zt-best (Malyshev) | median-demand SAT, cooling-run hold 288 steps, weekend -6 K, min pressure, per-zone economic target shift | SADR has coldest SAT (round 4: mixed-handler relief n.s.), starts handlers 2.4-4.8 times a day (round 5: cycling not a lever), weekend -6/+4 K since v8, floor pressure, 0.3 K margin | No: covered or tested |
| facilities-v17 (jazivxt) | weather-qualified hot-water reset in mild weather; warmest feasible SAT | 350 K in heating season, 310 K otherwise | No: tank dissipation is < 1% of the harsh-set loss (PREREG round 6); warm SAT is wrong in this simulator (constant COP, fan ~ P^1.5) |
| Topic 752619 (B. Bartling) | notes the VAV boxes are pressure-dependent (no airflow sensors) so a true G36 trim-and-respond is not possible | SADR already inverts flow = damper x sqrt(P / P_design) in closed form | Nothing to add; consistent with our design |
| Topic 752678 (E. Shieh) | the occupancy model's fixed RNG seed (17321) could be replayed to predict per-zone arrivals | not used | **Do not use** (asks for a ruling; same class as the billing quirk: it exploits hidden configuration, not control) |
| Topics 749531 / 751998 / 752142 + starter-kit PR #2 | gas-billing quirk (setpoint saw-tooth bills heat at 0.38x) | not used; round 5 showed SADR's score does not rest on it (v7 -0.4% under PR #2, pid_water +23%) | **Never.** See the estimate in section 3 of how much of the leaders' margin it could explain |

## 3. Where our remaining loss is

**Which weather Kaggle is.** Round 6 fitted the Kaggle score with the two local sets: v8 scores 0.00777 on the public 30
(P, level 0.72 of Kaggle) and 0.01657 on the new harsh confirmation set HC (level 1.54). A mixture of 34% HC and 66% P
matches v8's Kaggle score by construction and then *predicts* pid_water's Kaggle ratio: 5.81 against the observed 5.96,
2.6% low (pid_water on all 48 HC scenarios; `round6/set_match.json -> mixture_P_HC`). So the hidden split behaves like
two-thirds public-like weather and one-third deep-cold weather.

**Loss by component** (leaderboard units per step; shares from the full diagnostic decompositions):

| set | v8/v7 metric | gas | chiller | fan | comfort | pump | file |
|---|---|---|---|---|---|---|---|
| P, v7 | 0.00786 | 52.3% | 40.1% | 4.8% | 2.5% | 0.2% | `round4/loss_decomposition_public_v7.json` |
| P Fairbanks, v7 | 0.01598 | 92.4% | 2.6% | 2.9% | 1.8% | 0.4% | same, `by_station` |
| P Phoenix / Singapore, v7 | 0.00741 / 0.00593 | 8.0% / 0.7% | 83.5% / 91.0% | 6.0% / 6.0% | 2.5% / 2.3% | 0 | same |
| P Atlanta / Denver, v7 | 0.00524 / 0.00471 | 46.2% / 58.0% | 45.3% / 29.6% | 6.4% / 6.5% | 2.0% / 5.9% | 0.1% | same |
| M (Minneapolis, 12), v7 | 0.01119 | 78.3% | 12.1% | 3.8% | 5.5% | 0.3% | `round5/loss_decomposition_r5m_v7.json` |
| HS (harsh screening, 18), v8 | 0.02243 | 95.3% | 0.3% | 2.4% | 1.5% | 0.4% | `round6/decomp_v8_r6hs.json` |

Weighting P and the harsh part 66/34 (HS shares used for the harsh part), **gas is about 75% of v8's Kaggle loss, the
chiller about 19%, fans about 3.5% and comfort about 2%**. Comfort is already near its floor; the score is an energy
problem, and mostly a cold-weather gas problem.

**Where the gas goes (HS, v8):** 63.9% in occupied weekday hours, 24.3% in weekday preconditioning (05:00-06:00 alone
14.5%, 04:00-05:00 7.2%), 7.0% in weekend setback, 3.5% preconditioning on Sunday evening, 1.4% weeknight setback. The
outside-air load of running handlers equals 0.49 of the gas, 0.43 of it through heated zones: the handler cannot
heat, at least 30% of the supply is outside air and at the 308.15 K discharge cap each joule of net heat costs
1 + (T - T_mix)/(T_disch - T) joules of gas. In occupied hours that overhead is physics; the levers are when and how
the heat is delivered outside occupied hours, and how much envelope loss the setback floor allows.

**How much a physics-consistent controller can still gain.** On building_train_1/fairbanks_1 (SADR's worst public
scenario), first 7 days, shipped simulator: v8 -88.42 (laptop run, `round6/deep_dive_7day/`), v7 -94.18, against
-85.4 for a third party's "twin-based LP planner" and -81.9 for the PR #2 author's "physically consistent controller"
(topic 752142; not reproduced). That is 3-7% headroom on the hardest public scenario for controllers that do not use
the billing quirk.

**How much of the leaders' margin the billing quirk could explain (estimate, not evidence of use).** PR #2 measured
gas billed at 0.38x the delivered heat for a tank-cycling policy. Applied to v8's Kaggle composition (gas 75%):
0.01074 x (1 - 0.75 x 0.62) = 0.0058, close to the top scores (0.00521-0.00556). A physics-consistent controller
therefore cannot be judged by its distance to #1; #20 (0.00685) and the 7-day comparison above are better yardsticks.

## 4. Ranked changes

Expected gains are on the Kaggle score unless stated, read through the 66/34 mixture (section 3); "noise" means below
the ~0.0005 public-LB resolution, so most items can only be verified locally. Costs are compute on Kaggle CPU kernels
(5 sessions x 4 workers) plus the Mac (<= 8 simulator workers), and developer time.

| # | change | evidence so far | expected gain | cost | Nov 13 (poster) | Jan 15 (final) |
|---|---|---|---|---|---|---|
| 1 | **Ship v9 (round-6 composite)** -- done | confirmed at full length: harsh confirmation set (48) -2.05% [-2.70, -1.43], public-30 -0.27% [-1.35, +0.65], M -1.28%; FD (large default-range buildings) +0.60% [-0.37, +1.36], n.s.; rule met; **shipped** (`submission/transfer_policy.py`); Kaggle probe 57678857: 0.01070 | about -1% (P part -0.3%, harsh part about -2.4%); not resolvable on the public LB | done | yes | yes |
| 2 | **Fix the cooling-side cost of c06** (preconditioning margin 0.5 K): apply it to the heating target only, or use c07 (lead safety 1.15) in the recovery family | confirmation: FD +0.60% (n.s.) with comfort up by more than the net change; r6_comp is +0.2% to +4.0% on the six public Singapore strips (five above +2.5%) and +3.1% / +3.7% on two Atlanta strips; the screen ledger puts it on c06 (+2.6% on building_train_7/singapore_6, +1.5% on phoenix_5) while c07 is -0.6% there; post-hoc `r6_compb` (c07 instead of c06): public-30 -0.92% [-1.80, -0.24] vs v8, -0.65% [-1.13, -0.20] vs v9, HS (9 of 18) -2.52% | +0.5-1% on the public-like two-thirds of Kaggle | one pre-registered screen + confirmation (about 3 h of Kaggle + Mac) | yes (round 7) | yes |
| 3 | **Joint distribution tuning (CMA-ES) of SADR's continuous constants** on generated shipped-range buildings x many stations (shipped six + NOAA ISD cold and hot stations), objective = the Kaggle mixture (1/3 harsh, 2/3 public-like), 7-day windows for speed, held out by station | topic 752324: -16.1% on the public LB for a weaker public controller; round 6: single constants move the harsh-set loss by 0.3-1% each and add nearly linearly (sum of the four members -2.6%, composite -2.3%) | 2-5% (much less than 16%: SADR's constants are already physics-set) | about 400-500 core-hours (12 candidates x 30 generations x ~20 scenario-weeks); 1-2 days of Kaggle + Mac; tooling exists (job files, dispatcher, Mac runner) | no | **yes, top item** |
| 4 | **Model-based morning recovery**: per-zone RC/ARMAX model fitted online in each episode, plan the preheat start and power to reach the band at 06:00 at least gas (an LP over the next 8 h with the replayed strip as forecast) | preconditioning = 24.3% of HS gas (05:00-06:00 alone 14.5%); weekend setback 7.0%; third-party twin-based LP planner -85.4 vs v8 -88.42 on fairbanks_1, 7 days; Seem et al. 2016 recommend 2-parameter recovery models without outdoor temperature (consistent with our round-6 fit) | 1-3% (cold part), 3-7% on the worst public scenario | 1-2 weeks of development; policy time must stay < 10 ms/step | no | yes |
| 5 | **Deeper weeknight setback and boost sweep** (night_low_ext 12/14 K, sb_boost_floor_k 3 K, sb_boost_h 10 h) as one pre-registered screen | c08 (8 -> 10 K) -0.8% HS; boosts -0.5% to -1.0% HS; frost floor shows the cost side (+0.9% HS for a 5 C floor) | 0.3-1% | one screen (about 2 h) | yes (with item 2) | yes |
| 6 | **Selection hygiene**: screen and confirm on a fixed Kaggle-weighted mixture (HS/HC + public-like), add NOAA ISD stations, keep the paired bootstrap and pre-registration | the 66/34 mixture predicts pid_water's Kaggle ratio (5.81 vs 5.96); the public set alone under-predicts Kaggle (level 0.72) and favours hot-strip changes; round 6's pub12 screen (2 hot strips of 12) missed c06's Singapore cost | indirect: fewer wrong ships | set generation (hours) | yes | yes |
| 7 | **Chiller side** (19% of the Kaggle loss; 84-91% of Phoenix/Singapore): pre-cooling of the fabric with outside air only where it is colder than the zones, chiller-aware occupied pressure | round 4: night flush helped Denver/Atlanta summers up to -7%, rarely possible in Phoenix/Singapore; constant COP leaves no part-load lever | <= 1% | screen | no | maybe |
| 8 | **Learned residual (RL) on top of SADR** | none locally; CityLearn 2023 winner was heuristic + classical control and most entries overfit | uncertain, risky | weeks + large compute | no | only if 3-4 are done |

Not worth doing (checked): hot-water reset (tank loss < 1% of the harsh-set loss), cost-based SAT under heating load
(the handler cannot heat), no simultaneous reheat/cooling (cooling is 0.3% of the harsh loss), outdoor-temperature
optimum start (the fit contradicts it), handler cycling (2.4-4.8 starts a day), lower occupied heating margin
(< 0.5% of the heat), joining another zone's burst (c03: no effect).


## 5. Do not

- Exploit the gas-billing quirk (hot-water setpoint saw-tooth) in any form, including "accidentally" through a
  hot-water reset that cycles the setpoint below the return temperature.
- Replay the public occupancy model or its RNG seed to predict per-zone arrivals (topic 752678).
- Tune on the 30 public scenarios: they under-predict Kaggle (v8 level 0.72) and favour hot-climate changes.
- Read public-LB differences below ~0.0005 as signal (about ten scenarios).

## 6. Literature worth citing (verified 2026-10-24 / 2026-10-26: title, venue and claim read from the source)

Already in the paper: Goldfeder & Sipple 2023 (simulator), Goldfeder et al. 2025 (control suite), the SB26 starter
kit, ASHRAE Guideline 36-2021, Taylor 2018 (VAV design), Wang & Hong 2020 (RL review). Worth adding:

1. **Goldfeder et al., "The Smart Buildings Challenge: Learning Foundation Models for Real-World Optimization at Scale"**,
   arXiv:2610.18511 (2026). https://arxiv.org/abs/2610.18511 -- the organisers' task definition; cite as the challenge
   paper.
2. **Raftery, Li, Jin, Ting, Paliaga, Cheng, "Cost responsive supply air temperature reset strategy"**, CBE / UC Berkeley
   (2017). https://cbe.berkeley.edu/wp-content/uploads/2019/03/Raftery-CostResponsiveReset-May2017.pdf -- picks the SAT
   that minimises modelled fan + cooling + reheat cost; 17% HVAC savings in a six-month randomised field trial. Cite for
   "SADR's coldest-SAT rule is the cost-responsive optimum when COP is constant and fan power grows as P^1.5".
3. **Seem, House, Alcala, "Model selection for predicting the return time from night setback"**, 4th Int. High
   Performance Buildings Conf., Purdue (2016). https://docs.lib.purdue.edu/ihpbc/231 -- 57 recovery-time models compared;
   recommends two-parameter models on room temperature and smoothed demand, **without** outdoor air temperature. Cite
   next to round 6's recovery fit (no outdoor-temperature term needed).
4. **Oldewurtel, Parisio, Jones, Gyalistras, Gwerder, Stauch, Lehmann, Morari, "Use of model predictive control and
   weather forecasts for energy efficient building climate control"**, Energy and Buildings 45:15-27 (2012).
   https://doi.org/10.1016/j.enbuild.2011.09.022 -- the standard reference for MPC with weather forecasts; the
   January planner (item 4 of section 4) is this idea with a perfect forecast (the strip is replayed).
5. **Sturzenegger, Gyalistras, Morari, Smith, "Model Predictive Climate Control of a Swiss Office Building:
   Implementation, Results and Cost-Benefit Analysis"**, IEEE TCST 24(1):1-12 (2016). https://doi.org/10.1109/TCST.2015.2415411
   -- seven months of field MPC; good comfort; the cost of building the model, not the controller, is the barrier.
   Supports SADR's "transfer by construction" argument.
6. **Drgona et al., "All you need to know about model predictive control for buildings"**, Annual Reviews in Control 50
   (2020). https://doi.org/10.1016/j.arcontrol.2020.09.001 -- MPC workflow and model classes.
7. **Bunning et al., "Physics-informed linear regression is competitive with two Machine Learning methods in residential
   building MPC"**, Applied Energy 310 (2022). https://arxiv.org/abs/2110.15911 -- ARMAX models beat RF / ICNN for MPC;
   supports an online-fitted per-zone linear model.
8. **Afram & Janabi-Sharifi, "Theory and applications of HVAC control systems -- A review of model predictive control
   (MPC)"**, Building and Environment 72:343-355 (2014) -- broad MPC review. Journal, volume and pages confirmed from
   several citing references; the DOI was not confirmed, so look it up on ScienceDirect before citing.
9. **Blum, Arroyo, et al., "Building optimization testing framework (BOPTEST) for simulation-based benchmarking of control
   strategies in buildings"**, Journal of Building Performance Simulation 14(5):586-610 (2021).
   https://doi.org/10.1080/19401493.2021.1986574 -- the closest benchmark; contrast: BOPTEST fixes a few emulators,
   SB26 generates the building.
10. **Garmendia, Morri, Cappart, Le Cadre, "Winning the 2023 CityLearn Challenge"**, ECAI 2024.
    https://publications.polymtl.ca/59790/1/59790_Winning_2023.pdf -- winning entry of a comparable NeurIPS building
    competition was heuristic + classical control; most submissions overfit.
11. **Hansen, "The CMA Evolution Strategy: A Tutorial"**, arXiv:1604.00772 (2016). https://arxiv.org/abs/1604.00772 -- for
    the distribution-tuning item.
12. **NOAA NCEI Integrated Surface Database (ISD)**, hourly station observations.
    https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database -- free public weather for more
    cold stations (allowed: "free public external data"); the topic-752324 entrant used 2023 data from twelve airports.

