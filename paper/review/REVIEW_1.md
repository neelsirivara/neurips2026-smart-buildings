# Self-review 1 -- SB26 poster-round paper (final draft of 2026-10-23)

Reviewer form (NeurIPS competition-track workshop style): Summary; Strengths; Weaknesses;
Clarity (1-5); Soundness (1-5); Reproducibility (1-5); Significance / usefulness to the
competition community (1-5); Must-fix list; Overall (1-10) and confidence (1-5).

## Summary
The paper presents SADR, a rule-based, metadata-driven HVAC controller for the SB26 challenge:
occupancy-gated modes with a self-tuning optimum start, per-zone PI loops on net heat mapped to
dampers and reheat valves through the supply-air and discharge-cap physics, closed-form
trim-and-respond static pressure, and demand-based hot-water resets. On the 30 public scenarios
it scores 0.0083 against 0.0550 for the strongest organizer baseline run on the same machine
(ratio 0.151, CI 0.117-0.188, 30/30 wins); on 10 scenarios from two generated buildings with
unseen strips the ratio is 0.278 (10/10 wins). A decomposition of the loss by term, station and
hour motivated one revision (coldest supply air when cooling, deeper night setback) worth a
further 9.7% on the public set (not significant on the ten held-out scenarios).

## Strengths
- The design is derived from stated properties of the reward and plant (comfort charged only
  when occupied; fan power ~ P^{3/2}; constant COP; discharge cap), and each property maps to
  one mechanism; the paper then verifies the mechanisms with data (hourly loss, out-of-band
  zone-steps, per-station decomposition) rather than asserting them.
- Evaluation hygiene: all policies re-run on one machine with paired bootstrap CIs and Wilcoxon
  tests; organizer values also reported; a cross-machine check (0.000% / 0.017% gaps); a
  generated held-out set run once after model selection; every number generated from result
  files and audited (AUDIT.md, 24 claims, 0 missing).
- The analysis-driven revision is a clean, falsifiable prediction (cold SAT helps cooling
  climates, deeper setback helps Fairbanks, mild climates unchanged) that the full-length
  candidate table confirms station by station.
- Honest reporting of the leaderboard context (not comparable, but 1.4x the leader) and of the
  non-significant held-out gain of v5 over v4.

## Weaknesses
- Model selection on the public set at full length makes the public number optimistic; the
  held-out set is small (10 scenarios, 2 buildings), so the v4-to-v5 gain cannot be confirmed
  there (CI [-0.00071, +0.00006]). The paper says so, but a reviewer may still want more
  generated buildings.
- The held-out ratio (0.278) is clearly worse than the public one (0.151), driven by the
  larger generated building; the paper notes it but does not diagnose why (zones per handler,
  two occupants per zone, colder strip?). A one-paragraph diagnosis would strengthen the
  transfer claim.
- "Why it wins" attributes pid_water's comfort regret to its per-handler loop; the attribution
  is argued from the baseline code and the out-of-band statistic, not from an ablation of the
  baseline. Acceptable for a competition report, but it is an interpretation.
- The random search is small (16 configurations) and the screen is five days; the paper's own
  conclusion ("gains come from structure") makes this acceptable, but the tuning figure adds
  little beyond that sentence.
- Minor: the Kaggle number is not yet available (the user must submit); the paper has no
  Kaggle result, only the public-leaderboard scale.

## Scores
| criterion | score | justification |
|---|---|---|
| Clarity | 4 | Dense but linear; the method section is long for a 6-page paper, the algorithm is in the appendix. |
| Soundness | 4 | Paired statistics, same-machine baselines, held-out once; optimism of the public number is acknowledged; mechanism attribution partly interpretive. |
| Reproducibility | 5 | Repository, deterministic seeds, resumable scripts, every number scripted, cross-machine check. |
| Significance | 4 | Strong reference point for learned entries (6.6x below the best organizer baseline, 30/30); no learned component. |
| Overall | 7 | Good competition report; would be stronger with a diagnosis of the held-out gap and more generated buildings. |
| Confidence | 4 | |

## Must-fix before upload
1. State explicitly in the held-out paragraph that the v4-to-v5 gain is not significant there (done in this draft).
2. Do not call the Fairbanks v4-to-v5 change a gain in the main-result paragraph when it is -0.0003 (done: "moves by").
3. Make the units of the decomposition readable (shares, not 0.0002 of 0.0092) (done).
4. Keep the main text within six pages (done: references start on page 7).
5. Fill the author block before upload (user).

## Applied fixes (deltas recorded in STATUS.md)
- Items 1-4 above were applied to the draft of 2026-10-23 06:50 PDT before this review was
  written up; the review scores refer to that draft.
- Not applied (would need more compute or user input): more generated buildings; a diagnosis of
  building_0502; the Kaggle submission.
