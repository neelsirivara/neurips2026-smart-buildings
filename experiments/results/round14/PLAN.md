# Round 14: CMA-ES over all 14 constants with frost protection ON (pre-registration)

Written 2026-11-09 by the orchestrator session (user: "keep iterating ... use aggressive exploration where needed"),
before any round-14 run. A one-window smoke test (v13 with and without the floor, HS building_train_1/fairbanks_2,
7 days, Lenovo) was run only to check that the switch works; it is not used for any decision.

## Why
Rounds 12 and 13 showed that black-box tuning against this reward reaches for frost exposure (deeper setbacks in
round 12; less setback boost heat and a shorter lead in round 13), because the simulator charges nothing for cold
zones. Instead of guarding against it after the fact, round 14 turns on SADR's existing frost protection
(`frost_floor_k`: the setback floor never goes below this absolute temperature) at 278.15 K (5 C), fixed and not
tuned, and then lets the tuner search all 14 constants again, setback depths included (round 12's bounds).

## Search (`experiments/src/cma_r14.py`, derived from cma_r12.py)
- Fixed: frost_floor_k = 278.15 K. Same policy file (round12/policies/v12.py, sha256 44ebbb3b...).
- Tuned: round 12's 14 parameters and bounds. Start: r12cand (round12/candidate_mean.json). Fresh covariance,
  sigma0 = 0.15. Population 10, 5 parents, 15 generations or sigma < 0.02. Seed 20261109.
- Objective: identical to rounds 12-13 (24 seven-day windows, 1/3 harsh + 2/3 public-like ratio to v12, r12ref).
- Compute: Kaggle (5 slots) + Mac (5 of 10 per generation, same gating; HOLD at ~/neurips/sb/r14/HOLD).

## Confirmation and ship rule (fixed now)
- Candidate r14cand = CMA mean after the last generation (with frost_floor_k 278.15).
- Full length on HC3 40, HH 40, public 30 and HS 18 (time series).
- The bar is v13 (= r12var, whose full-length runs exist): Primary = mixture 1/3 HC3 + 2/3 HH of the per-scenario
  ratio r14cand / r12var, minus 1; its 95% paired bootstrap CI (2,000 resamples, seed 20261107) must lie below 0.
- Guard 1: public-30 mean ratio r14cand / r12var <= 1.000.
- Guard 2 (frost, vs v12 as in round 13): HS below-5 C share <= v12 + 0.25 pp and HS coldest >= v12 - 1.0 C.
- If all pass: r14cand becomes v14 (candidate file + private Kaggle probe, as for v13). Otherwise v13 stays.
- Reported regardless: the same numbers against v12, per-set wins, frost figures, and the parameter moves.
