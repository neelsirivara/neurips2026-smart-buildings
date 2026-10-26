# Round 5 plan, keyed to v7's Kaggle public score (written 2026-10-23, before the score is known)

**Outcome (2026-10-24):** v7 public score **0.01088**, rank **75 / 315** → the "> 0.0090" row applies: robustness round.
Concretely, when the Mac returns (in this order):
1. Which local set predicts Kaggle? Our default-size held-out sets (0.0097–0.0117) bracket 0.01088; the public-30 (0.00786)
   and shipped-size (0.00725) sets do not. Re-run v7 + pid_water on (a) the unused Minneapolis weather station with the
   shipped six buildings, (b) default-size generated buildings × all six stations, (c) with and without starter-kit PR #1
   (occupancy fix) and PR #2 (gas-billing fix) to see whether the grader's kit version moves our number.
2. Loss decomposition on whichever set matches 0.0109, then targeted fixes (cold-climate ventilation gas, morning
   recovery, large-building comfort) plus the public-notebook and literature ideas in `../COMPETITION_INTEL_2026-10-24.md`
   (cost-based supply-air reset, weekend/Monday handling, sensor-lag compensation, mild-weather hot-water reset).
3. Never use the gas-billing quirk (setpoint toggling); a check that v7 does not benefit from it goes in the paper.
4. Up to 5 Kaggle submissions/day: spend them on discriminating variants (e.g. v6 vs v7) only after local screening.

Local reference points for v7 (mean |mean per-step reward|, lower is better):
public 30 scenarios **0.00786**; fresh buildings at the shipped six's sizes **0.00725**; 74 untouched held-out
**0.00971** (mixes larger default-size buildings). Kaggle public board on 2026-10-22: #1 0.00578, #8 0.00647, #30 0.00996.

When reporting the score, also note (if visible in the notebook output): the per-scenario totals or counts, the number of
steps per episode, the kit version or any plant/reward constants the template sets, the run time, and the daily
submission limit.

| Kaggle public score | Reading | Round 5 |
|---|---|---|
| **Submission errors / score missing** | Contract mismatch with the template (e.g. no `zone_map` in metadata, different action spec, step limit). | Fix the integration first: diff the official template against the kit's `evaluate.py`; v7 already degrades to no area scaling without `zone_map`, so look at imports, file paths, time limits. |
| **≤ 0.0070** | Test buildings are at least as easy as our shipped-size proxy; local sets are predictive or pessimistic. | Keep the method; push the largest loss terms toward the leader (0.00578 needs about −20%): cold-climate ventilation gas (outside-air heating is 54% of Fairbanks gas), morning recovery, chiller electricity under high loads. Full-length switch ablation of v7 first (attribution), then 1–2 new mechanisms per family. |
| **0.0070 – 0.0090** | Consistent with local proxies (0.00725–0.00971). | Same as above; also widen the generator-based training set toward the shipped six's size ranges (round 4 showed default generator sizes are larger than the test distribution is said to be) so screens weigh the right buildings. |
| **> 0.0090** | Worse than every local proxy: the hidden buildings or the kit differ from what we simulate (plant constants, weather strips, occupancy, reward scaling). | Robustness round: rerun v5/v6/v7 and pid_water on generated buildings with perturbed plant constants (valve capacity, fan curves, COP, envelope) and on weather strips from extreme months; find which perturbation reproduces the gap; prefer the controller version that degrades least; consider submitting v6 or v5 once to see which local metric tracks Kaggle. |
| **v7 worse than an earlier version on Kaggle** (if you also submit v6) | The round-4 switches overfit our buildings. | Submit with switches selectively off (the code reproduces v6 bit for bit with them off) to find the culprit with one submission per day. |

The Mac (`ssh mac`) is idle and ready; the round-4 scripts (`experiments/src/`, Mac tree `~/neurips/sb/`) rerun any of
these within hours.

**Round 5 outcome (2026-10-26, laptop):** done as planned except the plant-perturbation robustness runs (the probes made
them unnecessary): Kaggle probes v6 0.01116, v5 0.01161, pid_water 0.06404 show the hidden buildings behave like the
shipped six and the gap is weather (public + Minneapolis reproduces the ratios; the hidden stations are harsher still);
v8 (weekend setback, request cap 20 kW) shipped under the pre-registered rule, Kaggle 0.01074. See STATUS.md "Round 5".
