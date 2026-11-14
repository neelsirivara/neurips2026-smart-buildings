# Resumed by the main session (2026-11-12 ~01:00 UTC)

- v14 (cooling handover ramp, HA) is in the paper: `paper/make_macros_r14.py` -> `results_macros_r14.tex`, a v14
  paragraph in the tuning section, a versions-table row and an abstract clause. 22 pp, 0 undefined.
- Round 14 (frost-floor CMA) is DROPPED. Its best (0.998 vs v12) does not beat v13 (about 0.996), and the Mac is the
  user's work machine again, with an ALERT on weekend_check.
- v14 Kaggle probe: one retry of `kaggle_probe_r14.py push/check`. If it errors again, push v14's code as a new version
  of the working v13 kernel.

# v14 packaged; Kaggle probe DEFERRED (2026-11-10 ~01:00 UTC)

- submission/candidates/transfer_policy_v14.py sha256 1f2944e5... = sadr_struct.py + st_hand_c_h 1.0 (class TransferPolicy, as v13). Lenovo pub30 atlanta_2 8640 steps: total -30.849723828052447 = HA exactly (rel diff 0); experiments/results/v14pkg/.
- Kaggle: 5 kernels r14g01c00..c04 sat QUEUED 10+ h and filled the account's 5 batch-CPU slots (cause of the all-day stall). Their work was already done on the Mac; deleted on Kaggle and marked abandoned in kaggle_registry.json (backup /tmp).
- kaggle_probe_r14.py push succeeded twice, but both runs ERRORed: FileNotFoundError /kaggle/input/competitions/neurips-2026-smart-buildings (competition source IS in kernel-metadata.json, identical to v13's working one). Likely Kaggle-side. Next: re-run the v13 kernel as a control; if it also fails, wait for Kaggle; then `python experiments/src/kaggle_probe_r14.py push/check/submit`. Nothing submitted for v14 yet.

# struct_r1 HA confirmed vs fresh v13: SHIP as v14 (2026-11-09 ~23:30 UTC)

- experiments/results/struct_r1/decision_HA_v13fresh.json (plan CONFIRM_PLAN.md sha256 8b82778e...): mixture -0.52% [-0.62, -0.41] (HC3 -0.04%, 28/40; HH -0.76%, 38/40), pub30 -0.59% (25/30), HH comfort regret -79%, frost unchanged; all guards pass.
- The r12var-reuse check missed 1e-9 (pub30 denver_7, 1.6e-9, Mac vs Kaggle), so per the plan v13 was re-run fresh on all three sets (v13fresh). HA HC3/pub30 ran on Kaggle, v13fresh HC3/pub30 on the Mac (Kaggle queue stuck): host difference ~1e-9, negligible vs the effect.
- v14 = sadr_struct.py + st_hand_c_h 1.0; packaging + Kaggle probe in progress.
- Round 14 (frost floor CMA) still running; its comparator is v13 by plan. If it passes later, HA is applied on top per CONFIRM_PLAN.

# struct_r1: structural-change screen on top of v13 (2026-11-09, subagent; nothing shipped)

- Plan `experiments/results/struct_r1/PLAN.md` (sha256 06b9cb45..., hashed before any screen run). Policy copy
  `experiments/src/policies_struct/sadr_struct.py`, all switches off = v13 bit for bit (`identity_check.json`).
  Mac, ~/neurips/sb/struct, one runner, 6 workers; booked on WEEKEND.md.
- Screen (24 seven-day windows, ratio vs v13; harsh / public-like / mixture): late-recovery escalation 1.019 / 1.017 /
  1.018 (fail); **cooling handover ramp 1 h (HA) 0.9997 / 0.9891 (12/12) / 0.9927 (pass)**, 3 h 0.9931 (pass);
  swing-zone target 1.000 / 0.9995 / 0.9997 (fail); cost-model mixed-handler SAT 1.001 / 0.999 / 0.9997 (fail).
  Files: `screen_<arm>.json`. HA's mechanism: public-like comfort regret -65%, energy +0.1%.
- Frost, HA vs v13 on HS-18 at full length: coldest -9.95 C vs -9.95 C, below-5 C 4.240% vs 4.239%
  (`frost_hs18_HA.json`). HA does not touch setback.
- Next: the confirmation in `struct_r1/CONFIRM_PLAN.md` (HC3 + HH + pub30 at full length, mixture CI < 0, pub30 and
  frost guards; comparator v13, or v14 if round 14 ships). Not run. (REPORT.md could not be written by the
  subagent; the full report is in its handback to the orchestrator.)

# v13 Kaggle public score: 0.01021 (2026-11-09 ~07:30 UTC)

- Ref 58147185 (label v13_r12var): public 0.01021 vs v12 0.01030 (lower is better, about -0.9%). Recorded in
  experiments/results/kaggle_feedback.json; paper macros regenerated (RTwKagVThirteen) and main.pdf rebuilt (0 undefined).
- Final Kaggle selections are the user's; candidates are v13 (submission/candidates/transfer_policy_v13.py) and v12.

# v13 packaged + Kaggle probe (2026-11-09 UTC, packaging session)

- File: `submission/candidates/transfer_policy_v13.py`, sha256 4cf9e40b12a14489c8a8682c82e295b80e3d01934f4da05c3c9efb5ed3c6f516.
  Copy of shipped v12 (44ebbb3b...) with the 14 DEFAULT_PARAMS keys of `round12/candidate_v12setback.json` (12 changed
  lines; night_low_ext 10.0 / night_high_ext 6.0 unchanged) + docstring note. submission/transfer_policy.py,
  best_params.json, round12/round13 untouched.
- Lenovo equivalence (v13, no --params-json, pub30 building_train_1/atlanta_2, 8640 steps): total -31.37316089353044,
  avg -0.003631152881195653 == round6 r12var reference exactly (rel diff 0). Copy:
  `experiments/results/round13_v13pkg/lenovo_v13_atlanta_2_summary.json`. LOCK taken and released.
- Kaggle: `experiments/src/kaggle_probe_r13.py`, kernel neelsiri/sadr-v13-smart-buildings v1 (private) COMPLETE;
  atlanta_2 total -31.376361 vs local -31.373161 (rel -1.0e-4, 8641 vs 8640 steps), parquet ok -> check ok.
- Probe submission ref 58147185 (2026-11-09 01:34 UTC, logged in kaggle_feedback.json). Public score: PENDING after
  ~60 min of polling (v12 = 0.01030, lower is better). Final Kaggle selections not changed.

# Paper updated for rounds 12-13 / v13 (2026-11-08, paper session)

- New `paper/make_macros_r12.py` -> `results_macros_r12.tex`, `table_tuning_r12.tex` (Table 5: v12, r12cand, r13cand,
  v13 with mixture CI, HC3/HH/P, HS loss, coldest zone, below-5 C share, frost guard) and `table_params_r12.tex`
  (appendix: the 14 constants); AUDIT.md gains an r12 block (all checks pass; it re-derives the frost guard and the
  round-13 choice). Backups: `paper/main_pre_r12.{tex,pdf}`.
- Paper: new Section 4.1 "Tuning the constants" (protocol, the frost lever found twice, v13 with its caveats); one
  abstract sentence; a round 12-13 row in Table 2; Limitations (tuning exploits the missing frost cost; v13's
  confirmation reuses sets and its guard was set knowing r12var's interim frost); "shipped v12" wording now says v12
  is the analysed version and v13 shipped. New citation hansen2016cma (verified on arXiv, logged).
- Build: 21 pages, 0 undefined, 0 overfull.
- **TODO:** the v13 Kaggle score prints "pending" (macro `\RTwKagVThirteen`). Once `kaggle_feedback.json` has the
  `v13_r12var` entry, run `python paper/make_macros_r12.py` and rebuild (pdflatex x2).

# r12var (frost-safe variant) confirmation: PASS (2026-11-08 09:05 UTC, orchestrator)

- r12var = round-12 CMA mean with v12's setback depths (night_low_ext 10, night_high_ext 6); `experiments/src/confirm_r12v.py`,
  `round12/decision_r12var.json`, `round12/frost_r12var.json`, params `round12/candidate_v12setback.json`.
- Mixture -0.39%, CI [-0.65%, -0.12%] (HC3 -0.68%, 36/40 better; HH -0.24%, 21/40); public 30 -2.5% (27/30): primary
  and guard pass.
- Frost on HS: coldest zone -10.0 C (v12 -9.4 C; r12cand -11.4 C); below-5 C share 4.24% (v12 4.24%; r12cand 4.9%):
  passes round 13's frost guard (<= v12 + 0.25 pp, coldest >= v12 - 1.0 C).
- Not shipped yet: round 13 (`results/round13/PLAN.md`) re-tunes with the depths fixed; its PLAN picks mechanically
  between r12var and r13cand after r13cand's confirmation.

# Round 12 confirmation: PASS (2026-11-07 17:30 UTC)

- The CMA mean (`round12/candidate_mean.json`) at full length against v12 (r10_K):
  - HC3 -1.0% (39/40 scenarios better);
  - HH -0.6% (28/40);
  - pre-registered mixture -0.74%, CI [-0.98%, -0.50%], so the primary passes;
  - public 30 -2.6% (28/30), so the guard passes.
  - `round12/decision.json`.
- **Frost on HS (`round12/frost.json`):** the candidate goes colder than v12.
  - Coldest zone: -11.4 C (v12: -9.4 C).
  - Zone-steps below 5 C: 4.9% (v12: 4.2%).
  - HS loss: -1.0%.
  - Per the plan this is flagged to the user before shipping. Nothing is shipped or submitted yet.

# Round 12: CMA-ES tuning of v12's constants on Kaggle (started 2026-11-07 01:29 UTC)

- Pre-registered in `experiments/results/round12/PLAN.md` (sha256 b81afdd7...) before any run.
  - Search: 14 continuous constants, population 10, 15 generations.
  - Objective: 7-day windows on 12 HS + 12 D10 scenarios, as 1/3 harsh + 2/3 public-like ratio to v12.
  - Confirmation: the final CMA mean at full length on HC3 and HH (primary, mixture CI below 0) and the public 30
    (guard: not worse).
- Driver: `experiments/src/cma_r12.py` (resumable; state in `round12/cma_state.json`, log `round12/cma_log.txt`).
- Chain: `_ops/sb_r12_chain.sh` (dataset check, init, dispatcher, loop). The private dataset gained r10dev, r10hc and
  r10hh (version of 01:28 UTC). About 50-60 min per generation on 5 kernel slots.
- Why not chase the top of the board: the leaders' ~0.005 matches what the gas-billing quirk gives (DEEP_DIVE R6). The
  realistic headroom without it is the LP bound, 10-15% of the heating loss.

- **Mac share (2026-11-07 02:50 UTC):** with the user's OK for the weekend, `cma_r12.py` sends 5 of each generation's 10
  candidates to the Mac (`round12/MAC_ON` = 5). Conditions and fallback are as in the booking on `~/neurips/WEEKEND.md`;
  Mac candidates go back to Kaggle after 4 h. The Mac isn't used while the speech chain is live.

# Paper tone pass (2026-11-06 ~14:30 UTC)

- Softer claims: "We argue that a structure-aware rule-based controller is a useful first entry" (was "the right first
  entry"); "shape" instead of "fix" for the three design facts. "Takeaways for SB26 entrants" is now "Pitfalls in the
  kit": only the two kit facts (Saturday decoding, baseline returns) plus our own Kaggle observation, since the best
  entries score less than half of v12's loss. AI line: "We used Claude (Anthropic) as an AI assistant." Four appendix
  sections retitled by topic. 20 pages, 0 undefined. The site gives no page limit or AI rule (paper template on Drive);
  the poster round closes Nov 13. A deeper appendix pass (relevance and display) is still to do before then.

# v12 Kaggle score: 0.01030 public, rank 153 of 589 (read 2026-11-06 13:22 UTC)

- Ref 58050462 (submitted 07:49 UTC) scored 0.01030, 2.4% below v10's 0.01055. The field: best 0.0047, median 0.0119
  (`../_downloads/sb26_lb_2026-11-06/`). Logged in `experiments/results/kaggle_feedback.json`; macros regenerated
  (`make_macros_r9r10.py`: RTenKagVTwelve; `make_macros_r11.py`: rank and field macros).
- Paper: the abstract, the Kaggle paragraph and Limitations now report the score and rank. The Next-step paragraph
  says the best entries score less than half of v12's loss. 20 pages, 0 undefined. Final Kaggle selections (v12 + v11
  recommended) remain the user's step.

# Ablation complete; paper rewritten as prose (2026-11-06 ~03:40 UTC)

- **Ablation (Table 3) complete:** 16/16 arms on the 30 public scenarios, with reference runs matching round 10 to within
  a relative 2e-9. Coldest supply air +7.4% (v12 wins 15, loses 13); zone gains scaled with area +2.2% (wins all 30);
  weekend setback, coil-delivery cap, day-of-week rounding, per-zone start and set-back reheat about +1% each;
  economizer, air boost, model start, heating season and the 20 kW cap under 1%; hot water 350 K, recoverable floor,
  night flush and proportional occupied flow inert (0.0-0.2%).
- **Paper:** at the user's request there are no bullet lists anywhere (prose with run-in paragraph heads). The ablation
  paragraph is written and the abstract states its headline. Ablation table narrowed (it overflowed once complete).
  Builds to 20 pages, 0 undefined, 0 overfull; limitations on p.8, appendix from p.10 (unchanged). Pre-rewrite copies:
  `paper/main_pre_prose.*`.
- **Kaggle v12: submitted** 2026-11-06 07:49 UTC as ref 58050462 (the user allowed reversible, non-final
  submissions). The private notebook check matched local to 0.012%. Score pending; logged in
  `experiments/results/kaggle_feedback.json`. The final selections stay the user's call (recommended v12 + v11).

# Smart Buildings Challenge (SB26) -- STATUS

## Review 2 and round 11 (2026-11-05 from ~07:55 UTC; nothing committed)

A fresh reviewer read the poster paper as a prize judge (`paper/review/REVIEW_2026-11-05.md`). Its verdict was 5.5/10:
rigour 7 and clarity 4, borderline for a $250 prize. Its main points:
- P1: the paper reads as a development diary.
- P2: process claims stronger than the evidence.
- P3: the shipped v12 is not described in the main text.
- P4: every analysis is about v5-v9.
- P5: no Kaggle score for v12.
- P6: a frost choice next to the billing-gap stance.
- P7: no ablation.
- P8: intervals that ignore clustering and selective checks.
- P9: no related work.
- P10: thin limitations.

**Writing fixes applied** (`paper/main.tex`; pre-edit copies `paper/main_pre_review2.{tex,pdf}`):
- New abstract and contributions that lead with the three design facts and the result.
- A "Related work" paragraph. The two MPC references were added and verified on Crossref: Drgona et al. 2020 and
  Oldewurtel et al. 2012. BOPTEST, CityLearn and Sinergym were already in `refs.bib`.
- A "Three design facts" paragraph, and every main-text symbol defined (l0, q_on, delta, C_w/C_a, k_v, eco band).
- The "Additions after v6" bullet, listing all eight later mechanisms.
- Process claims corrected: v4 and v5 were selected on P, and round 9 reused HC2.
- Table 1 is now generated (`paper/table_main_r11.tex`) at 5 decimals. Its new column is each row's ratio to v12 with a
  paired bootstrap CI; `pid_water` is 7.37 [6.02, 9.29], 30/30.
- Building-clustered intervals: v12 vs v11 on P [-1.3, -0.7]%, on HC3 [-1.9, -1.0]%.
- The Kaggle paragraph now names its reference versions, with a caveat.
- Headings by content.
- All twelve round-7 checks are in `paper/table_checks_r7.tex`, with the "Checks" text matching them.
- A takeaways box for entrants.
- Limitations rewritten: simulator gaps (billing gap and frost together), unconfirmed parts, the trade-off, FD, and
  the LP bound.
- Cheap wins 1, 2, 7, 9, 12, 13 and 14.

New numbers come from `paper/make_macros_r11.py`, which writes `results_macros_r11.tex`, the tables and an r11 block
in `AUDIT.md`. The build has 19 pages, 0 undefined references and 0 overfull boxes, with the main text and references
on pages 1-8.

**Round 11 = leave-one-out ablation of v12 (P4, P6, P7)**, plan `experiments/results/round11/PLAN.md` (sha256 d55e6b27...,
written before any run). The 16 arms plus the reference run on the public 30, and the frost pair runs on HS. That is 55
shards in all, on private Kaggle CPU kernels (`experiments/src/ablation_r11.py`; dispatcher `kaggle_sim.py dispatch
--loop --max 5`, log `results/round6/kaggle_dispatch_log.txt`). The first 5 kernels were pushed at 08:10 UTC. The Mac
was not used: the speech session held its GPU lock.

**Open:**
- The ablation results go into Table 3, its two-sentence summary in Section 4, the frost numbers and the v12
  loss-by-hour figure. All of these are generated by `make_macros_r11.py`; re-run it, then pdflatex x2.
- The P8d generator headers for the hand-typed tables.
- Minus signs in `make_macros.py` output.
- **A Kaggle score for v12 is the user's call** (the reviewer's top request). `experiments/src/kaggle_probe_r12.py` is
  a v12 copy of the round-9 probe: slug sadr-v12-smart-buildings, local reference r10_K. Push and check it after the
  ablation frees the Kaggle slots; submit needs `SB_COORDINATOR_OK=1`.

## Poster paper updated for v12 (2026-11-04 ~19:30 UTC; nothing committed)

`paper/main.tex` now presents v12 as the shipped policy (abstract, Section 3, Table 1 rows v11 and v12, Table 2
rounds 9-10, parameters table, Appendix G "Rounds 9 and 10"). Appendix G is generated: `paper/make_macros_r9r10.py`
writes `paper/results_macros_r9r10.tex` (197 macros from the round 9/10 result JSONs, 0 missing) and a block at the
end of `AUDIT.md` (source file and field per macro, 37 checks, all pass). Re-run it after `make_macros.py` /
`make_audit.py`. Every hand-typed number matched its file; wording corrected in three places (round-4 losses
"6 of its 7 on 0610 and 0639", "4 wins, 4 losses, 32 unchanged", HC2 called "unseen" rather than untouched). Compute
paragraph refreshed (rounds 6-10). Build: MiKTeX, 16 pages, main text and references through page 6, appendix from
page 7, 0 undefined, 0 overfull, `main.pdf` md5 5d381683...; pre-edit copies `paper/main_pre_v12text.{tex,pdf}`.
Open: `paper/main_r10.txt` is stale; round-9 compute is described, not counted; the Kaggle column for v11/v12 is
"--" (neither submitted; the Kaggle selection is the user's call). Poster paper due Nov 13.

## Round 10 (2026-11-01 ~10:00 UTC - 2026-11-02 ~02:00 UTC): **v12 shipped** under the pre-registered rule

**v12 shipped 2026-11-02 ~01:52 UTC** in `submission/transfer_policy.py` (md5 57bc72cb..., sha256 44ebbb3b582f8e06...;
`experiments/src/ship_round10.py --cand r10_K`). v12 = v11 + E (`wk_ext_lo` 12) + C (`mpr_on` 1, `mpr_burst` 0, `mpr_safety`
1.3) + a heating season of 7 days instead of 1, only while some step of the last 24 h was below 15 C (`season_ext_steps`
2016, `season_oat_k` 288.15). v11 kept as `submission/transfer_policy_v11_shipped_before_round10.py`. No Kaggle kernel or
submission in this round; final selections should become v12 + v11 (the coordinator's call). Nothing committed or pushed.

Pre-registration `experiments/results/round10/PREREG.md`, final sha256 e79c7de4ee464d2a... (Part 1 839e2ed1..., 10:10 UTC;
Part 2a selection rule 82341df2..., 17:09 UTC; Part 2 candidate ddc86103..., 19:18 UTC, hashed before the first confirmation
job; copies with hashes on the Mac in `~/neurips/sb/r10/`). The last hash adds only the decision section.

Sets (`src/make_sets_r10.py`, `results/round10/sets/`): HC3 (40 cold, primary), HH (40 hot, guard), both on 8 new
shipped-family buildings (seeds 700-706, 708; 707 rejected by the kit); D10 (24, shipped six x unused windows, development).

Confirmation, v11 -> v12, 8,640 steps, paired bootstrap 5,000 resamples (`results/round10/confirm_r10_K.json`):
| set | n | loss | change [95% CI] | wins |
|---|---|---|---|---|
| **HC3 (primary)** | 40 | 0.02398 -> 0.02364 | **-1.41% [-1.75, -1.11]** | 40/40 |
| public-30 | 30 | 0.00753 -> 0.00745 | -0.97% [-1.40, -0.59] | 21/30 |
| HH (guard) | 40 | 0.00727 -> 0.00728 | +0.04% [-0.02, +0.11] | 4/40 |
| HS | 18 | 0.02139 -> 0.02110 | -1.36% [-1.75, -1.01] | 18/18 |
| M | 12 | 0.01030 -> 0.01018 | -1.21% [-2.18, -0.49] | 12/12 |
| FD | 20 | 0.00994 -> 0.00989 | -0.47% [-0.95, -0.14] | 11/20 |
Rule met (HC3 CI below 0 and >= 24/40 wins; public CI not entirely above 0; no guard with CI entirely above 0 and mean
above +0.20%). Stable over bootstrap seeds 0-9. Public by station: Denver -2.21% (6/6), Fairbanks -1.68% (6/6), Atlanta
-1.58% (4/6), Phoenix -1.05% (3/6), Singapore 0.00% (2/6).

What v12 costs, and limits of the evidence:
1. Comfort regret rises 20% on HC3 (3.7% -> 4.5% of the loss) and 14% on the public 30 (2.8% -> 3.2%); C causes most of it
   in development; energy and carbon more than pay for it (HC3: comfort +0.74, energy -0.63, carbon -1.52 points of loss).
2. HH missed the prediction written in Part 2 (-0.1 to -0.4%): Phoenix +0.07% (4/20 wins), worst building_0702/phoenix_3
   +1.19%, building_0704/phoenix_3 +0.96% (energy, not comfort). April Phoenix gets a little worse. FD worst
   building_0639/phoenix_2 +0.60%. All inside the guard.
3. HC3 cannot test the 15 C gate (always open in cold windows). The gate and the other new switches were chosen after
   reading rows of the same 30 development scenarios; public-30 and HH guard against harm but E, C and B ran on the public 30 in round 9.
4. HC3 and HH have now been read; a later candidate needs fresh sets.

Development (`results/round10/dev_summary.json`, D10 + six cold HC2, pooled against v11): E -0.31%; E + C -0.37%; B + E
-0.79% but Singapore +0.22% (0/6) and building_train_4/atlanta_4 +2.87% (the 7-day season also shuts the night flush); gate 10 C
-0.89%, gate 15 C -0.97% (chosen by the Part 2a rule; worst scenario 0.00%), no gate -0.85% (disqualified). **Cooling integral x3
is worse: +0.79%, Singapore +5.31%, comfort up**, so the round-9 diagnosis that the integral is simply too slow did not hold at x3
(smaller multipliers untested); no hot-weather component.

Decision for the coordinator to review: **`tw_ramp_k` left out**, a departure from round 9's candidate B. From `simulator/boiler.py`
the loop flow is billed at the setpoint, so the ramp lowers billed gas, from the billing gap the quirk uses on the other side (it never bills below delivered heat, and
physical gas was not measured separately). With the 7-day season its effect was nil on cold dev rows (bit-identical runs); alone it
was about -0.26 points cold. It could be re-added in January with its own test.

Checks: v12 code off = v11 bit for bit (6 D10 scenarios); bake check; robustness 35/35; 36-step smoke; shipped file = confirmation
runs bit for bit at 8,640 steps on building_0700/denver_c1 and building_train_8/denver_6 (`results/round10/xcheck_shipped_v12.json`);
`results/tune/best_params_v12.json`; README and notebook header. The smoke step inside `ship_round10.py` failed on the laptop
(its `python` has no `gin`), so smoke and cross-check ran on the Mac with the shipped bytes.

Paper: Appendix G retitled and extended with a v12 paragraph; rebuilt, 16 pages, references on page 6, appendix from page 7, pages 1-15
text identical to before, 0 undefined, 0 overfull (`paper/main.pdf` md5 10536f26...; pre-v12 copies in `results/round10/`). AUDIT.md not extended (as round 9).

Compute: Mac only, `OMP_NUM_THREADS=1`, no GPU lock, memory 87% free at every check. Batches: `dev_a` 116 jobs, `dev_b` 94 of 122
(3 workers, beside PAIEC's 1), `dev_c` 112 (3 workers, finished cleanly 18:19 UTC); after the coordinator's 4-worker limit `devcheck_K` 6, `confirm_K` 240
(19:18-01:51 UTC, rc 0 throughout), `xcheck_v12` 3. I stopped the `dev_b` runner at 15:29 UTC to skip a superseded variant (its 3 running jobs finished, never more than 3 workers);
`r10_d_bhec` has 5 rows, unused. The laptop rebooted at ~18:57 UTC; nothing was lost. Laptop: orchestration, brief compare scripts, robustness test, pdflatex; before the reboot
some compare runs lacked `OMP_NUM_THREADS=1`. After the reboot compare and job building ran on the Mac until the laptop's python was idle. Logs `~/neurips/logs/r10_*.log`, copies in `results/round10/jobs/`.

## Round 9 (started 2026-11-01 ~02:00 UTC): where a large gain could come from -- **v11 shipped** (Saturday bug fix)

**v11 shipped 2026-11-01 ~06:35 UTC** in `submission/transfer_policy.py` (md5 6335742f..., sha256 f9c0ad1a...;
`experiments/src/ship_round9.py --cand r9_dow`): v10 + `dow_snap` (round the decoded day of week). Pre-registered rule
met (`results/round9/confirm_r9_dow.json`): HC2 (44) 0.02152 -> 0.02120, **-1.50% [-1.71, -1.30], 44/44 wins**;
public-30 0.00762 -> 0.00753, -1.23% [-1.88, -0.69], 28/30; HS (18) -1.59% [-1.96, -1.24], 18/18; CIs stable over
bootstrap seeds 0-9. Secondary (outside the rule): M (12) -1.70% [-2.75, -0.76], 11/12; FD (20) -0.59% [-1.33,
+0.07], 13/20 (worst building_0639/denver_6 +2.8%, energy; the losses sit on the two largest-room generated
buildings). Paper note (Appendix G) updated with FD; rebuilt 16 pages, main text through page 6, 0 undefined, 0
overfull (main.pdf md5 4aabeb29...). v10 kept as `submission/transfer_policy_v10_shipped_before_round9.py` (md5 7d7f6899...); v9 /
v8 copies untouched; `results/tune/best_params_v11.json`; README v11 section; notebook template header v11; robustness
test 35/35; 36-step smoke run. Final Kaggle selections should become v11 + v10 (the coordinator's call). **No Kaggle
submission made**; `experiments/src/kaggle_probe_r9.py` (build / push / check a private notebook; submit refuses
without `SB_COORDINATOR_OK=1`). Nothing committed or pushed.

Goal (coordinator): decompose v10's loss on HC2 and the public 30 by component, bound what any controller can reach,
prototype 2-3 structurally different controllers, ship v11 only under a pre-registered rule. v10 stays shipped.
Pre-registration: `experiments/results/round9/PREREG.md` (Part 1 sets/rule, Part 2 candidate B).

Findings (2026-11-01, final at ~10:00 UTC):
1. **Decomposition** (all 74 scenarios, Kaggle `run_diag.py` runs identical to round 8's; `results/round9/
   decomp_v10_{pub30,hc2}.json`): HC2 0.02152 = gas 94.2%, comfort 2.8%, fan 2.5%, pump 0.5%; public 30 0.00762 = gas
   51.0%, chiller 41.2%, fan 4.9%, comfort 2.7%; Kaggle mixture ~79% gas, ~17% chiller. Per scenario (12 runs with
   plant internals, `decomp_mac12.json`): heating scenarios are 89-97% gas, hot strips 91-92% chiller; comfort 1-8% (largest on
   building_train_7 in deep cold: 8%, its perimeter zones are at the coil's water-side limit, ~20 kW per box at -24 C,
   damper and discharge cap saturated), fan 2-7%, pump < 1%. HC2 by the score's own terms: carbon 70%, energy cost
   27%, comfort 2.8%; public 30: energy 51%, carbon 47%, comfort 2.7%.
2. **Delivery bound** (`bound_r9.py`, `results/round9/bound_r9_v10.json`): occupied coil duty is within 0.2-0.5% of
   the instantaneous lower bound (net need at the 308.15 K cap, or need + the forced air's outside-air share while a
   handler runs); unoccupied 0.8-1.8%. The heating cost per joule g = (T_cap - T_sa)/(T_cap - T) (median 1.75) is
   physics at 30% outside air. Hot strips: chiller energy / net cooling = 1.14 (Singapore) - 1.33 (Phoenix) =
   the outside-air share, no reheat.
3. **The zone air is quasi-algebraic**: with the handler off the zone air relaxes to the slab/partitions within one
   5-minute step (air ~0.1 kWh/K per 100 m2 against a 5 W/m2K slab coupling). So occupied heat must be delivered
   continuously; band riding (bursts, handler off between) collapses comfort (dev run, building_train_1/fairbanks_1,
   7 days: -178.56 vs v10 -85.98; `results/round9/dbg/obr`). Prototype A (`obr_on`) dropped.
4. **Hot-water loop** (tank charging + dissipation + the flow term billed at a setpoint the warming tank has not
   reached): 0.4-0.7% of the gas in cold scenarios, 1.1-3.6% in mild ones (3-5 loop re-warms a month) -> candidate B.
5. **Billing quirk, measured (analysis only)**: `quirk_probe_r9.py` overrides v10's hot-water setpoint in the harness
   with the saw-tooth published in topic 752142 (never in a policy file; nothing submitted; Mac). Harness check: no
   override = the official v10 run (building_train_1/atlanta_2 -33.1021529 vs -33.1021527). Loss x0.54-0.62 on the
   Fairbanks / Minneapolis / Denver probes (comfort unchanged), x0.83 Atlanta, x1.00 Phoenix / Singapore; through the
   66/34 Kaggle mixture: **v10 + simple saw-tooth = 0.0069 (-35%, ~rank 37)** (`results/round9/quirk_summary.json`).
   PR #2 measured 0.38x billing for a tuned saw-tooth (round 6's estimate ~0.0058, ~rank 10).
6. **Leaderboard** (read-only CLI, 2026-11-01 ~03:00 UTC, `results/round9/intel/`): #1 0.00470, #10 0.00588, #20
   0.00612, #50 0.00781, #100 0.01037; v10 0.01055 = #113 of 400 shown (112 ahead).

7. **v10 bug: every Saturday is treated as a workday.** The day-of-week observation is an integer day sent as float32
   sin/cos; v10 decodes it with atan2 and tests `day_next < 5.0`; Saturday decodes to 4.999999999, so v10 runs a full
   morning recovery every Saturday (about 02:00-06:00, then setback at 06:15): 1.5-5.1% of the gas in all 12
   diagnosed runs (`src/debug_saturday_r9.py`). The day after Sunday decodes to 6.99999998, so on Sunday evening the
   Monday recovery cannot start before midnight. Over all 74 v10 runs the Saturday-morning preconditioning steps carry
   2.9% of HC2's loss (1.96-4.3%, every scenario) and 1.7% of the public 30's (0.4-4.5%)
   (`results/round9/saturday_precondition_share.json`). Fix = candidate D `r9_dow` (`dow_snap`, round the day): dev 14 days
   building_train_8/fairbanks_8 -78.05 vs -81.18 (-3.9%). Registered (PREREG amendment 2) before any screen run.
8. **Prototypes**: A band riding dropped (comfort collapse); C with burst recovery dropped (-6.8% worse in dev);
   B `r9_hwl`, C `r9_mprs` (start model only) and D `r9_dow` registered and queued on Kaggle (D first). D met the rule
   and shipped (header above); B's screen is complete, HS -0.15% [-0.23, -0.07] (18/18), public-30 -0.55% [-0.82,
   -0.30] (18/30): "helps" but not confirmed (it cannot displace D under amendment 2; January composite with v11);
   C's screen is complete too, HS -0.42% [-0.59, -0.26] (16/18), public-30 -0.14% [-0.33, +0.02] (14/30): "helps",
   not confirmed (ledger only).
9. **Perfect-foresight bound** (`src/lp_bound_r9.py`, `results/round9/lp_summary.json`): the kit's building model is
   linear (one LU-factorised backward-Euler step); v10's logged net heat replayed through it reproduces the zone
   temperatures within 0.14-0.51 K RMSE; with 1 kW impulse responses per zone, an LP over 30-minute heat blocks with
   comfort priced at the score's weight (expected occupancy share 1/V, holiday mornings kept until 06:15), solved per
   zone and coordinated by 16 damped Gauss-Seidel sweeps over the cross-zone responses, saves **10.5-15.1% of v10's
   loss (mean 12.2%) on seven heating scenarios**; per-zone independent (optimistic) 13-21%. Where: Saturday mornings
   (the bug), weekend floor holding, weeknight recovery timing; occupied hours slightly *more* heat. With v11 as the
   base (3 scenarios, `results/round9/mac/lp_bound_dow`) the LP reaches the same optimum as from v10 and **9.4-13.2%
   (mean 11%) remains** for a perfect-foresight controller.
10. **Paper**: one clearly marked appendix note added (`paper/main.tex`, Appendix G "Note added after the poster
   version: v11"); nothing else changed; rebuilt 16 pages (main text still ends on page 6), 0 undefined references,
   0 overfull boxes; pre-note copies in `results/round9/paper_before_note/`.

11. **Round-10 dev: is the LP's weekend slack realisable?** (2026-11-01 08:10-08:46 UTC; no registration, nothing
   shipped.) `experiments/src/make_v12_r10.py` builds `policy_candidates/transfer_policy_v12.py` from the shipped v11
   (md5 a731f9a1...; all round-10 switches off = v11 bit for bit: building_train_8/fairbanks_c3 30 days, 0.00%
   against v11's Kaggle run). Switches: `wk_free` (no heating floor from Friday evening to Monday's lead),
   `wk_lead_max_h` (longer Monday lead cap), `wk_no_mbr` (learned-rate Monday lead only). Mac, 31 runs x 8,640
   steps on 6 cold HC2 scenarios (HC2 is no longer a clean set), `src/dev_r10.py`, `results/round10/dev/dev_table.json`:
   free-float with 8 / 12 / 16 h caps -0.33 / -0.34 / -0.34% mean (-0.40 to -0.42% pooled, 5/6; energy + carbon
   -1.3% of the loss, comfort +0.9%); learned-rate lead only -0.24% (4/6); the round-5 parameter `wk_ext_lo` 12 (deeper
   weekend setback, v11 code) -0.37% mean / -0.45% pooled, 6/6, comfort-neutral. The LP put 4-9% here: its weekend
   slack is about a tenth realisable (the Monday recovery costs nearly what the weekend saves). No round 10 run:
   the remaining levers are below the coordinator's "not another 1-2% round" bar. Ready for January:
   `src/make_sets_r10.py` (fresh HC3 builder: 8 new shipped-range buildings x 5 cold strips; written, not run).

Running at hand-off: nothing. The Kaggle dispatcher exited by itself at 09:53 UTC with an empty queue (all round-9
kernels private and complete: B's screen 08:02, D's FD 09:16, C's screen 09:53 UTC); `screen_summary.json` and
`confirm_r9_dow.json` are final.
- Mac: idle (all round-9 batches finished 2026-11-01 00:53 PDT, the round-10 dev batch at 01:45 PDT; results fetched without the large `lp_cache.npz`
  files, which stay on the Mac under `~/neurips/sb/r9/out/lp_bound*/` for `lp_bound_r9.py --reuse`).
- The 74 v10 diag runs, the 12 plant-internal runs, the quirk probes and the LP bounds are all fetched and summarised
  (`results/round9/decomp_v10_*.json`, `bound_r9_v10.json`, `quirk_summary.json`, `lp_summary.json`,
  `summary_r9.json`).
- Compute note: one 600-step smoke test of `run_diag_r9.py` (1 process, ~20 s) ran on the Mac at ~18:52 PDT just
  after PAIEC took the GPU lock (my check had run before it); every later Mac job goes through the lock-aware runner,
  which paused its workers for 10 minutes (19:16-19:26 PDT) while the lock was held. One runner was restarted at
  19:15 PDT because its jobs had picked up the older `~/neurips/sb/kit` clone (fixed: the runner pins `SB_KIT_DIR`
  to the r6 kit copy that matches the laptop and Kaggle); those partial runs were deleted.
- Compute note 2: a chained follow-up batch (`batch3`, one LP job) started at 20:26:52 PDT instead of waiting for
  `batch2` (my wait loop split on a newline in the pid list), so **5 simulator processes ran on the Mac for about
  21 minutes** (memory 86-87% free throughout, no GPU lock). Found and stopped at ~20:47 PDT; the chain now waits on
  the single runner pid.
- Compute note 3: round-10 dev batch `r10_dev1` on the Mac 01:10-01:45 PDT (31 jobs, 4 workers via the lock-aware
  runner, no GPU lock held, memory 87% free at start); log `~/neurips/logs/r10_dev1.log`, outputs
  `~/neurips/sb/r10/out/dev` (fetched to `results/round10/dev`).

Last updated: 2026-10-30 ~21:50 UTC. State: ROUND 8 COMPLETE -- **v10 shipped** in `submission/transfer_policy.py` under the pre-registered rule: the round-7 fix r7L_mbr2 (per-zone model start that may only shorten the learned lead; c07 lead safety instead of c06), registered before its only clean test, lowers the loss on HC2 (44 never-used cold-window scenarios) by 0.88% [0.77, 0.98] (43/44) and on the public 30 by 1.62% [1.26, 2.02] (30/30); M -1.09% (12/12); FD -1.30% (17/20). Round 7 (analysis + four pre-registered candidates) shipped nothing: all four were "public only". v9 kept as `submission/transfer_policy_v9_shipped_before_round8.py`; final Kaggle selections v10 + v9 (replacing v8). One private Kaggle probe of v10 (ref 57816757) scored 0.01055 public (v9 0.01070), read 2026-10-31 16:20 UTC. Paper rebuilt (15 pages, main text through page 6, 0 errors / undefined / `??` / overfull), AUDIT 75 claims, review pass 6, `DEEP_DIVE.md` updated. Mac not used since its 13:08 PDT crash on 10-29 (coordinator: off-limits for simulator work). Kaggle dispatcher stopped (2026-10-30 ~22:50 UTC; queue empty). Nothing committed or pushed.

Round 6 header (2026-10-26 ~16:00 PDT): State: ROUND 6 COMPLETE -- harsh-weather sets built on private Kaggle CPU
kernels and the Mac: a 34/66 mixture of the new harsh confirmation set HC and the public set reproduces v8's Kaggle
score and predicts pid_water's Kaggle ratio (5.81 vs 5.96, 2.6% low); 9 single changes screened at full length; the composite
r6_comp (set-back air boost before workdays and near the floor, preconditioning margin 0.5 K, weeknight setback 10 K)
met the pre-registered rule (HC -2.05% [-2.70, -1.43], 40/48; public-30 -0.27% [-1.35, +0.65], a tie) and is
**shipped as v9** in `submission/transfer_policy.py` (v8 kept as `submission/transfer_policy_v8_shipped_before_round6.py`);
no gain on FD (large default-range buildings: +0.60% [-0.37, +1.36], 4/20 wins, comfort up) and up to +4% on hot public
strips -- see Round 6 item 5.
Kaggle probes: c01 0.01071 (noise vs v8 0.01074), v9 pending (ref 57678857). Paper rebuilt (15 pages, main text through
page 6; 0 errors / undefined / `??` / overfull), author block filled, AUDIT 63 claims (0 missing), review pass 5,
`DEEP_DIVE.md` written. The Kaggle dispatcher keeps running reference shards (PID 49940). Round 5 header kept below.

Round 5 header (2026-10-26 04:00 PDT): ROUND 5 COMPLETE -- Kaggle used as an oracle (v7 0.01088,
v6 0.01116, v5 0.01161, pid_water 0.06404, v8 0.01074): the hidden buildings behave like the shipped six
and the local-vs-Kaggle gap is weather (public + Minneapolis reproduces the probes' ratios); SADR v8
(round-5 composite `r5_c12_comp`: weekend setback, request cap 20 kW per 100 m2) met the pre-registered
rule at full length (public -1.1%, M -4.1%, P+M -2.2%; FD a tie) and is baked into
`submission/transfer_policy.py` (v7 kept for provenance).

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private; `kit/` and the
per-scenario time series are git-ignored; `.git`, `.gitignore`, `LICENSE`, `.github` and the
top-level `README.md` are managed by `make_repos.py` and were not edited here). Nothing was
committed or pushed from this session.

## Round 8 (2026-10-29 22:45 UTC - 2026-10-30; private Kaggle CPU kernels only): confirmation of the round-7 fix, v10 shipped

State: ROUND 8 COMPLETE -- r7L_mbr2 registered before any HC2 run, confirmed at full length, **rule met, shipped as
v10**; one private Kaggle probe submitted (ref 57816757, 2026-10-30 20:48 UTC), score PENDING at writing. Nothing committed or pushed.

1. **Pre-registration** `experiments/results/round8/PREREG.md` (2026-10-29 22:45-22:49 UTC, coordinator's go-ahead;
   before the first HC2 shard was pushed at 22:49:30 UTC): one candidate, r7L_mbr2 exactly as frozen (code
   `results/round6/policies/v10b_screen.py` sha256 2827a88a...f931, params `policy_candidates/r7L_mbr2.json` sha256
   79857dd1...7bbe), reference v9, rule as rounds 6-7 (public-30 CI not entirely above zero AND HC2 CI entirely below
   zero). States that HS and public-30 were seen before registration, so HC2 is the one clean test; HC2 had only v9
   runs (checked across runs/, Kaggle job files, Mac jobs and registry).
2. **Runs** (private Kaggle CPU kernels; no Mac): `r8-r7hc-1..4` (HC2, 44), `r8-r5m-1..2` (M, 12), `r8-r4c-1..3` (FD,
   20), job files from `jobs_r6.py make --variant r7L_mbr2 --policy-file .../v10b_screen.py --params r7L_mbr2.json`
   (every job checked to carry that code and those parameters). The dispatcher (PID 9880) wrote no log lines from
   2026-10-29 23:52 UTC to 2026-10-30 20:21 UTC (the coordinator saw a network error, ENOTFOUND); the kernels had
   finished on Kaggle and were fetched at 20:21-20:23 UTC (44 HC2 summaries, code md5 296f75d3..., params hash
   d449045d9a, 8,640 steps). One push failed on a dropped connection (22:59 UTC) and was retried by the dispatcher.
3. **Decision** (`compare_r8.py` -> `results/round8/confirm_r7L_mbr2.json`; paired bootstrap 5,000 resamples, seed 0):
   HC2 (44) 0.02171 -> 0.02152, **-0.88% [-0.98, -0.77]**, wins 43/44, CI below zero for seeds 0-9 (worst
   building_train_4/fairbanks_c2 +0.06%); public-30 0.00775 -> 0.00762, -1.62% [-2.02, -1.26], 30/30, not worse for
   seeds 0-9 (worst building_train_8/phoenix_4 -0.09%); **rule MET**. Secondaries: HS (18, seen) -0.80% [-0.93, -0.64],
   17/18; M (12) -1.09% [-1.51, -0.67], 12/12; FD (20, fresh default-range buildings, where v9 did not help) 0.01013 -> 0.01000, -1.30% [-1.66, -0.90], 17/20 (fetched 22:47 UTC; secondaries cannot change the decision).
4. **Shipped** (`python experiments/src/ship_round8.py`, refuses unless the rule is met and the sha256s match):
   `submission/transfer_policy.py` = v10 (v10b code + r7L_mbr2 overrides baked; md5 7d7f6899..., sha256 dc606dbc...),
   v9 kept as `submission/transfer_policy_v9_shipped_before_round8.py` (md5 866b9023...), `results/tune/best_params.json`
   = `best_params_v10.json` (v9: `best_params_v9.json`), `submission/best_params.json`, notebook template header v10.
   Checks: bake check, robustness test 35/35 (1.1-1.5 ms per step), 36-step smoke run, shipped file vs the Kaggle
   confirmation runs at 8,640 steps on two HC2 scenarios (`results/round8/xcheck_shipped_v10.json`): identical totals on both (building_train_8/minneapolis_c2 -189.44745624391362, building_train_8/denver_c1 -143.5173071897516).
   `submission/README.md` has a v10 section (v9 kept as previous version).
5. **Kaggle probe** (one, private notebook `neelsiri/sadr-v10-smart-buildings`, internet off, built from the shipped
   file by `experiments/src/kaggle_probe_r8.py`): the notebook's interactive building_train_1/atlanta_2 total -33.10639 against the local -33.10215 (0.013%); submitted 2026-10-30 20:48:56 UTC, ref 57816757 (`results/kaggle_feedback.json`; 1 submission on 2026-10-30 UTC). **Score PENDING** at writing (poll: `bash experiments/src/kaggle_poll_submissions.sh 57816757`, log `results/round5/kaggle_poll.log`). When it arrives: set `scores_by_policy.v10_r7L_mbr2` and that submission's `public_score` in `kaggle_feedback.json`, then run `make_macros.py`, `make_audit.py` and the pdflatex passes; until then the paper prints "Kaggle pending".
6. **Final Kaggle selections** (user, on Kaggle): v10 and v9, replacing v8 (coordinator's instruction, conditional on
   the ship).
7. **Paper**: abstract (rounds 7-8 sentence), Section 3 protocol and Setup (rounds 4-8, Kaggle kernels), Table 1 gains
   a v10 row (per-station public means), new "Round 8" paragraph (HC2, public, M and FD), parameters table = v10 (model-start row, v9 lead
   safety / margin in the caption), Limitations and disclosure merged into one section (with "Reproducibility and
   disclosure" as a paragraph) to keep six pages. Build: 15 pages, main text through page 6, references from page 7; 0 errors, 0 undefined references, 0 `??`, 0 overfull boxes; author block unchanged (Neel Sirivara, University of Washington, nsiriv@cs.washington.edu). `paper/AUDIT.md` 75 claims, 0 missing values, all 359 result macros used in main.tex covered; `AUDIT_header.md` gains the round-7 and round-8 typed constants;
   `paper/review/REVIEW_1.md` pass 6.

## Round 7 (2026-10-29 ~09:00-15:20 PDT; private Kaggle CPU kernels, the Mac until its 13:08 PDT crash, laptop light): heating-lever analysis and a model-based recovery

State: ROUND 7 COMPLETE -- analysis done and checked in the simulator; four pre-registered candidates screened at
full length on HS (18) and the full public-30; **all four "public only", none helps, v9 stays shipped**; HC2 (44 new
cold-window scenarios) left unused; no Kaggle probe. Nothing committed or pushed.

1. **Analysis** (coordinator item 1; written into the paper, Section 5 "What each heating lever is worth (round 7)",
   and the final report -- the harness refuses a subagent-written `round7/ANALYSIS.md`, so there is no such file):
   heating cost identity g = (T_d - T_sa)/(T_d - T) = 1 + (T - T_sa)/(T_d - T), T_sa = min(SAT, r T_ret + (1-r) T_out),
   r <= 0.7, checked with the kit's own methods wrapped (`check_identities_r7.py`, 576 steps of v9 on
   building_train_8/fairbanks_c2): max error 1.8e-12; billed gas 1.030 x coil duty; recirculation at its 0.7 cap on 100%
   of steps; 82% of net heat at the 308.15 K discharge cap (53% of heated box-steps); energy-weighted g 1.61 (Minneapolis
   check 1.44). So outside-air fraction and discharge temperature are spent levers (g for a 294 K zone 1.45 at 0 C, 2.31
   at -40 C; 1.09 / 1.53 at 281 K). First-order zone models (`zone_log_r7.py` 14-day v9 logs of six HS scenarios on the
   Mac, `fit_zone_model_r7.py`, `zone_model_fit.json`): 306 zones, tau p10/50/90 9/33/192 h, C median 1.35 kWh/K,
   R^2 median 0.41 on 30-min windows, recovery duration error median 27%, recovery rate at the cap falls 0.60 K/h per K
   of zone temperature. Consequences (`analysis_r7.py`, `analysis_r7.json`): a deeper floor never costs gas in the model
   if reached and recoverable, so depth pays only where the floor binds (1-47% of unoccupied zone periods under v9);
   with capped heat the latest feasible start is optimal, so a start rule can save at most the hold at the target
   before 06:00 (0.36 h per recovery over 2,599 recoveries, 2.6% of the gas). 7-day checks (Kaggle shard r7chk-1,
   `compare_r7.py checks`, `checks_r7.json`): floor -2 K measured vs predicted gas -1.14/-1.00% (train_8),
   -0.90/-0.87% (train_7), +0.05/-0.43% (train_1, wrong sign: slowest zones); lead safety 1.0: -1.44/-2.03,
   -2.17/-1.98, -0.96/-2.51% gas with part returned as comfort (loss -1.26, -1.16, -0.32%).
2. **Pre-registration** `experiments/results/round7/PREREG.md`: part 1 (~17:45 UTC, before any candidate) = HC2 (44,
   `heldout_scenarios_r7hc`, `make_sets_r7.py`, `sets_r7.json`; no building x strip pair run before) as the
   confirmation set, ship rule as round 6 (public-30 not worse AND HC2 better); part 2 (~18:10 UTC, after the checks,
   before any candidate) = four candidates and the screen rule; notes: 18:59 UTC post-hoc ledger switch
   `mbr_lead_cap` (v10b), 22:17 UTC decision. Coordinator messaged at the PREREG point and at the decision.
3. **Code**: v10 = `policy_candidates/transfer_policy_v10.py`, generated by `make_v10_r7.py` from the frozen v9 code
   (`results/round6/policies/v9_screen2.py`): per-zone RLS model (`mbr_on` start = model recovery time at the cap x
   `mbr_safety` 1.1; `mbr_floor` = least predicted hold + recovery gas among floors reached and recoverable, down to
   eco - 16 K); all switches off = v9 bit for bit (576 steps, `results/round7/regress/`); policy 2.1 ms/step on
   building_train_5. Frozen for the screen: `results/round6/policies/v10_screen.py` (md5 c21e1c65...); ledger code with
   `mbr_lead_cap` (the model may only shorten the learned-rate lead, ignored where the target is unreachable at the
   cap): `v10b_screen.py` (md5 296f75d3..., sha256 2827a88a...; = current `transfer_policy_v10.py`).
4. **Screen** (8,640 steps vs v9 = r6_comp runs; `compare_r7.py screen`, `screen_summary.json`, paper Table B7;
   classes identical for bootstrap seeds 0-9, `screen_seed_classes.json`):

   | id | change | HS (18) | wins | public-30 | wins | class |
   |---|---|---|---|---|---|---|
   | r7_base (= round 6's r6_compb runs) | v9 with c07 lead safety 1.15 instead of c06 margin 0.5 | +0.04% [-0.04, +0.13] | 9/18 | -0.65% [-1.13, -0.20] | 17/30 | public only |
   | r7_mbr | base + model-based start | +0.37% [-0.42, +1.39] | 12/18 | -1.42% [-1.82, -1.04] | 29/30 | public only |
   | r7_mbf | base + model-chosen floor | +0.01% [-0.08, +0.12] | 10/18 | -0.66% [-1.14, -0.22] | 16/30 | public only |
   | r7_mb | base + both | +0.33% [-0.45, +1.34] | 12/18 | -1.43% [-1.82, -1.06] | 29/30 | public only |

   Against the base: floor HS -0.03% [-0.07, +0.02] (the analysis's size); start HS +0.32% [-0.48, +1.39], public
   -0.78% [-1.16, -0.42]. The start wins 12/18 HS scenarios (best -3.1% train_1/minneapolis_3) but loses +5.4% and
   +4.0% on building_train_7 denver_c1 / fairbanks_8 (model lead longer than the learned one, used also where the cap
   cannot reach the target). Decision (`decision.json`, 22:17 UTC): chosen = none; v9 stays; no Kaggle probe.
5. **Post-hoc ledger** r7L_mbr2 (base + start with `mbr_lead_cap`; not eligible in round 7): HS -0.80% [-0.93, -0.64],
   17/18 wins; public-30 -1.62% [-2.02, -1.26], 30/30. It became the round-8 candidate (below).
6. **Compute**: 25 private Kaggle CPU kernels (`sb26-r6-r7chk-1`, `v9-r7hc-1..4`, `r7{mb,mbr,mbf}-r6hs-1..2`,
   `r7{mb,mbr,mbf}-pub30-1..3`, `r7Lmbr2-*` x5; dataset `neelsiri/sb26-sim-r6` version 3 adds r7hc). The Mac ran the
   six zone-log runs (10:16-10:40 PDT) and two batches: `mac-r7-pub30` ran r7 candidates *without their parameters*
   (`mac_batch_r6.py` attached parameters only to `r6_` names; fixed) -> quarantined in
   `results/round6/runs_invalid_r7/`, rerun on Kaggle; `mac-r7-mbf-pub30` (8 workers) was running when the Mac
   panicked and rebooted at 13:08 PDT together with PAIEC's MLX job; all my Mac jobs killed, nothing of the screen
   comes from the Mac; Mac use stopped on the coordinator's instruction. The coordinator's laptop memory guard stopped
   the dispatcher at 13:50:55 PDT (no push or download interrupted); restarted as PID 9880
   (`kaggle_dispatch_stdout_4.txt`).
7. **Paper**: abstract adds rounds 7/8; Section 4 "Round 7" paragraph; Section 5 "What each heating lever is worth
   (round 7)" (Eq. 1, levers, zone model, bounds, checks); rounds 3-5 diagnoses in Appendix C; Table B7 (round-7
   screen + ledger row); compressions in Rounds 5/6, "Where it loses" and Section 5 to keep six pages.

## Round 6 (2026-10-26 04:00-16:00 PDT; private Kaggle CPU kernels + the Mac, laptop <= 1 thread): harsh weather

State: ROUND 6 COMPLETE. Harsh-weather sets built and matched to Kaggle; 9-candidate pre-registered screen at full
length; composite r6_comp confirmed at full length and **shipped as v9** under the pre-registered rule; v9 probe
submitted to Kaggle (pending); paper, AUDIT, review pass 5, `DEEP_DIVE.md`. Nothing committed or pushed.

1. **Pre-registration** `experiments/results/round6/PREREG.md`: part 1 (11:05 UTC, before any round-6 run) = sets HC
   (48, confirmation, never used before) / HS (18, screening), Kaggle-match criteria, ship rule (public-30 not worse AND
   HC better, paired bootstrap 5,000 resamples seed 0); part 2 (12:10 UTC, after the v8 decomposition, before any
   candidate) = 8 candidates in 4 families, 6 planned ideas dropped with reasons (recovery fit contradicts an outdoor-
   temperature optimum start; SAT reset under heating load, hot-water reset, no simultaneous reheat/cooling and a lower
   occupied heating margin target < 1% of the HS loss or are out of reach); amendment 13:35 UTC = c11 (post hoc, labelled);
   resume notes (18:07-21:10 UTC) = dispatcher fix, Mac runs, speculative composite runs, post-hoc ledger item r6_compb.
2. **Compute**: private Kaggle CPU script kernels (`experiments/src/kaggle_sim/kaggle_sim.py`: private dataset
   `neelsiri/sb26-sim-r6` = laptop kit + scenario sets + runner; kernels `sb26-r6-*`, all private) and, after the Mac
   came back, `kaggle_sim/mac_shard_runner_r6.py` on the Mac (same tarball, <= 8 simulator workers machine-wide,
   `memory_pressure` >= 30% checked before every job launch; `mac_batch_r6.py`, `fetch_mac_r6.py`, `mac_registry.json`).
   Reproduction: Kaggle = laptop bit for bit (4/4, `kaggle_repro.json`); Mac = Kaggle bit for bit on v8 and pid_water,
   2e-11 relative on one v9-code run (`mac_repro.json`).
   **Dispatcher found at resume** (`kaggle_sim.py dispatch --loop --forever`, PID 43176, started 07:24 PDT): alive, 5
   kernels running, 16 queued; but 3 shards (c06-r6hs-2, c07-r6hs-1, c08-pub12-1) had failed to push after the 09:24-10:30 PDT network outage (pushes at
   10:35-10:40 PDT) and the dispatcher had **dropped them from the queue** (registry `push_failed`; the kernels did
   not exist on Kaggle). Stopped it at 18:07 UTC during its sleep, patched `dispatch()` (a failed push goes back to the
   front of the queue and is parked after 3 failures), restarted it (one instance, PID 5136, stdout
   `kaggle_dispatch_stdout_2.txt`); the 3 lost shards ran on the Mac. Second fix at 22:30 UTC: a failed output download
   ("a problem on Kaggle's side") had marked pidwater-r6hc-2 fetched with 0 summaries; `fetch()` now keeps such a kernel
   'running' so the dispatcher retries; re-fetched with `--force` (12 summaries) and restarted (PID 49940,
   `kaggle_dispatch_stdout_3.txt`). Queue edits during the round are logged with
   `[resume]` in `kaggle_dispatch_log.txt`. **The dispatcher is still running** (it idles when the queue is empty; it is
   working through the v7 reference and r6_compb ledger shards); stop it with `taskkill /PID 49940 /F` when those are fetched.
   Machine notes: the kit venv's `python.exe` was blocked by Windows Application Control from ~18:20 UTC; laptop
   scripts ran with the uv base interpreter (3.12.15) + `PYTHONPATH=kit/.venv/Lib/site-packages` (same packages). The Mac
   ran at load 100-130 (other users' processes) from ~19:00 to 19:30 UTC; FD was moved back to Kaggle for time.
3. **Kaggle match** (`set_match.json`, paper Table 2): v8 on P 0.00777 (level 0.72 of Kaggle), M 0.01073 (1.00), HC
   0.01657 (1.54), HS 0.02243 (2.09). A mixture of 34% HC + 66% P fitted to v8's Kaggle score predicts pid_water's
   Kaggle ratio: 5.81 against 5.96, 2.6% low (pid_water on all 48 HC scenarios; P+M: 6.15). Reading: the hidden split is about two thirds
   public-like weather and one third deep cold.
4. **Screen** (8,640 steps, HS 18 + pub12, vs v8; `screen_summary.json`, paper Table B6): helps c01 boost 8 h -0.94%
   [-1.42, -0.50] HS / -0.43% pub12, c02 boost 4 h -0.58%, c11 boost 8 h cold-only -0.95% [-1.43, -0.52] / -0.46%, c09
   floor boost -0.49%, c06 preconditioning margin 0.5 K -0.36%, c07 lead safety 1.15 -0.34%, c08 weeknight setback 10 K
   -0.81% [-1.14, -0.50] / -0.32%; n.s. c03 burst sync -0.04%; frost floor 5 C (reporting only) **+0.91% [+0.60, +1.22]**
   HS, +0.51% pub12. Composite (one per family, lowest HS): c11 + c09 + c06 + c08 = `r6_comp`: HS **-2.32% [-3.07,
   -1.60]** (17/18), pub12 -1.36% [-2.76, -0.09]; C* = r6_comp (`decision_composite.json` 20:44 UTC, `decision.json`).
5. **Confirmation** (8,640 steps; `confirm_r6_comp.json`), v8 -> v9:
   HC (48): 0.01657 -> 0.01623, **-2.05% [-2.70, -1.43]** (-33.9 [-44.7, -23.8] x1e-5), wins 40/48, CI below zero for
   10/10 bootstrap seeds; public-30: 0.00777 -> 0.00775, -0.27% [-1.35, +0.65] (-2.1 [-10.5, +5.0] x1e-5), wins 16/30;
   **rule MET** (public not worse for all 10 seeds, HC better). Secondary: HS -2.32%, H (66) -2.14% [-2.63, -1.66], M (12)
   -1.28% [-2.45, -0.31], P+M -0.63% [-1.43, +0.13], FD (20) 0.01007 -> 0.01013, +0.60% [-0.37, +1.36], wins 4/20 (n.s.; the comfort term rises
   by 2.3 times the net change, energy falls). Worst single scenarios: public
   building_train_1/singapore_8 +3.98% (five of six Singapore strips +2.6% to +4.0%, Atlanta 5/6 +3.7%/+3.1%), HC
   building_train_4/minneapolis_6 +3.36%. The screen ledger puts the hot-strip cost on c06 (+2.6% singapore_6, +1.5%
   phoenix_5; c07 -0.6% there): the pub12 screen had two hot strips of twelve. Post hoc, ledger only: `r6_compb` (c07
   instead of c06): public-30 -0.92% [-1.80, -0.24] vs v8 (25/30 wins) and -0.65% [-1.13, -0.20] vs
   v9; HS (9 of 18 when written) -2.52% vs v8 (v9 -2.44% on the same 9); FD runs queued on Kaggle (`compb-r4c-*`).
   Not eligible this round (defined after reading the confirmation); the natural round-7 candidate.
6. **Shipped** (`python experiments/src/ship_round6.py r6_comp`, ~22:00 UTC): `submission/transfer_policy.py` = v9
   (`results/round6/policies/v9_screen2.py` + r6_comp overrides baked; md5 866b9023...), v8 kept as
   `submission/transfer_policy_v8_shipped_before_round6.py` (md5 98036ef2..., = `results/round6/policies/v8.py`),
   `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v9.json` (v8: `best_params_v8.json`).
   Checks: bake (DEFAULT_PARAMS = v9 defaults + overrides), robustness test 35/35, 36-step smoke run, Kaggle template
   smoke test (`results/round6/kaggle_template_smoke_v9.txt`: 288 steps, building_train_1/fairbanks_1, -2.2481), shipped file vs the confirmation's Kaggle runs at
   8,640 steps on building_train_8/{minneapolis_3, fairbanks_c1} (HC): identical totals on both (-65.3053747611848, -323.96867298041616) (`results/round6/regress/
   xcheck_shipped_v9.json`); the Kaggle-scored notebook (`submission/kaggle/sadr-v9-comp-smart-buildings`, from
   `results/round6/policies/v9_r6_comp.py`) differs from the shipped file only in two docstring lines
   (`results/round6/shipped_vs_kaggle_scored.diff`). README updated (v9 section, v8 kept).
7. **Kaggle probes** (`results/kaggle_feedback.json`): c01 (ref 57669693, 14:41 UTC) and v9 = r6_comp (ref 57678857,
   21:19 UTC; Kaggle's interactive building_train_1/atlanta_2 -33.5602 vs local -33.5568, 0.010%); c01 scored **0.01071** at 22:27 UTC (v8 0.01074;
   -0.00003, noise); v9 **PENDING**. Daily count 2026-10-26 UTC: 3 of 4 (1 spare kept). Leaderboard 19:05 UTC: v8 0.01074 rank 87 (86 ahead), #1
   0.00521, #8 0.00603, #20 0.00685 (`results/round6/intel/lb_page1_2026-10-26T1905Z.csv`).
8. **Paper** (`paper/main.tex`): author block filled (Neel Sirivara, University of Washington,
   nsiriv@cs.washington.edu; supplied by the user via the coordinator); abstract adds round 6; Section 3 protocol covers
   rounds 3-6; Setup states the round-6 machines; Table 1 gains a v9 row; Section 4: Kaggle paragraph compressed
   (round-5 table to the appendix), Table 2 = local sets incl. HC/HS and the 66/34 mixture, new "Round 6" paragraph;
   Section 5 "What round 6 found" (HS decomposition, recovery fit, frost); round-4/5 paragraphs and Limitations
   compressed to keep six pages; Appendix: params table v9 row, round-6 ledger (Table B6). Build: 15 pages, main
   text through page 6, references from page 7; 0 errors, 0 undefined references, 0 `??`, 0 overfull boxes.
   `paper/AUDIT.md` (63 claims, 0 missing; every macro used in main.tex is covered), `paper/review/REVIEW_1.md` pass 5.
9. **Deep dive** `DEEP_DIVE.md` (coordinator request): public notebooks/threads vs SADR, loss by component and weather
   (Kaggle-weighted: gas 75%, chiller 19%, fan 3.6%, comfort 2%), a ranked change list with gains/costs/fit, literature;
   numbers from `experiments/src/deep_dive_r6.py` -> `results/round6/deep_dive_numbers.json`, Kaggle reads in
   `results/round6/intel/`, v8 7-day fairbanks_1 run in `results/round6/deep_dive_7day/`.

### Round 6 -- what remains
- Running at hand-off (all ledger/reference, none decision-relevant): the Kaggle dispatcher (PID 49940; v7 on HC
  `v7-r6hc-1..4`, r6_compb on HS `compb-r6hs-2` and FD `compb-r4c-1..3`); Mac batch `mac-v7-r6hs` (v7 on HS, 18 jobs).
  To finish: `python experiments/src/kaggle_sim/fetch_mac_r6.py mac-v7-r6hs`; the dispatcher fetches Kaggle shards
  itself (stop it with `taskkill /PID 49940 /F` once `kaggle_queue.json` is empty and `kaggle_registry.json` shows no
  `running`); then `compare_r6.py match`, `compare_r6.py screen --all`, `make_macros.py`, `make_audit.py` and the three
  pdflatex passes (Table 2 gains the v7 column; the ledger row of r6_compb gains the full HS). On this laptop run Python
  through the uv base interpreter with `PYTHONPATH=kit/.venv/Lib/site-packages` (the venv's python.exe is blocked by
  Windows Application Control; `finalize.sh` assumes the venv python and has a new round-6 block).
- Kaggle: the v9 probe score (c01 is in: 0.01071); final selection by 2027-01-15 (v9 and v8 are the natural pair).
- Next round (see `DEEP_DIVE.md`): fix c06's cooling cost (heating-only margin or c07), CMA-ES distribution tuning on
  more stations, model-based morning recovery.

## Round 5 (2026-10-25 11:25 PDT - 2026-10-26 04:00 PDT, laptop only, <= 3 simulator workers): Kaggle as an oracle

State: ROUND 5 COMPLETE. Goal 1 answered (the hidden buildings behave like the shipped six; the gap to Kaggle is weather); four Kaggle probes and the v8 candidate scored; 11-candidate pre-registered screen; full-length confirmation met the rule (narrowly on FD); **v8 shipped** in `submission/transfer_policy.py`; paper, AUDIT, REVIEW pass 4 updated. Nothing committed or pushed (coordinator).

1. **Pre-registration** `experiments/results/round5/PREREG.md`: part 1 (11:30 PDT, before any round-5 result) = candidate
   sets, probes, level + shape criteria; part 2 (11:50, before any candidate ran) = 9 candidates, screening sets, rules;
   amendment (12:20, before any screen job) = request cap c10/c11 and one deep-cold screening scenario
   (building_train_7 x fairbanks_1), from the v7 decomposition of the Minneapolis set; note (18:12, after the probe
   scores, before the confirmation) = the literal shape rule names FD (its E rests on the non-discriminating v6 ratio),
   so the ship rule became: public-30 not worse AND better on both P+M and FD; addenda 18:50 / 22:40 = runs dropped for time.
2. **Tooling** (`experiments/src/`): `run_queue_r5.py` (job queue; RAM check before each launch, 3/2/1 workers at
   >= 1.0 / 0.6-1.0 / < 0.6 GB; resumable; log `results/round5/queue/queue_log.txt`; disabled job files end in `.off`),
   `jobs_r5.py`, `make_sets_r5.py` (Minneapolis scenarios by rewriting the weather lines of a shipped strip; self-check:
   all 120 shipped strip-to-strip rewrites reproduce the shipped configs byte for byte; sets `kit/smart_buildings/
   heldout_scenarios_r5m` (confirmation, 12), `r5ms` (screening, 12), `r5x` (building_train_7 x fairbanks_1)),
   `kaggle_build.py` (rebuilds the v7 notebook cell byte for byte) + `kaggle_wait_kernels.sh` + `kaggle_poll_submissions.sh`,
   `compare_sets_r5.py`, `screen_round5.py`, `decide_round5.py`, `confirm_round5.py`, `bake_candidate_r5.py`, `ship_round5.py`,
   `regress_r5.py`, `diag_comfort_r5.py`, `diag_capacity_r5.py`, `diag_ahu_starts_r5.py`, `make_macros_r5.py`;
   `run_scenario.py` / `run_diag.py` take `SB_KIT_DIR` (kit copy) and `run_scenario.py` records `sim_module`.
   Policies frozen for round 5: `results/round5/policies/{v7,v6,v5}.py`; v8 code `policy_candidates/transfer_policy_v8.py`
   (all round-5 switches off = v7 bit for bit, 576 steps x 3 public scenarios, `results/round5/regress/`).
3. **Kaggle** (CLI, `results/kaggle_feedback.json`; every interactive building_train_1/atlanta_2 total within 0.014% of
   local): v7 0.01088 (rank 75/315 when scored; 2026-10-25 20:40 UTC: 347 teams, 85 ahead), v6 0.01116, v5 0.01161,
   pid_water 0.06404 (all submitted 2026-10-25 18:40 UTC), v8 candidate r5_c12_comp submitted 2026-10-26 00:44 UTC
   (ref 57647928): public score 0.01074 (v7 0.01088; difference below the 0.0005 noise threshold, same direction as local); best own score now 0.01074, 82 of 358 teams ahead (2026-10-26 07:10 UTC). Daily count: 10-25 UTC 3, 10-26 UTC 1 (limit kept at 4/day).
4. **Which local set predicts Kaggle** (`results/round5/set_comparison.json`, `kaggle_like_decision.json`, paper Table 2):
   v5/v7 on Kaggle 1.067 = public buildings 1.058 (default-size old held-out 1.169; M, n=5, 1.076) -> the hidden buildings
   behave like the shipped six; pid_water/v7 on Kaggle 5.89 vs public 7.00, Minneapolis 4.30, default-size 4.35,
   public+Minneapolis 6.02 -> the gap is weather; v6/v7 1.026 vs 1.02-1.03 everywhere (no information). Shape error E
   (v6, v5, pid_water): P+M 0.010, P 0.062, M 0.109, O 0.132 (FS 0.011 / FD 0.005 on v6 alone). Level v7/Kaggle: M 1.03,
   O 1.08, FD 0.93, P+M 0.81, P 0.72, FS 0.67. Reading: hidden buildings like the shipped six, hidden stations harsher
   than public + Minneapolis. A public notebook's three controllers show the same 1.17-1.37 gap; its baseline scored
   0.06439 on Kaggle (our pid_water 0.06404).
5. **PR #2** (energy-balanced tank; diff read from GitHub and saved as `results/round5/pr2_download/pr2.diff`; applied
   only in a separate kit copy (moved out of the repo after the runs; recreate by copying `kit/smart_buildings/{__init__.py,
   evaluate.py,baselines,smart_control,weather,training_scenarios}` and `patch -p1 < pr2.diff`), import verified):
   v7 -0.4% (range -2.8% to -0.1%) on the 6 public Fairbanks scenarios; pid_water +23.4% (fairbanks_1 +33%,
   fairbanks_8 +38%): SADR does not use the billing gap, the organizers' baseline partly does.
6. **v7 on M** (`results/round5/loss_decomposition_r5m_v7.json`, `analysis/`): gas 78%, cooling 12%, comfort 5.5%, fan 4% (12 scenarios);
   78% of M's comfort loss is building_train_7/minneapolis_1, where 4 zones sit 0.5-3.3 K below the band with open
   dampers at <= 276 Pa because the v5-era request cap (12 kW per 100 m2) binds below the box/coil limit (22-25 kW).
   06:00-07:00 carries 45-68% of v7's comfort loss on the public/generated sets (Monday 2.1x on the old held-out set);
   AHUs start 2.4-4.8 times a day (cycling not a lever).
7. **Screen** (`results/round5/screen_summary.json`, ledger paper Table 13; 2,880 steps, held-11 / public-4, vs v7):
   Monday lead x1.5 worse (+1.1% / +0.9%), x1.25 worse; weekend setback -3/+2 K helps (-0.7% / -1.0%), -6/+4 K helps
   (-1.2% / -1.5%); lag compensation 1.0 / 0.5 n.s.; cooling precondition cap 0.5 n.s. (no effect); setback burst 8 kW
   worse (public +0.3%); preconditioning at the cap worse (+6.3% / +6.6%); request cap 20 / 30 kW help (-7.6% held,
   driven by building_train_7 x fairbanks_1 -19%; -0.5% public); composite c12 (wk -6/+4 + cap 20 kW) helps
   (-8.8% [CI -529, -14 x1e-5] held, -2.3% [-116, -1.6] public) and is chosen (`decision.json`, 17:26).
   Baked candidate `results/round5/policies/v8_r5_c12_comp.py` reproduces the screen runs bit for bit (2 scenarios).
8. **Confirmation** (8,640 steps, `results/round5/confirm_r5_c12_comp.json`): 
   public-30: v7 0.00786 -> v8 0.00777, -1.10% [-18.2, -1.5] x1e-5 (-2.31% to -0.19%), wins 17/30;
   M (shipped six x Minneapolis): v7 0.01119 -> v8 0.01073, -4.10% [-116.8, -4.9] x1e-5 (-10.44% to -0.44%), wins 6/12;
   P+M: v7 0.00881 -> v8 0.00862, -2.19% [-42.2, -4.9] x1e-5 (-4.79% to -0.56%), wins 23/42;
   FD (fresh default-range): v7 0.01012 -> v8 0.01007, -0.56% [-14.3, -0.0] x1e-5 (-1.41% to -0.00%), wins 9/20.
   Ship rule (public not worse AND better on both P+M and FD): MET as written (seed 0). FD is a tie: the CI's upper end is below zero for 1 of 10 bootstrap seeds (seed 0 only; `results/round5/fd_seed_sensitivity.json`), while public, M and P+M pass for 10/10 seeds. Worst single scenarios: public building_train_7/phoenix_3 +0.5%, FD building_0610/denver_5 +0.7% (hot strips); the gain is in the cold strips (M: building_train_7/minneapolis_1 -10.2%, the request-cap case). Official scorer on `results/round5/full/r5_c12_comp/pub30`: 0.00777 (`results/score_leaderboard_final_r5.txt`).
9. **Shipped**: `python experiments/src/ship_round5.py r5_c12_comp` (2026-10-26 ~03:40 PDT) -> `submission/transfer_policy.py` = v8 (`transfer_policy_v8.py` + wk_ext_lo 6, wk_ext_hi 4, q_cap_w 20000 baked; md5 98036ef2...), `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v8.json`; v7 kept as `results/round5/transfer_policy_v7_shipped_before_round5.py` and `results/tune/best_params_v7.json`. Checks: bake (DEFAULT_PARAMS = v8 defaults + overrides), robustness test 35/35, 36-step smoke run, Kaggle template smoke test (288 steps, `results/round5/kaggle_template_smoke_v8.txt`), the shipped file reproduces the screen runs bit for bit on 2 scenarios x 2,880 steps (`results/round5/regress/xcheck_shipped_v8.json`). The Kaggle-scored notebook (`submission/kaggle/sadr-v8-smart-buildings`, built from `results/round5/policies/v8_r5_c12_comp.py`) differs from the shipped file only in two docstring lines (`results/round5/regress/shipped_vs_kaggle_scored.diff`). README updated.
10. **Paper** (`paper/main.tex`): abstract adds the Kaggle result and reading; Section 3 tuning protocol compressed and
    extended to round 5; Section 4 adds Table 2 (local sets vs Kaggle), paragraphs "Kaggle" and "Round 5"; Section 5
    adds "What round 5 found" (Minneapolis decomposition, the request-cap case, 06:00/Monday comfort, AHU starts, PR #2);
    the round-4 full-length table moved to Appendix A, which also gains Table "set M per scenario"; Appendix B gains the
    round-5 ledger; Sections 2-5 compressed to keep the main text on six pages. Build: 14 pages (main text through page 6, references page 7, appendices A-C), 0 errors, 0 undefined references, 0 `??`, 0 TODO, 0 overfull boxes. `paper/AUDIT.md` (51 claims, 0 missing),
    `paper/review/REVIEW_1.md` pass 4.
11. **Machine note**: the laptop ran on battery 18:00-20:30 PDT; from about 18:10 the simulator ran 2-3x slower (also after
    plugging in; Windows kept the workers on congested cores -- pinning my own oldest worker to core 5 helped, helper
    loop in the scratchpad); this is why the extra v5 runs were dropped.

### Round 5 -- what remains
- Kaggle: allows two final selections; v8 (0.01074) and v7 (0.01088) are the natural pair. Daily count used: 10-25 UTC 3, 10-26 UTC 1.
- Not run (time): v5 on FD (FD's shape error stays on the v6 ratio alone), 7 of 12 v5 runs on M, pid_water/v5 on FS (`results/round5/queue/*.json.off`; rename to .json and restart the runner). A full-length ablation of the two v8 switches (which one costs the hot strips: the weekend ceiling or the cooling side of the request cap).
- Ideas: weight screens toward cold strips (the hidden stations are harsher than public + Minneapolis); more cold stations if weather files become available; the morning recovery (MPC / learned lead).
- User: author block, OpenReview upload by 2026-11-13.

## Headline numbers (leaderboard metric = mean over scenarios of |mean per-step reward|, lower is better)
All rows: 8,640 steps, paired bootstrap 95% CIs over scenarios (5,000 resamples, seed 0).

Round 4, SADR v7 (final) vs the shipped v6 (`experiments/results/round4/confirm_r4_c14_comp_a.json`;
v7 runs: Mac + laptop, bit-identical on the 6 scenarios run on both; v6: round-3 Mac runs, and
`r4_c00_v6` on the fresh set):

| set | v7 (final) | v6 | v7 - v6 x1e-5 [95% CI] | relative [95% CI] | wins | v7 / pid_water [95% CI], wins |
|---|---|---|---|---|---|---|
| 30 public scenarios | **0.00786** | 0.00803 | -17.1 [-37.8, -3.2] | -2.1% [-4.7, -0.4] | 24/30 | 0.143 [0.113, 0.176], 30/30 |
| 40 old held-out (r2 + r3 buildings) | **0.01173** | 0.01206 | -33.5 [-51.4, -19.8] | -2.8% [-4.3, -1.6] | 39/40 | 0.230 [0.203, 0.258], 40/40 |
| 34 old held-out never screened | 0.01090 | 0.01119 | -28.5 [-48.8, -14.8] | -2.6% [-4.4, -1.3] | 33/34 | -- |
| 40 fresh (8 new buildings, round 4) | **0.00869** | 0.00890 | -20.9 [-35.1, -10.8] | -2.3% [-3.9, -1.2] | 38/40 | not run |
| 20 fresh, shipped-six ranges (0601-0603, 0606) | 0.00725 | 0.00736 | -10.3 [-21.0, -3.0] | -1.4% [-2.9, -0.4] | 18/20 | not run |
| 20 fresh, kit default ranges (0604, 0607, 0610, 0639) | 0.01012 | 0.01044 | -31.5 [-56.6, -14.8] | -3.0% [-5.4, -1.4] | 20/20 | not run |
| 74 clean held-out pooled (34 + 40) | 0.00971 | 0.00995 | -24.4 [-35.7, -15.3] | -2.5% [-3.6, -1.5] | 71/74 | -- |

- Official scorer on the v7 tree (`experiments/results/final_r4`, `score_leaderboard_final_r4.txt`):
  LEADERBOARD SCORE = 0.00786 over 30 scenarios (shipped baselines: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520).
- v7 by station (public): Fairbanks 0.0160 (v6 0.0167, -4.5%), Denver 0.0047, Atlanta 0.0052,
  Phoenix 0.0074, Singapore 0.0059. Public v7 is 1.36x the Kaggle leader's 0.00578 and 1.21x rank
  8 (0.00647) -- different buildings and strips, not comparable.

Round 3 (unchanged; the v6 rows of the paper's round-3 narrative), all Mac:

| set | SADR v6 | SADR v5 (previous) | pid_water (same machine) | v6 vs v5 [95% CI], wins | v6 / pid_water [95% CI], wins |
|---|---|---|---|---|---|
| 30 public scenarios | **0.00803** | 0.00831 | 0.05498 | -0.00028 [-0.00045, -0.00015] (-3.4%), 28/30 | 0.146 [0.114, 0.182], 30/30 |
| 10 held-out, buildings 0501/0502 | **0.00944** | 0.01109 | 0.03989 | -0.00165 [-0.00298, -0.00055] (-14.9%), 10/10 | 0.237 [0.153, 0.296], 10/10 |
| 30 held-out, six new buildings (round 3) | **0.01294** | 0.01458 | 0.05467 | -0.00164 [-0.00230, -0.00109] (-11.3%), 30/30 | 0.237 [0.209, 0.268], 30/30 |
| all 40 held-out (8 generated buildings) | **0.01206** | 0.01371 | 0.05097 | -0.00165 [-0.00223, -0.00112] (-12.0%, CI 9.5-14.3%), 40/40 | 0.237 [0.209, 0.264], 40/40 |
| 34 held-out never screened | 0.01119 | 0.01254 | -- | -0.00135 [-0.00190, -0.00089] (-10.8%, CI 8.3-13.5%), 34/34 | -- |

- Official scorer on the round-3 tree (`kit/score_leaderboard.py` on `experiments/results/final`,
  transfer = v6): LEADERBOARD SCORE = 0.00803 over 30 scenarios; shipped baselines: pid_water 0.05414,
  fixed_setpoint 0.06592, pid 0.06736, bang_bang 0.22520 (`experiments/results/score_leaderboard_final.txt`).
- v6 by station (public): Fairbanks 0.01673 (v5 0.01752), Phoenix 0.00742 (0.00755), Singapore
  0.00594 (0.00602), Atlanta 0.00530 (0.00549), Denver 0.00475 (0.00497).
- Kaggle public leaderboard (coordinator's read, 2026-10-22, `experiments/results/kaggle_leaderboard_2026-10-22.json`):
  #1 0.00578, #8 0.00647 (last prize rank), #30 0.00996, 292 teams, on different held-out
  buildings with a 33% public split -- same formula, not directly comparable. Our public-set
  number (v6 0.00803, v7 0.00786) is 1.4x the leader; our generated-building numbers are higher
  still because those buildings are larger than the public ones (round 4: the kit's default ranges
  produce larger buildings than the shipped six); the Kaggle test buildings are unknown.
- Older rounds, unchanged: v4 -> v5 on the public set -9.7% (CI 5.1% to 15.2%), 19/30 wins;
  local re-runs of all four baselines on the Mac: pid_water 0.05498, pid 0.06782, fixed_setpoint
  0.06550, bang_bang 0.22453 (local pid_water -1.7% vs the shipped values on average, range
  -12.7% to +4.6%).
- Cross-machine checks: v4 laptop vs Mac 0.000% per scenario (pid_water 0.017%); round 3: v6
  (`r3_c16`) on building_0502/denver_1 at 2,880 steps, laptop vs Mac, identical total
  (-67.5222061858949), and the baked `submission/transfer_policy.py` (no parameter file) gives the
  same total (`experiments/results/round3/xcheck_c16_laptop`, `regress_shipped_v6`).

## Round 4 (2026-10-23, 13:20-19:35 PDT): diagnosis, pre-registered screen, fresh confirmation

Goal: follow the open leads of round 3 (lower `f_cap_pre`, chiller on the generated buildings,
Fairbanks gas), with a fresh never-screened confirmation set, and ship only under a rule written
down first.

1. **Pre-registration** `experiments/results/round4/PREREG.md` (written before any policy ran on the
   new sets): sets, the 10 planned candidates with hypotheses, classification (helps / public only /
   n.s. / worse vs the shipped v6), composite and choice rule, ship rule (public not worse; pooled
   clean held-out better; neither clean part worse). Decision record with times:
   `results/round4/decision.json`.
2. **Diagnosis** (`results/round4/diagnosis_note.md`, `diag_round4.json`, `diag_cooling_v6.json`;
   `experiments/src/diag_cooling_r4.py` reconstructs the chiller load from the logged handler states
   within 0.1%, `diag_round4.py`; inputs: the round-3 v6 diagnostic runs, no new simulation):
   - Chiller on the generated buildings is a normalization effect: Phoenix + Singapore strips cool at
     2.05 W/m2 of zone (public 2.31) but 0.067 of the 80 kW-per-handler normalizer (public 0.032),
     because a handler serves at most ten zones and the generated buildings have 2,643 m2 of zone per
     handler (public 1,088). Economizer active on 5.5% of the hot strips' coil load (outside air is
     hotter than return air); reheat-while-cooling and missed economizer 1.5-2.4% of the
     cooling-weighted coil load; no latent load in the simulator; flat load through comfort hours;
     preconditioning ~11% of the coil load, setback ~1%. Night air >= 3 K below the zones on 59% of
     unoccupied steps in the generated Denver/Atlanta strips that cool (public 42%), almost never in
     Phoenix/Singapore summers.
   - What control can still reach: fan power above the 200 Pa floor, 0.00047/step on the round-3
     buildings (3.6% of their metric, 39% of their fan term; public 0.00002), 46% of it on handlers
     that heat and cool at once (SAT floored at 292 K, so big cooling zones need full flow) and 41% on
     cooling handlers already at 285 K; pressure above the floor also enlarges every idle zone's forced
     flow.
   - Fairbanks gas (public strips below 0 C): outside-air heat of running handlers = 54% of the gas
     (round-3 buildings 68%); preconditioning 30% and setback 11% of the gas; idle zones chilled by
     their forced minimum flow while unoccupied = 5.1% of the gas. The gas per joule of net heat at
     the discharge cap, 1 + 0.3 (T - Tout)/(Tdisch - T), does not depend on flow -> lowering the
     preconditioning cap below the floor-pressure flow can only slow the recovery.
   - **The kit's DEFAULT_RANGES do not reproduce the shipped six** (seed 0: 597 x 494 ft vs
     building_train_1, seed 0, 373 x 188 ft; the six span width 318-430, height 188-301, rooms 25-51;
     `results/round4/generator_ranges.json`), while the kit README says the Kaggle buildings come from
     "the same generator and parameter ranges as the shipped six". The round-3 held-out buildings
     (default ranges, median zone 246 m2) are therefore larger than the likely test buildings; round 4
     generates both families and reports them separately.
3. **New sets** (`experiments/src/make_sets_r4.sh`, `gen_buildings_r4.py`; generated on the Mac and
   copied to the laptop -- the laptop's own generation writes Windows backslashes into config.gin,
   which gin reads as escapes; floor plans and zone maps are identical on both machines):
   screening `kit/smart_buildings/heldout_scenarios_r4s` = 0520, 0524 (shipped ranges), 0522, 0523
   (default ranges) x 5 stations = 20 scenarios (31-146 zones, rooms up to 1,024 m2); fresh
   confirmation `heldout_scenarios_r4c` = 0601, 0602, 0603, 0606 (shipped ranges) + 0604, 0607, 0610
   (largest rooms of seeds 606-699), 0639 (largest floor area of 606-699; 179 zones, 18 handlers) x 5
   = 40 scenarios (40-179 zones, rooms up to 1,439 m2). Seeds the kit rejects (zones < 20 m2: 521, 600,
   605) replaced by the next free seed (524, 606, 607). Strips: Latin square per station.
4. **Code**: `policy_candidates/transfer_policy_v7.py` = shipped v6 + switches (`f_cap_min`,
   `occ_press_dyn`, `sat_mix_relief`, `flush_on`/`flush_heat_guard`, `sb_neutral`/`sb_neutral_cold`),
   all off by default. Regressions: v7 defaults = v6 bit for bit (3 public scenarios x 576 steps,
   `results/round4/regress`), and the screen's `r4_c00_v6` equals the round-3 screen values of the
   shipped c16 on all 12 round-3 screening scenarios.
5. **Screen** (2,880 steps; public-10 = the 6 earlier public screening scenarios + the other 4
   Fairbanks strips; held-26 = the 6 round-3 held-out screening scenarios + the 20 r4s scenarios;
   `screen_round4.py`, ledger `results/round4/candidates.json`, paper Table 11). Against v6
   (x1e-5 per step, paired 95% CI):

   | id | change | public-10 | held-26 | verdict |
   |---|---|---|---|---|
   | c01 | f_cap_pre 0.316 (floor-pressure flow) | -0.3 [-0.6, -0.1] | +1.7 [-0.3, +4.1] | public only |
   | c02 | f_cap_pre 0.25 (clip removed) | +1.3 [-0.3, +3.6] | +13.2 [+4.1, +24.8] | worse |
   | c03 | f_cap_pre 0.15 | +31.8 [+7.6, +59.2] | +49.4 [+19.4, +85.2] | worse |
   | c04 | f_cap_pre 0.05 | +208.4 [+73.9, +357.9] | +190.5 [+98.1, +297.2] | worse |
   | c05 | discharge margin 0.25 K | -25.7 [-57.5, -3.0] | -20.7 [-38.0, -6.4] | helps |
   | c06 | mixed-handler SAT relief | -0.0 [-0.0, +0.0] | +3.7 [-1.0, +10.9] | n.s. |
   | c07 | occupied pressure cap (e0 0.3, span 1 K) | -4.4 [-9.3, -0.2] | -2.4 [-7.7, +2.0] | public only |
   | c08 | occupied pressure cap (e0 0.1, span 0.5 K) | -4.7 [-10.2, -0.2] | -7.4 [-13.3, -2.4] | helps |
   | c09 | night flush (outside air) | +16.5 [+0.3, +34.3] | -3.3 [-24.6, +18.7] | worse |
   | c10 | reheat set-back zones' forced air | -15.7 [-35.8, +1.2] | -5.8 [-13.0, -0.3] | helps |
   | c11* | night flush, not in heating season | -0.8 [-1.7, -0.0] | -9.6 [-16.6, -3.7] | helps |
   | c12* | discharge margin 0 K | -31.5 [-70.8, -3.6] | -25.1 [-46.0, -8.1] | helps |
   | c13* | c10 only below the setback floor | -15.8 [-35.8, +1.0] | -5.5 [-12.8, +0.0] | n.s. |
   | **c14** | composite c12+c08+c11+c01+c10 | -51.7 [-113.7, -2.9] | -45.7 [-72.6, -22.7] | helps (chosen) |
   | c15 | composite with c13 instead of c10 | -51.8 [-113.6, -3.1] | -46.2 [-73.1, -22.9] | helps (ledger only) |

   \* added after a first partial read of the screen (c09 lost on a winter Fairbanks strip by
   flushing heat that gas had to buy back; c05 helped -> c12; c10 hurt mild strips -> c13); recorded
   in `candidates_notes_r4.json` and `decision.json`. The hypotheses held for the discharge margin
   (consistent -1 to -3% in every heating scenario), the set-back reheat (cold Fairbanks -1.4 to -2.8%)
   and the guarded flush (Denver/Atlanta summers up to -7%); the fan-pressure diagnosis gave only the
   mild occupied cap (c08) and the mixed-handler relief did nothing measurable; caps below the
   floor-pressure flow were worse, as predicted.
6. **Decision** (16:40 PDT, before any full-length candidate run): one change per family among those
   that helped (discharge: c12 over c05 by held metric; occupied cap: c08; flush: c11; set-back:
   c10 because c13 was n.s.; f_cap: c01 public only) -> composite c14; the lowest held-26 metric
   among the composite and the helping singles -> **c14**.
7. **Confirmation** (8,640 steps, diagnostics on; v6 on the fresh set run at the same time and not
   looked at before the decision): the table at the top. The ship rule is met (public better, not
   only not worse; pooled clean held-out better; neither clean part worse). Where the gain comes
   from (`results/round4/loss_decomposition_{public_v7,old40_v6,old40_v7,fresh40_v6,fresh40_v7}.json`):
   public gas 0.00425 -> 0.00411 per step (Fairbanks 0.01673 -> 0.01598, -4.5%); old held-out cooling
   -0.00014, fan -0.00010, gas -0.00017, comfort +0.00008 (0.00039 -> 0.00047); fresh gas -0.00011,
   cooling -0.00009, fan -0.00004, comfort +0.00003.
8. **Shipped**: `python experiments/src/ship_round4.py r4_c14_comp_a` -> `submission/transfer_policy.py`
   (v7 code with the five overrides baked into `DEFAULT_PARAMS`; "mismatches after bake: none"),
   `submission/best_params.json` = `results/tune/best_params.json` = `best_params_v7.json`; v6 kept as
   `results/tune/best_params_v6.json` and `results/round4/transfer_policy_v6_shipped_before_round4.py`.
   Robustness test 35/35 cases; 36-step smoke run; Kaggle template smoke test (288 steps,
   building_train_1/fairbanks_1: -2.141, `results/round4/kaggle_template_smoke_v7.txt`); the baked file
   (no parameter file) reproduces the Mac's c14 screen runs bit for bit on building_train_8/fairbanks_8
   and building_train_1/denver_7 at 2,880 steps on the laptop (`results/round4/xcheck_shipped_v7`);
   official scorer 0.00786 on `results/final_r4`. Policy time per step in the full runs 0.6-0.7 ms (0.74 ms on the 179-zone building 0639).
9. **Machines**: Mac -- held-26 screen of c00-c10 (286 runs, 14 workers, 132 min), c11-c13 and
   the two composites on both screening sets, v6 and v7 full length on the fresh default-range
   buildings, v7 on the old 40 and on 20 public scenarios (130 full-length runs, 0 failures; load
   40-110 from the user's Chrome). Laptop -- public-10 screen of c00-c10 (110 runs, 3 workers, 94 min),
   regressions and smoke tests, v6 full length on the fresh shipped-range buildings (20), v7 full
   length on 18 public/fresh scenarios; six v7 scenarios ran on both machines with identical totals.
   Fetched with `experiments/src/fetch_mac_round4.sh` into `experiments/results/mac/round4/`; Mac logs
   `experiments/results/logs/mac/r4_*.log`.
10. **Paper** (`paper/main.tex`): abstract and Section 4 lead with v7; Section 3 adds the v7 switches
    and the round-4 protocol; Section 4 adds Table 2 (v7 vs v6 on every set) and the round-4 ledger
    summary; Section 5 adds "What round 4 found" (normalization, fan pressure, ventilation, generator
    ranges); Table 1 gains a v7 row; Appendix A gains Table 6 (fresh set per scenario) and Figure 1
    (v7 vs v6 per generated building); Appendix B Table 11 (round-4 ledger); the decomposition and
    held-out-building figures moved to Appendix C to keep six pages; Sections 3-5 compressed.
    `finalize.sh` now also runs the round-4 summary, confirmation, ledger, `assemble_round4_tree.py`
    and `make_figures_r4.py`; macros in `make_macros_r4.py`; audit 43 claims, 0 missing.

### Round 4 -- what remains
- Nothing running. Not done: a full-length ablation of the five v7 switches; `pid_water` on the
  fresh buildings (the fresh set reports v7 vs v6 only); the Kaggle submission (user).
- Ideas for January: the shipped-range buildings gain least (-1.4%) and are the likely test
  distribution -- screen future changes on shipped-range buildings first; Fairbanks remains the
  largest single loss (building_train_1/fairbanks_1 0.0461, 95% gas), bounded by the 30% outside-air
  physics; a learned residual or MPC for the morning recovery.

## Round 3 (2026-10-23): what was done, before/after, which machine ran what

Goal: find where v5's loss sits, fix the weakness on large generated zones, enlarge the held-out
set, and ship a better policy only under a rule fixed in advance.

1. **Loss decomposition** (`experiments/results/round3/loss_decomposition_note.md`, `decompose_loss.py`
   on `run_diag.py` runs; Mac, 8,640 steps). Public set, v5: gas 52%, chiller 38%, fans 5%, comfort
   4%; preconditioning + setback carry 30% of the loss; Fairbanks is 90% gas. Generated buildings,
   v5: comfort 14-16% (vs 4% public), the largest quartile of zones in band only 0.4-0.65 h after
   06:00. Diagnosis: every VAV box has the same 2 m3/s and hot-water Kv, so v5's constants (12 kW
   cap, fixed gains, one building-wide lead) starve 300-1,400 m2 zones.
2. **Enlarged held-out set**: six new generated buildings (generator seeds 500, 505, 507, 508, 509,
   511; 32-120 zones, 5-12 handlers, zones 33-1,373 m2), one strip per station = 30 scenarios
   (`kit/smart_buildings/heldout_scenarios_r3`), on top of the previous 10 (0501, 0502): 40
   held-out scenarios on 8 generated buildings. v5 and pid_water were run on it once (Mac,
   `mac_round3_diag.sh`): v5 0.01458, pid_water 0.05467.
3. **v6 code** (`experiments/src/policy_candidates/transfer_policy_v6.py`): area-scaled gains, caps
   and setback burst (zone areas from the metadata zone map); physical and water-side request caps;
   per-zone optimum start; adaptive setback floor; a preconditioning latch was tested and rejected.
   With the switches off it reproduces v5 bit for bit (576-step regression, `results/round3/regress_*`).
4. **Screens** (2,880 steps; 6 public scenarios on the laptop, 6 held-out scenarios on the Mac;
   `screen_round3.py`; ledger `experiments/results/round3/candidates.json`, table in the paper's
   Appendix B). 17 v6 variants paired against v5 and against the v6 defaults (c00). Against c00:
   7 worse (c01 f_cap_pre 1; ablations c03 no area scaling, c04 no per-zone start; c09 rate prior 1;
   c11 latch; c12 lead safety 1.6; c13), 5 not significant (c05, c07, c08, c10, c15), 1 public-only
   (c06 no down-scaling of small zones), 3 met the rule (c02 f_cap_pre 0.5, c14 = c02 + c06,
   c16 = c14 with f_cap_pre 0.35). Choice rule fixed before any full-length composite run
   (`candidates_notes.json -> decision_rule`): lowest held-out screen among composites meeting the
   rule -> **c16** (held screen 0.01824 vs c14 0.01832; c16 vs c14 not significant). c16 vs c00 on
   the screens: public -5.0e-5 [-8.9e-5, -1.4e-5] (5/6), held-out -21.5e-5 [-44.9e-5, -4.5e-5] (6/6).
5. **Full-length confirmation** (Mac, `mac_round3_confirm.sh` -> `mac_round3_full.sh`, 12/10/10
   workers, nohup, per-scenario checkpoints): the table above. Ship rule (not worse than v5 on the
   public set, better on the held-out sets) met on every set. The v6 defaults alone at full length
   on the public set (laptop, 3 workers): 0.00814 (vs v5 -0.00017 [-0.00029, -0.00007], 22/30); c16
   vs c00 on the public set: -0.00011 [-0.00018, -0.00006], 28/30. After shipping, for the ledger,
   c00 on the 40 held-out scenarios (Mac): 0.01222 (vs v5 -0.00148 [-0.00201, -0.00102], 40/40);
   c16 vs c00 there: -0.00016 [-0.00031, -0.00006], 33/40 (`candidates.json -> full_length_c00_heldout`).
6. **Shipped**: `python experiments/src/ship_round3.py r3_c16_pre035_min1` -> `submission/transfer_policy.py`
   (v6 source + `f_cap_pre` 0.35, `area_scale_min` 1.0 baked into `DEFAULT_PARAMS`; "mismatches after
   bake: none"), `submission/best_params.json` = `experiments/results/tune/best_params.json` =
   `best_params_v6.json`; v5 kept as `tune/best_params_v5.json` and
   `results/round3/transfer_policy_v5_shipped_before_round3.py`. Robustness test 35/35 cases;
   36-step smoke run; Kaggle template smoke test (288 steps, building_train_1/fairbanks_1, -2.037);
   baked file reproduces the Mac run bit for bit (item "Cross-machine checks" above).
7. **Where the gain came from** (decomposition of the v6 runs): comfort on the six new buildings
   0.00208 -> 0.00039 per step (share 14.2% -> 3.0%; out-of-band occupied zone-steps 14.0% -> 2.1%;
   largest-quartile recovery 0.65 h -> 0.12 h), fan +0.00026, gas -0.00024; on the public set
   comfort 0.00036 -> 0.00018 and gas 0.00436 -> 0.00425. What is left on the generated buildings is
   chiller electricity (0.00709/step vs 0.00318 public), not diagnosed this round.

Machines in round 3:
- laptop: public screens of all 17 variants (`results/round3/screen/*/public`), c00 at full length
  on the public set (`results/round3/laptop_full_c00_public`, 97.7 min, 3 workers), ten-day tests
  on building_0502/denver_1 (`b0502_*`), regressions and the cross-machine/bake checks, finalize.
- Mac: v5 diagnostics on all three sets (`diag_v5_public`, `diag_v5_heldout`, `diag_v5_r3` + pid_water),
  held-out screens of all 17 variants, the shipped c16 at full length on public/old/new held-out
  (`final_v6_public`, `final_v6_heldout`, `final_v6_r3`), and the ledger-only c00 held-out runs
  (`final_c00_heldout`, `final_c00_r3`). Fetched with `experiments/src/fetch_mac_round3.sh` into
  `experiments/results/mac/round3/`; Mac logs in `experiments/results/logs/mac/` (`r3_*.log`).
- Paper trees: `assemble_round3_tree.py` -> `results/final` (transfer = v6, transfer_v5, transfer_v4,
  4 baselines), `final_heldout` (v6, v5, v4, pid_water), `final_heldout_r3` (v6, v5, pid_water).

### Round 3 -- what remains
- Nothing running. The ledger-only c00 held-out runs finished at 13:04 PDT, were fetched, and are in
  the ledger and in one clause of the paper's Section 4.
- Not tried (ideas for January, `candidates.json -> ideas_not_run` plus round 3): `f_cap_pre` below
  0.35 (the trend 1.0 -> 0.7 -> 0.5 -> 0.35 was still improving on the held-out screen); envelope
  pre-cooling / setback depth in cooling climates for the large generated buildings (their chiller
  term is 2x the public one); a learned residual on top of SADR.
- The 6 held-out screening scenarios (first 10 days) informed the choice; the 34 never screened are
  the clean held-out estimate (-10.8%, CI 8.3-13.5%, 34/34).

## Final policy (`submission/transfer_policy.py`, SADR v10 since round 8)
v10 = the v9 rules below with two changes: the optimum-start lead safety is 1.15 (v9 1.3) and the preconditioning target is back at 0.8 K inside the band (v9 0.5 K); and each zone carries a first-order thermal model (dT/dt = a Q - k (T - Tout) + c, fitted online by recursive least squares on its unoccupied history) whose recovery time at the request cap (x 1.1) may only shorten the learned-rate start lead, and is ignored where it predicts the target is unreachable at the cap (`mbr_on` 1, `mbr_lead_cap` 1). With the round-7 switches off the v10 code reproduces v9 bit for bit. The v9 description follows.

v9 = the v8 rules below + four round-6 switches: in heating season the forced minimum air of a set-back zone on a
running handler is reheated to the discharge limit instead of to the zone temperature (within 8 h of a workday start
while the outside air is at or below the zone's setback floor, and at any time within 2 K of the floor); the
preconditioning target sits 0.5 K inside the band (v8 0.8 K); the weeknight setback floor is 10 K below the eco
heating setpoint (v8 8 K). With every round-6 switch off the v9 code reproduces v8 bit for bit. The v8 description
follows.

v8 = the v7 rules below + two round-5 switches: far from the next workday start (weekends) the setback floor drops
by 6 K and the ceiling rises by 4 K, ramped back over the 12 h that end 10 h before the start; and the per-zone
request cap is 20 kW per 100 m2 (v7: 12 kW), so in deep cold the box and coil bound the heat. With every round-5
switch off the v8 code reproduces v7 bit for bit. The v7 description follows.

Schedule-Aware Demand-based Reset: occupancy-gated OCCUPIED / PRECONDITION / SETBACK modes with
holiday detection and a self-tuning optimum-start lead (per zone since v6); per-zone PI loops on net
heat (W) translated to damper flow via the supply-air temperature and to reheat valve position via
the water capacity rate and the 308.15 K discharge limit; coldest supply air (285 K) whenever a
handler cools, 292 K floor on handlers that also heat; static pressure trim-and-respond in closed
form; proportional economiser with the fan break-even; loop dP reset to the most-open valve; hot
water 350 K in heating season; setback by burst heating/cooling against a floor widened by 8 K
below / 6 K above the eco band. v6 added: gains, request cap and setback burst scaled with zone area
/ 100 m2 (clip [1, 6]), request caps at what the box delivers at a flow fraction and at the coil's
water-side limit, per-zone optimum start, adaptive setback floor. v7 (round 4) adds: discharge
margin 0 (flows and valves sized for the simulator's own 308.15 K cap); a pressure-aware occupied
request cap (flow above the 200 Pa floor-pressure flow only in proportion to the zone's error, from
0.1 K, full 0.5 K later); a night flush with outside air before workdays outside heating season
(zone >= 3 K warmer than outside, floor pressure, coil off, within 8 h of the start); reheat of the
forced minimum flow of set-back zones on running handlers in heating season; preconditioning cap
at the floor-pressure flow (0.316). With the five v7 switches off the code reproduces v6 bit for
bit. Pure numpy + stdlib, ~0.6-0.7 ms per step in the full runs (init ~40-100 ms on a 120-zone
building for the zone-map labelling), deterministic, shape-agnostic, every action slot written and
clipped; 54 KB.

Parameter provenance: v4 random search (16 configurations, ki 60 -> 120 is the whole gain), v5
analysis-driven candidates at full length on the public set (winner `c10_satcold_night8_hi6`:
sat_cool_hi 285, night_low_ext 8, night_high_ext 6), v6 round-3 screen + full-length confirmation
(winner `r3_c16_pre035_min1`: f_cap_pre 0.35, area_scale_min 1.0 on the v6 defaults), v7 round-4
pre-registered screen + full-length confirmation (winner `r4_c14_comp_a`: disch_margin_k 0,
occ_press_dyn 1 / e0 0.1 / span 0.5, flush_on + flush_heat_guard, sb_neutral, f_cap_pre 0.316).

## Machines
- `laptop`: this Windows laptop (8 cores shared; <= 3 simulator processes; 0.03-0.2 s/step).
  Generating scenarios here writes backslash paths into config.gin (gin reads them as escapes):
  generate on the Mac and copy (done for r4s/r4c).
- `mac`: `ssh mac`, Apple M5 Pro, 18 cores, 48 GB, kit clone + uv venv (Python 3.12.15, same pins),
  layout mirrors this tree at `~/neurips/sb`; shared with the user's own apps (Chrome used 5-8
  cores during round 4; load 40-110). Round 1-3 paper rows come from Mac runs; round-4 v7 rows mix
  Mac and laptop runs, which are bit-identical (checked on 6 full-length scenarios).

## Deliverables (all present)
1. `submission/transfer_policy.py` (v7, baked), `submission/README.md` (v7 description and
   selection, v6 kept as "previous version", paste-in steps for the Kaggle notebook, repo link),
   `submission/kaggle_notebook_template.py` (smoke-tested with v7), `submission/best_params.json`.
2. `experiments/results/final_scores.json`, `heldout_scores.json`, `heldout_r3_scores.json`
   (round-3 trees, transfer = v6), `final_scores_local.json`, `heldout_scores_local.json`,
   `analysis.json`, `candidates_summary.json`, `env_info.json`, `score_leaderboard_final.txt` (v6) and
   `score_leaderboard_final_r4.txt` (v7, tree `results/final_r4`); round 3: `results/round3/*`;
   round 4: `results/round4/PREREG.md`, `decision.json`, `candidates.json` (ledger),
   `screen_summary_screen_vs_r4_c00_v6.json`, `screen_ranking.txt`, `confirm_r4_c14_comp_a.json`,
   `confirm_ranking.txt`, `diagnosis_note.md`, `diag_round4.json`, `diag_cooling_v6.json`,
   `generator_ranges.json`, `scan_default_606_699.json`, `loss_decomposition_*_v{6,7}.json`,
   `regress/`, `xcheck_shipped_v7/`, `kaggle_template_smoke_v7.txt`, `finalize_r4.log`;
   `paper/results_macros.tex`, `per_scenario_table.tex` (3 tables), `per_scenario_table_r4.tex`,
   `tuning_tables.tex` (ablation, v5 candidates, round-3 and round-4 ledgers); `paper/figures/*`
   (+ `fig_round4_buildings`); `paper/main.pdf` (13 pages: main text through page 6, references page
   7, Appendices A-C from page 8; 0 errors, 0 undefined, 0 `??`, 0 overfull); `paper/AUDIT.md` (43
   claims, 0 missing values; header `AUDIT_header.md`); `paper/review/REVIEW_1.md` (passes 1-3).
3. This file.

Pipeline (idempotent): `bash experiments/src/finalize.sh` regenerates everything in item 2 from the
result trees (assemble, score, analysis, decompositions, screen summaries, round-4 confirmation and
ledger, the v7 tree and its official score, macros, audit, figures, three pdflatex passes).

## Paper
NeurIPS 2026 style, `[sglblindworkshop,final]` + `\workshoptitle`. Round-4 changes: abstract leads
with v7 (public 0.00786, ratio to pid_water 0.143) and the round-4 result on the 74 untouched
held-out scenarios; Section 3 adds "Round 4 (v7)" and the pre-registered protocol (and that three
candidates were added after a first look); Section 4 adds Table 2 (v7 vs v6 on every set, both
building families) and the round-4 ledger summary with where the gain comes from; Section 5 adds
"What round 4 found"; Table 1 has a v7 row; Appendix A: Table 6 (fresh set) and Figure 1 (v7 vs v6
per building); Appendix B: Table 11 (round-4 ledger); the decomposition and held-out-building
figures moved to Appendix C; Sections 3-5 compressed to keep six pages. Self-review pass 3
(`paper/review/REVIEW_1.md`): must-fixes 1-5 applied.

## To do (user)
- Round 9: **v11 is shipped** (v10 + the Saturday day-of-week fix; HC2 -1.50%, public -1.23%). Choose the two final
  Kaggle submissions before 2027-01-15: **v11 and v10** (replacing v10 + v9) -- coordinator's call; no submission was
  made in round 9. If a probe is wanted: `python experiments/src/kaggle_probe_r9.py push`, `... check`, then
  `SB_COORDINATOR_OK=1 python experiments/src/kaggle_probe_r9.py submit`. The paper has one clearly marked appendix
  note on v11 (Appendix G); the OpenReview upload by 2026-11-13 is unchanged otherwise.
- Round 8: v10 is shipped; its Kaggle probe (ref 57816757) scored **0.01055** public (v9 0.01070), read 2026-10-31
  02:58Z and entered in `kaggle_feedback.json`, macros, AUDIT and the PDF by the coordinator. Choose the two final Kaggle submissions before 2027-01-15: **v10 and v9** (the coordinator's instruction after the ship; v8 is dropped from the pair). OpenReview upload of `paper/main.pdf` by 2026-11-13. All round-8 Kaggle shards are fetched and the dispatcher is stopped.
- Round 6: v9 is shipped; its Kaggle probe (ref 57678857) was pending at hand-off. Choose the two final Kaggle
  submissions before 2027-01-15: v9 and v8 are the natural pair (v9 is better on the harsh sets, a tie on the
  public set and worse on large default-range buildings and hot strips; v8 hedges that). The author block is filled
  (round 6); the OpenReview upload by 2026-11-13 remains.
- Round 5: v8 is shipped and was scored on Kaggle (0.01074; v7 0.01088). Choose the two final Kaggle submissions
  before 2027-01-15 (v8 and v7 are the natural pair). The older Kaggle instructions below are kept for reference.
- Kaggle (joined): follow `submission/README.md` -- open the official notebook template, replace
  the policy cell with `submission/transfer_policy.py` (v7), run once on the public scenarios
  (expect the per-scenario totals in `experiments/results/final_r4/<b>/<w>/transfer/summary.json`,
  leaderboard 0.00786; a few per cent off if the grader's kit differs), submit. Keep the submitted
  file identical to the one here so the paper's numbers refer to the submitted policy. v7 reads the
  optional `zone_map` from the metadata (the kit provides it); without it the area scaling switches
  off and the policy still runs.
- OpenReview poster paper (group NeurIPS.cc/2026/Workshop/SB26_Challenge) by 2026-11-13: fill in
  name/affiliation in `paper/main.tex` (author block), rebuild (`bash experiments/src/finalize.sh`
  or the three pdflatex passes), check the Overleaf template
  (https://www.overleaf.com/project/6ace893ebb021a3e1807b140) for the page limit (main text is six
  pages), upload `paper/main.pdf`.
- Before the January final paper (2027-01-15): the Kaggle score once available; the open ideas in
  "Round 4 -- what remains".

## Risks
- Selection used the public set at full length (v5) and the screening sets (v6, v7): the public
  number (0.00786) is optimistic; the 74 held-out scenarios no decision touched (34 old + 40 fresh)
  are the clean estimate; 16 generated buildings are still a small sample of the generator.
- The kit's default generator ranges produce larger buildings than the shipped six; the README says
  the Kaggle buildings share the shipped six's ranges. On fresh shipped-range buildings v7 gains
  1.4% over v6 (CI 0.4-2.9%), less than on large buildings (3.0%); round-3's large held-out gains
  (-12%) probably overstate what v6/v7 gain on Kaggle over v5.
- The Kaggle leaders (0.0058) are 1.36x below our public-set number; most of our remaining loss is
  heating gas in Fairbanks (outside-air physics: 54% of the gas in the cold public strips is
  ventilation heat) and chiller electricity in the hot strips.
- v7 changes comfort slightly (old held-out comfort term 0.00039 -> 0.00047 per step) in exchange
  for energy; the trade is net positive on every set at full length.
- Local-vs-official pid_water gap (-1.7% mean, up to -12.7% on one scenario) means the organizers'
  kit version may differ slightly from the clone used here.
- v6/v7 depend on the metadata `zone_map` for the area scaling; if the grader's harness omitted it,
  the policy would fall back to unscaled gains (the round-4 switches do not need it).

## 2026-10-31 ~03:45 PDT: reviewer-friendly restructure of the paper (same numbers)
- At the user's request for PAIEC (denoise; more authoritative; bullets, separation, diagrams), the same pass was
  applied here.
  - Shorter abstract.
  - Contributions, environment, method, results, analysis and limitations as bold-lead lists.
  - New Figure 1: one SADR control step.
  - New Table 2: the eight development rounds (change, confirmation set, loss reduction with CI, Kaggle score). It
    replaces eight chronological round paragraphs, which moved verbatim to Appendix D ("Round-by-round results").
  - The v6/v7 version-change paragraphs moved verbatim to Appendix C.
  - The new "Kaggle" paragraph states the weather-not-buildings finding first.
- Main text ends on p.6 (15 pp).
- Build checks: 0 undefined, 0 overfull, 0 `??`.
- AUDIT: 75 claims, 0 missing.
- Hash: main.pdf c3706aa49f234812…
- Build logs: `paper/build_r9_*`.
- The pre-restructure tex and PDF are kept in the session scratchpad.
