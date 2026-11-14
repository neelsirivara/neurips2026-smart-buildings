# struct_r1 finalist confirmation (pre-registration draft; NOT run in struct_r1)

Written 2026-11-09 after the struct_r1 screen and before any confirmation-set run of the finalist. To be hashed
(sha256) by whoever launches it, before the first run.

## Candidate
- `HA` = v13 + `st_hand_c_h = 1.0` (all other struct switches off), on
  `experiments/src/policies_struct/sadr_struct.py` (sha256 recorded in identity_check.json), params
  `results/struct_r1/params/HA.json`. All off = v13 bit for bit (identity_check.json).
- Comparator: v13 (`submission/candidates/transfer_policy_v13.py`) = r12var, whose full-length HC3 / HH / pub30 runs
  exist (round12/decision_r12var.json). Using those is allowed only if a fresh v13 run on 2 scenarios per set matches
  them to within a relative 1e-9; otherwise v13 is re-run on all three sets.

## Runs
Full length (8,640 steps): HC3 (r10hc, 40), HH (r10hh, 40), public 30. None of these was used in struct_r1.

## Decision rule (fixed now)
- Primary: mixture = 1/3 mean(HC3 ratio) + 2/3 mean(HH ratio) - 1, ratio = HA / v13 per scenario; 95% paired
  bootstrap CI (2,000 resamples, seed 20261107) must lie entirely below 0.
- Guard 1: public-30 mean ratio <= 1.000.
- Guard 2 (frost, vs v13, from struct_r1's full-length HS-18 runs): below-5 C share <= v13 + 0.25 pp and coldest
  zone >= v13 - 1.0 K.
- Guard 3 (comfort is where the change acts): HH comfort regret per step must not rise vs v13.
- All pass -> HA is a ship candidate (a v14 candidate file + private Kaggle probe, as for v13). Otherwise v13 stays.
- Reported regardless: per-set means and wins, comfort / energy / carbon split, and HC3 / HH separately.
- If round 14 ships first (r14cand -> v14), the same rule is applied with v14 as the comparator and HA's switch on
  top of v14 (bit-identity of the switch-off code against v14 checked first).

## Expectation (for calibration, not a criterion)
The screen gave public-like -1.09% (12/12) and harsh -0.03%, so about -0.7% on the 1/3-2/3 mixture. HH (hot strips)
should carry most of the effect; on HC3 (cold) it should be near zero.
