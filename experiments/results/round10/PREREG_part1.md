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
