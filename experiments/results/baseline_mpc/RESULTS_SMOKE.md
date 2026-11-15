# MPC baseline: smoke results (dev window only)

Window: `heldout_scenarios_r10dev/building_train_8/denver_4`, the first 7 days (2016 five-minute steps), run locally on
the HP one process at a time with `experiments/src/run_scenario.py` (the same runner the Kaggle shards use).
This is a development scenario, not a public-30 or cold/hot evaluation scenario. Loss is |mean per-step reward|
(lower is better). The regret, energy and carbon columns are the episode totals of the normalized components.

| policy | loss / step | x v14 | x pid_water | comfort regret | energy | carbon | policy ms/step |
|---|---|---|---|---|---|---|---|
| v14 (`submission/candidates/transfer_policy_v14.py`) | 0.00324 | 1.0 | 0.13 | 0.47 | 14.0 | 17.2 | 0.9 |
| `pid_water` (kit) | 0.02408 | 7.4 | 1.0 | 70.5 | 15.0 | 16.3 | 0.2 |
| **MPC v2 = `mpc_rc.py` (frozen baseline)** | **0.05245** | **16.2** | **2.18** | 89.5 | 129.0 | 131.4 | 12.8 |
| MPC v0 (`mpc_rc_v0.py`, superseded) | 0.06355 | 19.6 | 2.64 | 190.0 | 36.1 | 34.5 | 4.2 |
| MPC v1 (`mpc_rc_v1.py`, superseded) | 0.08565 | 26.4 | 3.56 | 164.6 | 184.9 | 184.6 | 12.5 |

The file runs cleanly: every step's action is finite, and it costs about 13 ms per step, which adds about 2 minutes to an
8640-step episode. Summaries are in `smoke/<policy>/building_train_8/denver_4/*/summary.json`.

## What happened, in order

v0 followed PLAN.md as written. Its online model failed to identify. The fitted heating and cooling gains took both
signs, reaching magnitudes up to 70 times the prior, so the MPC treated several cold zones as unheatable and left them
about 5 K below the band in occupied hours. Amendment 1 added first-order filtered inputs, an AHU-on-while-idle
regressor and projected RLS. v1, the result, oscillated instead: its rollout assumed the AHU's run state lasts the whole
horizon, the idle coefficient sat at its bound, and the MPC heated zones that were already at 298 K at night.
Amendment 2 confined that term to the first block and set the box to the prior mean plus or minus 3 prior std. The
resulting v2 is frozen (sha256 `d5506221...`, also in `jobs/policy_sha256.txt`) and goes to the full runs whatever its
numbers. All three iterations used this single dev scenario. No evaluation set was run or read.

## Reading

The MPC is a weak baseline, and the reason is informative. Its comfort is close to `pid_water`'s (regret 89 against
70), but it spends 8.6 times the energy, for a loss 2.2 times `pid_water`'s and 16 times v14's on this window. It does
find the first design fact on its own: off-hours comfort costs nothing, so its AHUs run on only 18% of off-hours
steps, against 78% of comfort-hour steps. What it cannot do with a per-zone first-order model, a persistence forecast
and a fixed actuator map is price the plant. Its energy term is a guess per unit of command, so it cannot see that a
running AHU's fan and ventilation load cost far more than the zone's own command implies. Its fitted gains still sit at
the box edges for many zones. That is the gap SADR's closed-form heat-to-actuator translation closes. Seven days on one
mild-weather building is not evidence about the full sets; the full runs decide.

## Full runs (not started; the Kaggle slots are busy)

The job files are written and checked: `python experiments/src/baseline_mpc_launch.py check` gives 11 files with
30/40/40 jobs, no problems, and no names already in the queue or registry. The main session enqueues them with

    cd experiments/src && python baseline_mpc_launch.py enqueue

and, after the dispatcher has fetched them, `python baseline_mpc_launch.py table` writes `baseline_mpc/table.json`.
That table gives the MPC loss per set next to v14 (`round6/runs/struct_HA`) and `pid_water`, with paired bootstrap CIs.
