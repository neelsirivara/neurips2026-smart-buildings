# Round 13: CMA-ES re-tune with v12's setback depths fixed (pre-registration)

Written 2026-11-08 ~08:20 UTC by the orchestrator session (user: "go auton; use the compute we have well"), before
any round-13 run and before the r12var confirmation was complete (interim r12var: mixture -0.39% [-0.68, -0.12] on
HH 40 + HC3 20 of 40, pub30 -2.5%, HS coldest -10.0 C, below-5 C share 4.24% = v12).

## Why
Round 12's tuned mean (r12cand) passed (mixture -0.74%) but bought part of its gain with deeper night setbacks
(HS coldest -11.4 C vs -9.4 C; below-5 C 4.9% vs 4.2%). The simulator has no frost cost, so that part leans on a
simulator gap. r12var restores the two depths and keeps the other 12 tuned constants, which were tuned jointly with
the deeper depths. Round 13 re-tunes those 12 with the depths fixed at v12's values.

## Search (same machinery as round 12, `experiments/src/cma_r13.py`)
- Fixed: night_low_ext = 10.0, night_high_ext = 6.0 (v12). The other 12 parameters, bounds and scales are round 12's.
- Start: r12var (`round12/candidate_v12setback.json`). Fresh covariance, sigma0 = 0.15 (round 12 ended at 0.099).
- Population 10, 5 parents, 12 generations or sigma < 0.02, seed 20261108.
- Objective: identical to round 12 (same 24 seven-day windows, 1/3 harsh + 2/3 public-like ratio to v12), reusing
  round 12's v12 reference windows (r12ref; same policy file, same scenarios, bit-reproducible simulator).
- Compute: Kaggle (dispatcher, 5 slots) + Mac (5 of 10 candidates per generation under the weekend-board rules:
  GPU lock free, >= 50% free memory, no ALERT, no HOLD at ~/neurips/sb/r12/HOLD or ~/neurips/sb/r13/HOLD).

## Confirmation and ship rule (fixed now)
- Candidate r13cand = the CMA mean after the last generation.
- Full length (8,640 steps) on HC3 40, HH 40, public 30 and HS 18 (with time series), vs v12 (r10_K; HS vs ab12_ref).
- Primary: round 12's mixture rule (95% paired bootstrap CI of 1/3 HC3 + 2/3 HH ratio - 1 entirely below 0).
- Guard 1: public-30 mean ratio <= 1.000.
- Guard 2 (frost, new): HS share of zone-steps below 5 C <= v12's + 0.25 percentage points, AND HS coldest zone
  >= v12's - 1.0 C.
- Choice of what ships as v13 (applied mechanically): among {r12var, r13cand} the candidates passing Primary, Guard 1
  and Guard 2; if both pass, the one with the lower mixture point estimate; if neither, v12 stays. r12cand (the deep
  setback) is not eligible under Guard 2 and is reported in the paper as a sensitivity result.
- Reported, not part of the rule: per-set wins, cluster bootstrap, comfort/energy/carbon terms.
- Shipping = candidate policy files + a private Kaggle probe (reversible). Final Kaggle selections stay the user's.
