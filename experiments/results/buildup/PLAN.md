# Cumulative build-up: from the final controller back to a plain controller (DRAFT, not yet hashed)

Written 2026-11-14 for the final-round paper (Jan 15). It answers the prize-judge review's main point: the
leave-one-out ablation prices each mechanism only near the final design, so it cannot support "most of the margin
over pid_water comes from two design facts". A cumulative removal path can.

**Run only on the round-2 simulator** (the organizers' fixed kit, announced for after Nov 15; it clears the Kaggle
leaderboard). Hash this plan (`sha256sum PLAN.md > PLAN.sha256`) after the kit is installed and before any run.

## Arms (each removes a group on top of the previous arm; overrides in `params/`, applied to v14)

| arm | removes | overrides (cumulative) |
|---|---|---|
| B0 | nothing: the final controller v14 | none |
| B1 `bu1_no_refinements` | everything added after area scaling: set-back air boost and reheat, night flush, error-proportional occupied flow, weekend setback, model-based starts, heating season, 20 kW cap (back to 12), cooling handover ramp | round-11 ablation overrides noboost, noneutral, noflush, nooccdyn, noweekend, nomodel, noseason, qcap12, plus `st_hand_c_h` 0 |
| B2 `bu2_no_building_awareness` | gains scaled with zone area, coil-delivery cap, per-zone optimum start, recoverable floor | + noarea, nowcap, nozone, nofloor |
| B3 `bu3_no_coldest_air` | design fact 3: coldest supply air at the lowest flow (upward reset, ceiling 293 K, as ablation arm sat293) | + sat293 |
| B4 `bu4_no_idling` | design fact 1: comfort is free while empty (lead fixed at 24 h, so the plant always preconditions; no setback widening) | + lead 24 h, night_low_ext = night_high_ext = 0 |
| P | `pid_water` | organizers' baseline, same kit |

Design fact 2 (heat only through reheat at a closed-form price) has no clean switch; it is embodied in the net-heat
loops and the discharge-limited flow and stays in every arm. Say so in the paper.

## Sets and statistics
- Public 30 (8,640 steps) for every arm; cold set (HC3, 40) and hot set (HH, 40) for B0, B3, B4 and P if compute allows.
- Report each arm's loss, the step from the previous arm with a paired bootstrap 95% CI over scenarios (2,000 resamples,
  seed 20261115) and the cluster (building) CI, plus the comfort / energy / carbon split.
- The share of the P-to-B0 gap closed at each step is the headline; it is descriptive, there is no ship rule.

## Checks before the full run
1. B0 on the round-2 kit reproduces the Kaggle notebook's local total on atlanta_2 (as kaggle_probe_r14b `check`).
2. B4 smoke test (one Fairbanks and one Phoenix scenario, 7 days): the AHU-on share on unoccupied steps must rise to near
   the occupied level, otherwise the 24 h lead does not disable idling and B4 needs a code switch instead.
3. Every arm with all overrides parsed: `transfer_policy_v14.py` must know each key (unknown keys are silently ignored).

## Compute
About 5 arms x 30 scenarios + extras: about 15-25 Kaggle shards of 10 runs (5 slots, `kaggle_sim.py`), or the Lenovo
(`ssh lenovo`, take `work\LOCK` first). The Mac is the user's work machine again; do not use it without asking.
