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

---

# Self-review 1, pass 2 -- round-3 draft (2026-10-23, ~12:00 PDT)

Same form. Draft reviewed: `paper/main.pdf` after `finalize.sh` with SADR v6 (`r3_c16_pre035_min1`)
shipped; 12 pages (main text through page 6, references page 7, appendices from page 8).

## Summary
The round-3 revision decomposes the remaining loss of SADR v5 into comfort, fan, chiller, pump and
gas, diagnoses the controller's weakness on large generated zones (fixed caps and gains tuned on
~100 m2 zones; every VAV box has the same design flow), and adds area-scaled zone loops, physical
and water-side request caps, a per-zone optimum start and an adaptive setback floor (v6). 17 v6
configurations are screened against v5 and the v6 defaults; a composite chosen by a rule fixed in
advance ships after a full-length confirmation: public 0.00803 vs 0.00831 for v5 (-3.4%, 28/30),
40 held-out scenarios on 8 generated buildings 0.01206 vs 0.01371 (-12.0%, CI 9.5-14.3%, 40/40),
34 never-screened held-out scenarios -10.8% (CI 8.3-13.5%, 34/34); ratio to pid_water 0.146
(public) and 0.237 (held-out).

## Strengths (new in round 3)
- The held-out set is four times larger and spans the generator's size range (32-120 zones, zones
  up to 1,373 m2); v5 and pid_water are re-run on it, so the before/after is paired per scenario.
- Selection hygiene is explicit: the choice rule was fixed before any full-length composite run,
  the six held-out scenarios that informed the screen are excluded in a separate estimate, and the
  ledger (Table 8) lists every variant including the seven that lost.
- The mechanism story is checked by the decomposition: on the new buildings the comfort term falls
  from 14.2% to 3.0% of the loss and the largest-quartile recovery from 0.65 h to 0.12 h, matching
  the diagnosis; the cost (fan energy) is stated.
- The bake is verified bit for bit against the evaluated configuration and across machines.

## Weaknesses
- The public-set gain of v6 is small (3.4%); the paper says so and attributes the held-out gain to
  zone size, which the per-building figure supports, but the attribution is still correlational
  (no per-mechanism full-length ablation; the ablations are 10-day screens on 12 scenarios).
- The shipped flow cap (0.35) is the edge of the screened range; a reviewer could ask why the line
  search stopped. (Addressed in Limitations.)
- Screen CIs over 6 scenarios are coarse; several "worse" verdicts (c01) are tiny in absolute terms.
  The table reports the effect sizes, so a reader can judge.
- Still no Kaggle score; the leaderboard paragraph is context only and says so.
- Remaining gap on generated buildings is chiller electricity (2x the public level per step); the
  paper states it but does not diagnose it.

## Scores
| criterion | score | justification |
|---|---|---|
| Clarity | 4 | Round-3 protocol and ledger are clear; the main text is dense (six full pages). |
| Soundness | 4 | Pre-fixed rule, paired CIs on every set, clean unscreened subset; mechanism attribution partly from screens. |
| Reproducibility | 5 | Every number from result files (AUDIT 34 claims, 0 missing), resumable scripts, bit-identical bake and cross-machine checks. |
| Significance | 4 | A strong, transparent non-learned reference; the held-out improvement is large and consistent (40/40). |
| Overall | 7 | Better supported than pass 1 (held-out set 4x, failures reported); still no Kaggle number. |
| Confidence | 4 | |

## Must-fix before upload (pass 2)
1. Reconcile "17 v6 variants" (Sec. 3) with "7 of the 16 variants" (Sec. 4): the 17 include the v6
   defaults. -- applied: Sec. 3 now says "17 v6 configurations (the v6 defaults and 16 variants)".
2. State the cost side of v6 on large buildings (fan energy) and what remains (chiller). -- applied
   in "Why v5 lost on large zones".
3. Say that the shipped preconditioning flow cap is at the edge of the screened range. -- applied in
   Limitations.
4. Do not describe v5/pid_water on the held-out sets as run "before the screen" (they ran
   concurrently on the Mac); they are fixed policies, which is what matters. -- applied.
5. Main text within six pages after the additions. -- applied (per-scenario figure moved to
   Appendix A, one Analysis sentence shortened; references start on page 7).
6. Fill the author block before upload. -- user.

## Applied fixes (deltas recorded in STATUS.md)
Items 1-5 applied in the 2026-10-23 ~12:00 draft; build: 0 errors, 0 undefined references, 0 `??`,
0 overfull boxes. Not applied: per-mechanism full-length ablations, the chiller diagnosis on the
generated buildings and the Kaggle submission (compute / user).
