# Round 4 diagnosis of the shipped SADR v6 (leads 2 and 3)

Sources: the round-3 full-length diagnostic runs of v6 on the Mac (`results/mac/round3/final_v6_{public,heldout,r3}`,
8,640 steps, diag.csv + zones.npz), processed by `experiments/src/diag_cooling_r4.py` (chiller-load
reconstruction from the logged handler states; it matches the logged chiller power within 0.1% on the
cooling scenarios) and `experiments/src/diag_round4.py` (fan regimes, ventilation share of gas, idle-zone
cooling, aggregation). Numbers: `diag_cooling_v6.json`, `diag_round4.json`; generator comparison:
`generator_ranges.json`. Loss shares are of the leaderboard metric.

## 1. Chiller electricity on the generated buildings is a normalization effect, not a control defect

| set (Phoenix + Singapore strips) | chiller W per m2 of zone | chiller / (80 kW x handlers) | m2 of zone per handler |
|---|---|---|---|
| public (12 scenarios) | 2.31 (0.34-4.20) | 0.032 | 1,088 |
| held-out 0501/0502 (4) | 1.81 | 0.030 | 1,367 |
| round-3 buildings (12) | 2.05 (1.02-3.25) | 0.067 | 2,643 |

Per square metre the generated buildings cool no more than the public ones (often less), but the energy
normalizer is 80 kW (electricity) per handler and a handler serves at most ten zones, so a building with
2.4x the floor area per handler pays 2.1x the chiller loss for the same physics. building_0507/phoenix_4
(the costliest cooling scenario, 0.0316) cools at 2.59 W/m2 against 4.20 W/m2 on building_train_1/phoenix_5.

Other checks on the hot strips (shares of the reconstructed coil load): the economiser is active on 5-9% of
it (outside air is hotter than return air almost always); reheat-while-cooling and missed economiser are
1.5-2.4% of the cooling-weighted coil load (mostly on mild-climate mixed handlers where the coil is nearly
idle); preconditioning carries 9-11% and setback 0-2%; the hourly profile is flat through comfort hours
(internal gains, people, envelope, 30% outside air); there is no latent load in the simulator. Night
outside air is >= 3 K below the zones on 12-26% of unoccupied steps in the hot strips (almost none in
Phoenix/Singapore summers) but on 42-59% (mean dT 5-7 K) in the Denver/Atlanta strips that cool.

## 2. Where the controllable part is: fan power above the pressure floor

Fan power above the 200 Pa floor (with the exhaust fan) costs 0.000467 per step on the round-3 buildings
(3.6% of their 0.01294; 39% of their fan term), 0.000111 on 0501/0502 and 0.000018 on the public set.
46% of it (0.000214) is on handlers that heat and cool at once, whose supply air v6 floors at 292 K: their
large cooling zones then need full design flow and push the handler to 1,000-2,000 Pa; 41% (0.000192) is on
cooling handlers already at 285 K whose largest zones (600-1,400 m2) are at full damper. Pressure above
the floor also raises every other zone's forced minimum flow (damper floor x sqrt(P/2000)). The comfort
term is charged per occupant and generated zones carry 1-2 occupants whatever their area, so holding a
1,000 m2 zone at the band edge with a 2,000 Pa handler costs more than letting it drift a fraction of a
kelvin. Candidates r4_c06 (mixed-handler supply relief) and r4_c07/c08 (pressure-aware occupied cap).

## 3. Fairbanks gas

In the three public Fairbanks strips with mean outside air below 0 C (train_1/fairbanks_1, train_2/fairbanks_2,
train_8/fairbanks_8), the outside-air heat of running handlers equals 54% (47-63%) of the boiler gas
(round-3 cold strips: 68%); preconditioning carries 30% of the gas and setback 11%. The heat the forced
minimum flow of idle zones removes from them while set back or preconditioning is 5.1% (3.2-8.0%) of the gas;
it is recovered later through the ventilated reheat at ~1.9 J of gas per J (candidate r4_c10 reheats it
now, at 1 J/J). The ventilation factor of reheat at the discharge cap, 1 + 0.3 (T - T_out)/(T_disch - T),
does not depend on the flow, so lowering the preconditioning flow cap below the floor-pressure flow
(c02-c04) only slows the recovery; a hotter assumed discharge (c05) lowers the factor directly.

## 4. The generator's default ranges do not produce buildings like the shipped six

`run_floor_generator.py` DEFAULT_RANGES (width 400-700, height 300-500, rooms 30-60) reproduce none of the
six shipped buildings from their own seeds (seed 0: 597 x 494 ft vs building_train_1, 373 x 188 ft); the
shipped six span width 318-430, height 188-301, rooms 25-51. The kit README says the Kaggle evaluation
buildings come from "the same generator and parameter ranges as the shipped six", so the round-3 held-out
buildings (default ranges, median zone 246 m2) are larger than the likely test buildings. Round 4 therefore
generates both families (PREREG.md) and reports the shipped-range buildings separately.
