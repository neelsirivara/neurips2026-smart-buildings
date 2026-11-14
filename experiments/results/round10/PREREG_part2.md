# Round 10 pre-registration

## Part 1: sets, reference and ship rule (written 2026-11-01 ~10:10 UTC, before any candidate is fixed and before any policy has run on HC3 or HH)

### What has run in round 10 before this was written
- Round-10 dev batch `r10_dev1` (2026-11-01 08:10-08:46 UTC; STATUS round 9 item 11): weekend free-float variants and
  `wk_ext_lo` 12 on six cold HC2 scenarios (`results/round10/dev/dev_table.json`). No registration, nothing shipped.
- Sets built 2026-11-01 ~10:00 UTC on the Mac (`experiments/src/make_sets_r10.py buildings / write / hot / dev`,
  kit generator only, no policy run), copied byte for byte into the Mac's r6 simulator kit and the laptop kit:
  set manifests below (`make_sets_r10.py manifest`; `results/round10/sets/manifest_r10.json`, archive
  `results/round10/sets/sets_r10.tgz`, scenario lists `results/round10/sets/sets_r10.json`).
- Code: `experiments/src/policy_candidates/transfer_policy_v12.py` (built by `make_v12_r10.py` from the shipped v11;
  round-10 switches `wk_free`, `wk_lead_max_h`, `wk_no_mbr`, `ki_c_mult`, `kq_c_mult`, all off by default), sha256
  b856cb445c9f33ebc08d92ad095a4ff4172692a913d62ea7a7960fe2e3613c6a. The round-9 switches B (`heat_season_steps`,
  `tw_ramp_k`) and C (`mpr_on`, `mpr_burst`, `mpr_safety`) and the round-5 `wk_ext_lo` are already in v11's code.
- Dev batch `dev_a` started on the Mac at 2026-11-01 10:09 UTC (3 workers): v11 on D10 (24), v12 all switches off
  on 2 D10 scenarios (bit-identity check), and three dev variants (B+E, B+E+C, cooling integral x3) on D10 + the six
  HC2 dev scenarios. Development sets only (below); nothing on HC3, HH, public-30, HS, M or FD.

### Sets
| name | n | content | use |
|---|---|---|---|
| **HC3** = `heldout_scenarios_r10hc` | 40 | 8 new buildings of the shipped family (seeds 700-706, 708; seed 707 rejected by the kit, small-room artifact) x 5 of the 10 cold Sunday-06:00 windows of rounds 6-7 (fairbanks_c1..c4, minneapolis_c1..c3, denver_c1..c3; building i gets strips (i + 2k) mod 10, every strip 4 times); never run by any policy | **primary confirmation** |
| **HH** = `heldout_scenarios_r10hh` | 40 | the same 8 buildings x 5 hot windows (phoenix_3..7, singapore_1/3/4/6/8; same Latin pattern; 20 Phoenix + 20 Singapore); never run | hot confirmation (co-primary only for a candidate with a hot-weather component, otherwise a guard) |
| P = public 30 | 30 | the shipped scenarios (seen in every round) | guard |
| HS = `heldout_scenarios_r6hs`, M = `heldout_scenarios_r5m`, FD = `heldout_scenarios_r4c` (FD_B buildings) | 18, 12, 20 | rounds 4-6 sets (seen) | secondary guards |
| D10 = `heldout_scenarios_r10dev` | 24 | the shipped six x windows the public 30 does not use (atlanta_4/7, denver_1/4, phoenix_7, singapore_2/5) | development only |
| HC2 = `heldout_scenarios_r7hc` | 44 | round 7's cold set (confirmed v10 in round 8 and v11 in round 9; not clean) | development only |

Manifests (sha256 over every file's relative path and content, `make_sets_r10.py manifest`, identical on the Mac and
the laptop): HC3 0cefe29d98f775eaac516eadb07cedca31b0331dee96e6eda421ddd919c03e85 (160 files); HH
52dea4cd821b5ec0e0783c46da456efff1aca55f4ab7b44c79be6db8dbd4a511 (160); D10
7140d5fd5c63922c988aec41b0636b72a10c7f390f3055e14fe2c64888007ee0 (96); buildings `heldout_buildings_r10`
b9c0c0708ecdaee735b5411cbef6a532d8cfaf1401bc100ca04854c03d5cefd5 (9).

Development (all round-10 tuning and the choice of the candidate) uses D10 and HC2 only. No round-10 candidate code
runs on HC3, HH, P, HS, M or FD before Part 2 is written and hashed.

### Reference
The shipped v11 (`submission/transfer_policy.py`, sha256 f9c0ad1a3be0a3983905b434a91fa7f9eca6b4fd7de1957d9c87355fc2ddb8d8).
v11 runs: HC3 and HH from the shipped file itself (Mac, r6 kit copy, 8,640 steps); P, HS, M, FD = round 9's `r9_dow`
runs (`results/round6/runs/r9_dow/<set>`, private Kaggle kernels; the shipped file reproduces them bit for bit,
`results/round9/xcheck_shipped_v11.json`, and the Mac kit reproduces the Kaggle runs bit for bit, round-10 dev
`f0_off`).

### Candidates (fixed in Part 2)
At most **one combined candidate K** = `transfer_policy_v12.py` + one parameter JSON, built from the components that
help in development (D10 + HC2 only). If K contains a hot-weather component (one that acts only while zones are
cooled, e.g. the cooling-loop gains), Part 2 may also name **one fallback K'** = K without that component. No other
candidate is confirmed in round 10.

### Ship rule
Metric per scenario: |total reward| / 8,640 (the loss, leaderboard units). Paired bootstrap of the mean per-scenario
difference (candidate - v11), 5,000 resamples, seed 0, 95% percentile CI; relative = divided by v11's set mean
(`compare_r10.py confirm`). A candidate meets the rule if all of these hold at 8,640 steps:
1. **HC3 better**: CI entirely below zero AND wins (scenarios with a lower loss than v11) >= 24 of 40 (60%).
2. **HH**: if the candidate contains a hot-weather component, HH better by the same test (CI entirely below zero AND
   wins >= 24/40); otherwise HH is a guard (rule 4).
3. **Public-30 not worse** (as rounds 6-9): CI not entirely above zero.
4. **No material regression on the guards** HH (when a guard), HS, M and FD: a set regresses materially if its CI is
   entirely above zero AND its mean relative change is above +0.20%.

Decision: K ships if it meets the rule. Otherwise, if Part 2 names K', K' ships if it meets the rule (with HH as a
guard). Otherwise v11 stays. At most one candidate ships. Reported either way: every set's mean, CI, wins, worst
scenario, and the CIs for bootstrap seeds 0-9 (HC3, HH, P).

The verdict is due by 2026-11-08 12:00 UTC; a candidate whose HC3, HH or P runs are incomplete then does not ship
(no decision on a partial primary set). If one ships it becomes v12 (`submission/transfer_policy.py`, parameters baked
as defaults, reproducing the confirmation runs bit for bit on two scenarios); v11 is kept as
`submission/transfer_policy_v11_shipped_before_round10.py`; v10 / v9 / v8 copies untouched. No Kaggle competition
submission in this round. Never in a policy or a tuning objective: the gas-billing quirk or occupancy-seed replay.

Part 2 (the candidate, its parameters and hashes) is appended after the development runs, before any confirmation run.

## Part 2a: how the candidate is chosen (written 2026-11-01 ~17:10 UTC, before the D10 rows of the last two development variants were read; no confirmation run)

Development so far (D10 + the six HC2 dev scenarios, 8,640 steps, Mac; v11 = reference; `compare_r10.py dev`,
`results/round10/dev_summary.json`): the faster cooling integral (`ki_c_mult` 3) is worse (+0.79% over 30, Singapore
+5.3%, comfort up), so round 10 has **no hot-weather component** and no K'. The hot-water setpoint ramp
(`tw_ramp_k`, part of round 9's B) is **excluded**: its saving is billed gas only (the shipped boiler bills the loop
flow at the setpoint, not at the tank temperature it reaches), i.e. it comes from the same billing approximation the
quirk uses, from the other side; and once the loop is kept hot its effect is nil (cold dev rows of the season
variants with and without the ramp are identical). The remaining components are physical: E (`wk_ext_lo` 12),
C (`mpr_on` 1, `mpr_burst` 0, `mpr_safety` 1.3) and the long heating season of B (`season_ext_steps` 2016: loop kept
hot, night-flush guard and set-back reheat for 7 days after the last heating demand), gated by the outside air
(`season_oat_k`).

Selection rule, fixed now: K = E + C + one season variant out of {gate 283.15 K (`r10_d_g10ec`), gate 288.15 K
(`r10_d_g15ec`), ungated (`r10_d_bnrec`)} -- the one with the lowest mean relative change over the 30 development
scenarios among those whose every station group (cold, denver, atlanta, phoenix, singapore) has a mean of at most
+0.05%; a variant within 0.05 percentage points of the best is preferred if its gate is lower (more conservative).
If no season variant qualifies, K = E + C (`r10_d_ec`). The cold rows of all three season variants are identical in
development (the gate is always open in the cold windows), so the choice is made on the D10 rows.

## Part 2: the candidate (written 2026-11-01 ~19:20 UTC, after all development runs, before any confirmation run)

Session note: the laptop rebooted at about 18:57 UTC. The Mac did not; dev batch `dev_c` had finished cleanly at 18:19
UTC (112/112 jobs, rc 0). No policy has run on HC3 or HH (`mac_conf_jobs_r10.py confirm` refuses otherwise, and it
passed at 19:17 UTC). No round-10 candidate has run on P, HS, M or FD.

### Development table (8,640 steps; change against v11; D10 24 + six cold HC2; `results/round10/dev_summary.json`)
| variant | contents | pooled, 95% CI, wins | cold | denver | atlanta | phoenix | singapore |
|---|---|---|---|---|---|---|---|
| `r10_d_e` | E | -0.31% [-0.64, -0.05], 10/30 | -0.37 | -0.20 | -0.00 | +0.00 | +0.00 |
| `r10_d_ec` | E + C | -0.37% [-0.74, -0.10], 20/30 | -0.48 | -0.35 | -0.11 | -0.07 | 0 |
| `r10_d_re` | E + ramp (excluded) | -0.49% [-0.89, -0.20], 23/30 | -0.63 | -0.55 | -0.12 | -0.07 | 0 |
| `r10_d_be` | round 9's B + E | -0.79% [-1.36, -0.30], 18/30 | -1.11 | -1.55 | -0.27 | -0.06 | +0.22 |
| `r10_d_bec` | round 9's B + E + C | -0.85% [-1.44, -0.33], 18/30 | -1.23 | -1.68 | -0.41 | -0.11 | +0.22 |
| `r10_d_bhe` | loop hold only, gate 283.15 K, ramp, E | -0.84% [-1.36, -0.41], 23/30 | -1.11 | -1.17 | -0.41 | -0.07 | 0 |
| `r10_d_g10ec` | season, gate 283.15 K, E + C | -0.89% [-1.44, -0.43], 21/30 | -1.23 | -1.29 | -0.48 | -0.07 | 0 |
| **`r10_d_g15ec`** | **season, gate 288.15 K, E + C** | **-0.97%, 21/30 (24 D10 + K's 6 cold rows)** | **-1.23** | **-1.36** | **-0.81** | **-0.62** | **0** |
| `r10_d_bnrec` | season, no gate, E + C | -0.85% (2 own cold rows, 4 from g10ec) | -1.23 | -1.68 | -0.41 | -0.10 | +0.22 |
| `r10_d_kc3` | cooling integral x3 | +0.79% [+0.19, +1.41], 10/30 | -0.00 | -0.73 | +0.48 | +0.71 | +5.31 |

Station columns are the mean per-scenario change in %. Also run: `r10_d_bhec` stopped after 5 D10 rows (superseded;
not used). Switches off = v11 bit for bit on 6 D10 scenarios across the three code revisions (`r10_off`, `r10_offc`,
`r10_offd`; hot and mild strips).

### Applying the Part 2a rule
Mean per-scenario change over the 30 development scenarios: gate 288.15 K -0.805% (worst scenario 0.00%), gate
283.15 K -0.616% (worst 0.00%), no gate -0.640% (singapore mean +0.22%, worst +2.87%: disqualified), E + C alone
-0.203%. The gate 283.15 K variant is 0.19 points behind, outside the 0.05-point preference. **K = E + C + season with
gate 288.15 K.** Before this Part was written K itself was run on the six cold dev scenarios (`devcheck_K`): bit
identical to `r10_d_bec` and `r10_d_g10ec` on all six, which confirms Part 2a's statement for the 288.15 K gate.

### Candidate K = `r10_K`, fixed
- Code `results/round10/policies/v12d_r10.py` (= `src/policy_candidates/transfer_policy_v12.py`, `make_v12_r10.py`), sha256
  b31da04d53c61a713255dd5ae84cd140a25331a181e2b975b9f49f22c02b25eb. This supersedes the earlier code hash in Part 1
  (the switches `tw_hold_*` and `season_*` were added during development).
- Parameters `results/round10/params/r10_K.json` = {"wk_ext_lo": 12.0, "season_ext_steps": 2016.0, "season_oat_k":
  288.15, "mpr_on": 1.0, "mpr_burst": 0.0, "mpr_safety": 1.3}, sha256
  22273c264731176dee0521020e08c4cb14942a8c990affb55f9e7d48805f94e6. `tw_ramp_k` stays 0, `ki_c_mult` 1.
- No hot-weather component, so HH is a guard (rule 4) and there is no K'. Only K is confirmed; v11 stays if it fails.

### Runs
Job file `results/round10/jobs/confirm_K.json`, sha256 e2b41899f71bc84caee6ba3c4eeedde6760754109cfc12ade93fad2c21d84612:
v11 and K interleaved on HC3 (80), then on HH (80), then K on P (30), HS (18), M (12), FD (20): 240 jobs, Mac, r6 kit copy,
4 workers (the limit given after the PAIEC job ended), `OMP_NUM_THREADS=1`. Decision by `compare_r10.py confirm --cand
r10_K` (sha256 68cb206bed8473bb70c8c8394034a21c988c2eed7d8bfc46b38180190aa31d4f; `compare_r6.py` sha256
eba74edef3a2f398b133b49af80764c849579ab539179aaab197b211889e6cf9), without `--hot`. Reported beyond the rule: P by station,
because the outside-air gate is shut or irrelevant in much of the rest.

### Expectation and known limits, stated before the runs
- Prediction: HC3 about -1.0 to -1.3%; HH about -0.1 to -0.4%, none worse than +0.05% by station; P about -0.5 to
  -0.9%. New buildings may differ.
- The development numbers are selected and therefore optimistic: `tw_hold_*`, `season_*` and the gate values were
  added after reading development rows of the same 30 scenarios. Only the confirmation sets are clean.
- HC3 cannot test the gate: in its cold windows the gate is always open, so HC3 tests E + C + the long season. The gate's
  value rests on D10 (tuned) and on P, HH and FD, which guard against harm but are not a clean test of its benefit.
- E, C and round 9's B ran on P and HS in earlier rounds (on v10); P is not clean for them, the gate is new to it.
- The ramp's exclusion rests on reading `simulator/boiler.py` (the flow term uses the setpoint, the tank warms at a fixed
  rate regardless) and on the bit-identical cold rows; physical gas was not measured separately. It is a judgment on the
  no-quirk constraint, and the reverse call would change nothing in cold windows once the season is long.
