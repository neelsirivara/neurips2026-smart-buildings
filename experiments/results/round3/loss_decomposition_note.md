# Round 3, goal 1: where the remaining loss of SADR v5 sits

Source: `experiments/src/run_diag.py` (the kit's evaluation loop with the plant energy rates read
from the `RewardInfo` every step), `decompose_loss.py` (split of the per-step loss into comfort,
fan, cooling, pump and gas; electricity $ and kg shared between the three electric loads in
proportion to their W; gas kg at the kit's 53.12 kg/MMBtu), all at 8,640 steps on the Mac.
Files: `loss_decomposition_public_v5.json` (30 public scenarios), `loss_decomposition_heldout_v5.json`
(10 scenarios of buildings 0501/0502), `loss_decomposition_heldout_r3_v5.json` (30 scenarios of the
six new buildings), and the same three for the round-3 policy (`*_v6.json`). Units: leaderboard
metric (loss per step, mean over scenarios); shares are of the metric.

## Public set (v5, 0.00831)

| component | loss/step | share |
|---|---|---|
| comfort (0.6 x regret) | 0.00036 | 4.3% |
| fan (supply + exhaust) | 0.00038 | 4.6% |
| cooling (chiller, COP 3.5) | 0.00320 | 38.5% |
| pump | 0.00001 | 0.2% |
| gas (boiler) | 0.00436 | 52.4% |

- By station: Fairbanks 0.01752 (gas 90%), Denver 0.00497 (gas 57%, cooling 29%), Atlanta 0.00549
  (gas 46%, cooling 45%), Phoenix 0.00755 (cooling 83%), Singapore 0.00602 (cooling 91%).
- By mode: occupied 70.1%, preconditioning 24.5%, setback 5.3% of the loss; unoccupied steps carry
  30% (preconditioning + setback), almost all of it gas in the cold stations.
- By hour: hours 4-7 carry the morning recovery (hour 5 peaks at 0.0010/step vs 0.0004 in the
  afternoon); in Fairbanks the hour-5 spend is four times the afternoon's.
- Ventilation: while gas burns, 27% of the supply air goes to zones at their damper floor
  (Denver 40%, Atlanta 33%, Fairbanks 32%): the forced minimum flow of idle zones on a running
  handler, each carrying 30% outside air that the reheat must warm. This is the mandatory
  ventilation of the simulator, not a controller choice, except through the handlers' run time.
- Comfort: 3.0% of occupied zone-steps out of band; the largest quartile of zones (by floor area)
  is inside the band 0.10 h after 06:00 on average, the rest 0.02 h. Nothing is late on the
  public buildings (zone areas 24-362 m2, median 99 m2).
- What is physics and what is control: heating with 30% outside air at the discharge cap costs
  1 + 0.3 (T_zone - T_out)/(T_disch - T_zone) J of gas per J of net heat (about 2 at -20 C); cooling
  at the coldest supply costs (T_mixed - 285)/(T_zone - 285)/COP J of electricity per J of zone
  cooling. Both are minimized by the v5 rules (minimum flow at the discharge cap, coldest supply,
  recirculation at the cap, floor pressure), so the remaining spend on the public set is the
  envelope and ventilation load at the band edge. The 30% the Kaggle leaders have over our public
  number is not visible on the public buildings; the generated large buildings are where our
  controller lost, see below.

## Previous held-out set (v5, 0.01109; building 0501 0.00443, building 0502 0.01774)

| component | share, 0501 | share, 0502 |
|---|---|---|
| comfort | 16% | 16% |
| fan | 6% | 4% |
| cooling | 54% | 25% |
| gas | 25% | 55% |

- Comfort is four times its public share; on building 0502, 11.7% of occupied zone-steps are out of
  band and the largest quartile of zones reaches the band 0.67 h after 06:00 on average (public:
  0.10 h); in the Denver and Fairbanks strips the two 356 and 429 m2 zones sit 2-4 K below the band
  until noon and the loss by mode is 0.0113 occupied, 0.0057 preconditioning (public: 0.0058, 0.0020).
- Diagnosis (trace of the controller's state on building_0502/denver_1): every VAV box has the same
  2 m3/s design flow and hot-water Kv, so a 430 m2 zone has a fifth of the heating authority per
  square metre of a 100 m2 zone and several times the thermal mass (the walls carry 10-20x the air's
  heat capacity and lag it by hours). v5's fixed 12 kW request cap, fixed gains (400 W/K, 120 W/K
  per step) and one building-wide optimum-start lead were tuned on 100 m2 zones: the big zones
  recovered at under 1 K/h, the lead saturated at 8 h, and the handlers ran all night at 12 kW per
  zone. The round-3 controller (v6) scales gains, caps and the setback burst with the zone's floor
  area (read from the metadata zone map), bounds a request by what the box can physically deliver
  (discharge limit, water-side limit with the valve fully open at 20 bar), learns a recovery rate
  per zone and raises the setback floor of zones that cannot recover within the maximum lead.
  Ten-day test on building_0502/denver_1: 0.02831 (v5) -> 0.02376 (v6), regret -16.95 -> -1.28,
  gas 2046 -> 1882 kWh/day, fan 34 -> 62 kWh/day.

## New held-out set (six generated buildings, 30 scenarios)

Buildings 0500, 0505, 0507, 0508, 0509, 0511 (generator seeds; 32-120 zones, 5-12 handlers,
zone areas 33-1373 m2, median 246 m2). v5 = `diag_v5_r3`, v6 = the shipped round-3 policy
(`r3_c16_pre035_min1`, `final_v6_r3`), both 8,640 steps on the Mac.

| component | v5 loss/step | v5 share | v6 loss/step | v6 share |
|---|---|---|---|---|
| comfort | 0.00208 | 14.2% | 0.00039 | 3.0% |
| fan | 0.00095 | 6.5% | 0.00121 | 9.3% |
| cooling | 0.00707 | 48.5% | 0.00709 | 54.8% |
| pump | 0.00002 | 0.1% | 0.00003 | 0.3% |
| gas | 0.00447 | 30.6% | 0.00423 | 32.7% |
| total | 0.01458 | | 0.01294 | |

- v6 removes most of the comfort loss: occupied zone-steps out of band 14.0% -> 2.1%; the largest
  quartile of zones is in band 0.65 h after 06:00 for v5 and 0.12 h for v6 (building 0509: 1.30 h
  -> 0.09 h). It pays for it with fan energy (+0.00026/step: more flow while recovering and while
  occupied at full design flow) and saves gas (-0.00024/step) and preconditioning loss overall
  (by mode: preconditioning 0.00326 -> 0.00226, occupied 0.01096 -> 0.01023, setback 0.00037 ->
  0.00046 per step).
- Previous held-out set (0501, 0502): comfort share 15.9% -> 4.5%, out-of-band 9.7% -> 2.9%,
  largest-quartile recovery 0.41 h -> 0.12 h; metric 0.01109 -> 0.00944.
- Public set: comfort 0.00036 -> 0.00018 per step, gas 0.00436 -> 0.00425; metric 0.00831 -> 0.00803.
- What is left on the generated buildings is cooling electricity: 0.00709 per step against 0.00318
  on the public set; the costliest cooling-climate scenarios are building_0507/phoenix_4 (0.0316),
  building_0507/singapore_6 (0.0221) and building_0509/phoenix_5 (0.0187)
  (`heldout_r3_scores.json`). Not diagnosed this round; hypothesis: a larger cooling load per unit
  of the plant normalizer in those buildings, since the cold-supply / minimum-flow rules already
  apply there. Candidate levers for January: envelope pre-cooling and the setback depth in cooling
  climates.
