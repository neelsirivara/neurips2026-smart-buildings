# struct_r1: structural controller changes on top of v13 (pre-registration)

Written 2026-11-09 by a subagent of the orchestrator, before any screen run of any idea. Separate from round 14
(constant tuning, running elsewhere); nothing in round12..round14, submission/ or best_params.json is touched.

## What was run before this plan (not used to rank ideas)
- v13 reference on the 24 screen windows (`v13ref`, submission/candidates/transfer_policy_v13.py, sha256 4cf9e40b...),
  with time series and the policy's debug log. Its diagnostics (`diag_v13ref.json`, hour-by-hour loss shares) chose
  which mechanisms to target: on the 12 HS windows 05:00-07:00 on workdays is 28% of the loss and at 06:00 several
  zones per building are still 1-5 K below 294 K (comfort 06:00-06:15 = 0.47% of the HS loss); on the 12 public-like
  windows comfort at 06:00-06:30 is 1.1% of the loss (zones overshoot 297 K by 06:15 after the cooling target steps up
  0.54 K at the handover), and the three Denver-May windows spend 25-31% of their loss before 06:00 heating zones that
  are cooled again later the same day while handlers serve heating and cooling zones at once.
- A bit-identity check (all switches off vs v13, one window) and a 3-day crash smoke test of all switches on one
  public-like window (not scored, not used for any decision).

## Policy
`experiments/src/policies_struct/sadr_struct.py` = v13 + four switches, all off by default (off = v13 bit for bit).

## Ideas (mechanism; loss term and hours targeted; arms fixed now)
1. **st_late: late-recovery escalation.** Within 2 h of the workday start, a preconditioning zone whose rise rate over
   the last (up to) 30 min, extrapolated to 06:00, will not close its gap (> 0.3 K) requests its full heat at a higher
   flow-fraction cap (latched until it reaches the target). v13 lets such zones draw that flow only from 06:00 (the
   occupied cap), so they start the workday below the band. Target: comfort regret 06:00-07:00 on cold days (HS),
   at the price of fan energy and earlier heat 04:00-06:00. Arms: L-A cap 1.0 (= the occupied rule's maximum);
   L-B cap 0.6.
2. **st_hand_c_h: cooling handover ramp.** The occupied cooling target starts at the preconditioning cooling target
   (comfort_hi - margin_pre) at a zone's first occupied step and relaxes linearly to the occupied target
   (hi_s - margin_occ) over the ramp time, so cooling does not stop at 06:00 while the fabric and the first arrivals
   warm the zone. Target: comfort regret 06:00-07:00 on warm days (public-like), at the price of chiller/fan energy
   in the first hours. Arms: H-A 1 h; H-B 3 h.
3. **st_swing: swing-zone preconditioning target.** A zone that needed cooling for >= 30 min of the last workday's
   comfort hours is preconditioned only to comfort_lo + margin_occ + k (instead of comfort_lo + margin_pre, 0.83 K);
   the label is renewed at the end of every comfort day with occupants. Setback floors are unchanged (frost-neutral by
   construction). Target: gas (and the handler run time and ventilation it drags along) 03:00-06:00 on shoulder days,
   plus the cooling of that heat later. Arms: S-A k = 0.1 K; S-B k = 0.3 K.
4. **st_msat: cost-model supply air on mixed handlers.** For a running handler with heating and cooling zones, v13
   uses a fixed floor (293.67 K). Instead, each step choose the supply-air setpoint on a 0.5 K grid up to the mixed
   air that minimises a modelled cost: chiller (flow x (mixed - supply) / COP 3.5) + supply and exhaust fans (flow x
   pressure / 0.9), both priced at r J of gas per J of electricity, + reheat gas of the heating zones, + a steep penalty
   on cooling a zone could not get at its design flow. Target: energy/carbon on shoulder days (occupied and
   preconditioning hours). Arms: M-A r = 2.1 (the score's ratio of the marginal normalised cost + carbon of 1 kWh of
   electricity to 1 kWh of gas, computed from the kit's tariffs); M-B r = 3.0.

## Screen (identical objective to rounds 12-14)
- 24 seven-day windows (2,016 steps) of `cma_r12.scenario_list()` (12 HS + 12 r10dev); score = 1/3 mean harsh ratio
  + 2/3 mean public-like ratio, per-window ratio = arm loss / v13ref loss on the same window. HC3, HH and pub30 are
  not run or looked at in this round.
- Frost on the 12 HS windows (time series): coldest zone and share of zone-steps below 278.15 K, vs v13ref.
- Every arm is reported (ratios, wins, comfort/energy/carbon per step, frost) in `screen_<arm>.json`.

## Promotion rule (fixed now)
- An arm passes if: mixture <= 0.997, harsh ratio <= 1.002, public-like ratio <= 1.002, HS-12 below-5 C share
  <= v13 + 0.10 pp and HS-12 coldest zone >= v13 - 0.5 K.
- Per idea, the passing arm with the lower mixture is its representative. If two or more ideas pass, one combination
  arm (all representatives together, same settings) is screened under the same rule. The recommended finalist is the
  combination if it passes and beats the best single arm's mixture, else the best passing single arm. No other arms,
  settings or re-runs are added after the first screen result is seen, except one: if an idea's arms both fail only
  by an error found in the code (a bug, documented in REPORT.md), the fixed code may be re-screened once.
- Finalists get full-length HS-18 runs with time series (v13 run alongside) for the frost report.
- Nothing is shipped from this round. The finalist goes to a separately pre-registered confirmation (full length,
  HC3 40 + HH 40 + pub30, as round 14) that is written but not run here.
