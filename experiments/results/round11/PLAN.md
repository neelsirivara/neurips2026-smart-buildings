# Round 11 (2026-11-05): ablation of the shipped v12, for the poster paper

Written 2026-11-05 ~08:05 UTC, before any run of this round. This is a description of the shipped policy, not a
selection: nothing ships from it, and every arm is reported, whatever its sign. It answers review points P4, P6 and
P7 (`paper/review/REVIEW_2026-11-05.md`): what each mechanism of v12 is worth, v12 against `pid_water` with a
confidence interval, v12's loss by hour of day, v12's coldest zone and the cost of a 5 °C frost floor.

Policy: the shipped `submission/transfer_policy.py` (md5 57bc72cb..., defaults = `results/tune/best_params_v12.json`),
each arm = one parameter override file (`round11/params/<arm>.json`), 8,640 steps, private Kaggle CPU kernels
(`kaggle_sim.py`, dataset neelsiri/sb26-sim-r6, 4 workers per kernel, at most 5 kernels). The Mac is not used:
the speech session holds its GPU lock, and simulator workers do not run beside a GPU job.

| Arm | Override | What it removes or changes (version that added it) |
|---|---|---|
| ab12_ref | none (time series saved) | the shipped v12 |
| ab12_noarea | gain_area_scaling 0 | zone gains scaled with zone area (v6) |
| ab12_nozone | per_zone_start 0 | each zone learns its own recovery rate and lead (v6) |
| ab12_nofloor | adaptive_floor 0 | setback floor limited to what the zone can recover (v6) |
| ab12_nowcap | water_cap 0 | heating requests capped at what the coil can deliver (v6) |
| ab12_noecon | econ_on 0 | economizer |
| ab12_sat293 | sat_cool_hi 293 | v4's upward supply-air reset instead of the coldest supply (v5) |
| ab12_tw330 | tw_hot_k 330 | hot water at 330 K instead of 350 K in heating season |
| ab12_nooccdyn | occ_press_dyn 0 | occupied flow above the floor only in proportion to the error (v7) |
| ab12_noflush | flush_on 0 | night flush (v7) |
| ab12_noneutral | sb_neutral 0 | set-back zones' forced air reheated to zone temperature in heating season (v7) |
| ab12_noweekend | wk_ext_lo 0, wk_ext_hi 0 | the deeper weekend setback (v8; deepened in v12) |
| ab12_qcap12 | q_cap_w 12000 | v7's request cap (12 instead of 20 kW per 100 m2, v8) |
| ab12_noboost | sb_boost 0, sb_boost_floor_k 0 | set-back air boost before workdays and near the floor (v9) |
| ab12_nomodel | mbr_on 0, mpr_on 0 | model-based starts (v10 first order, v12 second order) |
| ab12_nodow | dow_snap 0 | the day-of-week rounding fix (v11): Saturday decodes as a workday again |
| ab12_noseason | season_ext_steps 0 | the 7-day heating season gated at 15 °C (v12) |

Sets: the 30 public scenarios for every arm. On HS (18 harsh scenarios, `heldout_scenarios_r6hs`): `ab12_ref` with
time series (coldest zone temperature) and `ab12_frost5` (frost_floor_k 278.15).

Reporting (fixed now): per arm, the public-30 mean loss, the change against `ab12_ref` with a paired bootstrap 95% CI
over scenarios (5,000 resamples, seed 0) and over buildings (cluster bootstrap), wins / 30, and the change in each
loss term (comfort, energy, carbon). `ab12_ref` must equal round 10's v12 runs (`round6/runs/r10_K/pub30`) to the
printed digits; otherwise the platform difference is reported and the table uses `ab12_ref` only.
