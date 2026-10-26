# SB26 improvement deep dive (round 6, 2026-10-26)

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

## 1. Where we stand

| | score | source |
|---|---|---|
| SADR v8 (round 5; best scored file) | 0.01074, rank 87 (86 teams ahead; 82 on 10-26 07:10 UTC) | `results/kaggle_feedback.json`, `round6/intel/lb_page1_2026-10-26T1905Z.csv` |
| SADR v9 (shipped in round 6) | probe 57678857 pending | `results/kaggle_feedback.json` |
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
| 1 | **Ship v9 (round-6 composite)** -- done | confirmed at full length: harsh confirmation set (48) -2.05% [-2.70, -1.43], public-30 -0.27% [-1.35, +0.65], M -1.28%; FD (large default-range buildings) +0.60% [-0.37, +1.36], n.s.; rule met; **shipped** (`submission/transfer_policy.py`); Kaggle probe 57678857 pending | about -1% (P part -0.3%, harsh part about -2.4%); not resolvable on the public LB | done | yes | yes |
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

