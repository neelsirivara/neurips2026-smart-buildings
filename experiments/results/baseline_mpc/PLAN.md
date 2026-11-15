# Non-rule baseline for the final-round paper: online-identified RC model + enumerated MPC

Written 2026-11-14, before any baseline run. The prize-judge review asked for "one learned or MPC baseline (even weak)".
This file fixes the design, the data it may see and how it will be reported, so that the numbers cannot have
shaped the design.

## Choice: option (a), short-horizon MPC on an online-identified RC model

We build a model-predictive controller rather than a learned policy, for three reasons. First, an MPC is the
baseline a building-controls reader expects next to a rule-based controller, and it answers the reviewer's real
question, which is whether SADR's margin over `pid_water` is something a generic optimiser would also find once it
is given the reward. Second, it needs no training data at all: the thermal model is fitted inside each episode from
the observations the policy has already seen, so there is no question of which scenarios it was trained on, and
the same file runs unchanged on any building. Third, a learned policy (CEM or behaviour cloning) over a
building-dependent action vector of 20 to 100 continuous slots would need either a hand-made low-dimensional
parameterisation (which makes it a tuned rule controller under another name) or far more simulation than the
laptop budget allows; a weak learned policy would be weak for reasons unrelated to the question.

## The controller (`experiments/src/policies_baseline/mpc_rc.py`, class `TransferPolicy`)

Model. Each zone z has a first-order discrete-time thermal model, one 5-minute step ahead,

    T[t+1] - T[t] = th0 + th1 (T_oa - T[t]) + th2 h[t] + th3 c[t] + th4 occ[t]

with h, c in [0, 1] the zone's commanded heating and cooling levels, T_oa the outside air temperature of the zone's
AHU and occ the schedule's comfort-hours flag (internal gains). The parameters are fitted online by recursive least
squares with forgetting factor 0.999 (memory about 3.5 days), from a weak physical prior (no heat gain from h or c
is assumed larger than about 0.6 K/h at full actuation; the envelope time constant prior is about 40 h). Signs are
constrained at planning time (th2 >= 0.002, th3 <= -0.002, th1 >= 0). Nothing is fitted before the episode starts
and nothing is carried between episodes.

Planning. Every step, each zone independently enumerates move-blocked input sequences over a 6-hour horizon
(three blocks of 0.5 h, 1.5 h and 4 h, five levels u in {-1, -0.5, 0, 0.5, 1} per block, 125 sequences; u > 0 is
heating, u < 0 cooling), predicts its temperature with the persistence forecast T_oa = current value, and applies
the first block of the cheapest sequence (receding horizon). The cost mirrors the reward:

- comfort, 0.6 x the kit's productivity shape (dev/5 up to 5 K, 1 + ((dev - 5)/5)^2 beyond) against the comfort
  band 294-297 K on predicted comfort-hour steps (weekday, between the metadata's morning and evening start hours)
  and zero otherwise, because the reward's comfort term is zero when nobody is in;
- energy, 0.4 x e x |u| per step with e = 0.5 for both heating and cooling: a single first-principles guess that
  a zone at full actuation spends about half its share of the plant maximum. It is not tuned;
- a frost/overheat guard that the reward does not contain: 0.06 x the same shape against the out-of-hours band
  289-298 K when the building is predicted empty, so the MPC does not let empty buildings freeze (the frost hazard
  in the paper's tuning section).

Actuators (fixed textbook mapping, not optimised). Cooling level c: damper 0.1 + 0.9c, valve shut. Heating level h:
damper 0.15 + 0.35h, valve 0.3 + 0.7h. An AHU runs iff one of its zones has |u| > 0; its SAT is the conventional
55 F design value (285.9 K) if any of its zones cools, else 305 K (coil idle); static pressure 300 + 1200 x max|u|
Pa; a dry-bulb differential economizer (outside-air fraction solved for mixed air at the SAT target when cooling and
outside air is at least 1 K colder than return, else the 0.7 recirculation cap). Hot water: pump on iff any zone
heats, supply 310 + 40 x max h K, differential pressure 4 + 16 x max h. Day of week is decoded by rounding (the
feature is weekday/7 sent as float32, per the kit's `conversion_utils.get_radian_time`).

What it deliberately does not have: SADR's net-heat loops, area scaling, optimum-start statistics, setback bursts,
the coldest-supply-air argument, set-back air reheat, holiday detection or the cooling handover ramp. Idling when
empty and pre-heating before occupancy are not coded; if they appear, the MPC found them from the reward.

## Data hygiene

- No pretraining. No constant is fitted to any scenario; the five constants above (e, guard weight, horizon blocks,
  levels, forgetting) are set here, before any run, and stay fixed for every reported number.
- The smoke test uses a development scenario (`heldout_scenarios_r10dev/building_train_8/denver_4`, 7 days =
  2016 steps), not a public-30 or cold/hot evaluation scenario. It checks that the file runs, is finite and is
  not absurd; it is not used to choose constants. If the smoke run is pathological (crash, NaN, loss more than
  10x `pid_water`), the only permitted fix is a bug fix, documented in RESULTS_SMOKE.md.
- No gas-billing quirk, no occupancy-seed replay, no reading of evaluation outcomes. The policy sees only the
  observation vector and the metadata, like every submission.

## Full runs (enqueued later by the main session; Kaggle private kernels)

`python experiments/src/baseline_mpc_launch.py make` writes job files for pub30 (30), r10hc (40) and r10hh (40) at
full length (8640 steps), variant tag `mpc_rc`, into `experiments/results/baseline_mpc/jobs/`. `enqueue` hands them
to `kaggle_sim.py enqueue`; `table` reports the MPC's loss per set next to v14 (`round6/runs/struct_HA`) and
`pid_water`, with paired bootstrap ratio CIs (2000 resamples over scenarios, seed 20261116).

## Reporting rule (fixed now)

Whatever the full-length numbers are, they are reported as they come out: loss per set, ratio to v14 and to
`pid_water` with paired 95% CIs, and the comfort/energy split. If the MPC loses to `pid_water`, the paper says so
and reports it as a weak generic baseline; if it beats SADR somewhere, that is reported too. No second version is
run against the evaluation sets after seeing the first one's results; any later MPC variant would be screened on
r10dev only and labelled as post hoc.

## Amendment 1 (2026-11-14, after the first dev smoke run, before any evaluation-set run)

The first smoke run (v0, dev window only) ran cleanly but its online model failed to identify: across zones the
fitted heating coefficient ranged from -0.51 to +1.46 K/step and the cooling coefficient from -1.44 to +3.44 K/step
(the prior is +/-0.05), so several cold zones were judged unheatable and left 5 K below the band in occupied hours.
Two structural causes, both visible in the regressors rather than in the score: (1) the plant answers a command with a
lag (the AHU starts on cold mixed air, the hot-water loop has to warm up), so a step input first moves the zone the
wrong way; (2) a zone on a running AHU receives floor ventilation air even when its own command is zero, which the
model attributed to the other regressors. The fix, fixed now and applied once:

- the model's heating and cooling inputs are first-order filtered commands (h_f <- h_f + 0.3 (h - h_f)), in both the
  RLS regression and the MPC rollout;
- a sixth regressor: the zone's AHU is running while the zone itself is idle (prior mean 0, std 0.03); the rollout
  assumes the AHU's last run state persists for idle steps;
- projected RLS: after every update the parameters are clipped to a physical box (th0 in [-0.1, 0.1], th1 in
  [0, 0.02], th2 in [0.002, 0.4], th3 in [-0.4, -0.002], th4 in [-0.05, 0.1], th5 in [-0.3, 0.3] K/step).

No cost constant, horizon, level grid or actuator mapping changes. The amended file (v1) is the baseline; it is run
once on the same dev window and then goes to the full runs whatever its smoke number. v0's smoke number stays in
RESULTS_SMOKE.md. No further revision is made on the dev window except for crashes.

## Amendment 2 (2026-11-14, after the v1 dev smoke run, before any evaluation-set run); final, the file is frozen after it

v1 (dev window) cut comfort regret by 13% but raised energy 5x. Diagnosis from the fitted parameters, not the score:
the rollout assumed the AHU's current run state persists for the whole 6 h horizon, and the idle-on coefficient sat
at its box edge (-0.3 K/step, confounded with the constant), so the MPC predicted idle zones would crash and heated
zones that were already at 298 K at night. The v1 box (Amendment 1) was also wider than the prior justifies. Two
changes, and nothing else:

- the idle-on term enters the rollout only in the first block (0.5 h), the only span over which the AHU's state is known;
- the projection box becomes one rule: prior mean +/- 3 prior std (th0 [-0.06, 0.06], th1 [0, 0.008], th2 [0.002, 0.2],
  th3 [-0.2, -0.002], th4 [-0.028, 0.032], th5 [-0.09, 0.09] K/step).

This v2 is the baseline for the full runs regardless of its smoke number. v0 and v1 smoke numbers are reported in
RESULTS_SMOKE.md. Three dev-window iterations happened in total, all on the single dev scenario; no evaluation set
was touched, and the paper should say so.
