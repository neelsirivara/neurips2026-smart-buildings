# SB26 submission package (SADR controller)

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private while the
competition runs). The starter kit (`kit/`) and per-scenario time series are not tracked there.

Files:

| file | purpose |
|---|---|
| `transfer_policy.py` | The policy. Drop-in replacement for `smart_buildings/baselines/transfer_policy.py` in the starter kit. Class `TransferPolicy(building_meta_data, action_spec)` with `get_action(obs)`; pure numpy + stdlib; deterministic; shape-agnostic. |
| `kaggle_notebook_template.py` | A self-contained script mirroring the kit's evaluation loop, with the policy inlined, for adapting to the official Kaggle notebook template. |
| `best_params.json` | The final parameter set (v9: the v8 set + the round-6 overrides of `r6_comp`). Its values are baked into `DEFAULT_PARAMS` by `../experiments/src/ship_round6.py`; kept for provenance only, the policy file does not read it. Earlier sets: `../experiments/results/tune/best_params_v8.json`, `best_params_v7.json`, `best_params_v6.json`, `best_params_v5.json`, `best_params_v4.json`; the shipped v8 file is `transfer_policy_v8_shipped_before_round6.py` (here), the shipped v7 file `../experiments/results/round5/transfer_policy_v7_shipped_before_round5.py`, v6 `../experiments/results/round4/transfer_policy_v6_shipped_before_round4.py`, v5 `../experiments/results/round3/transfer_policy_v5_shipped_before_round3.py`. |
| `transfer_policy_v8_shipped_before_round6.py` | The v8 file as shipped in round 5 (md5 98036ef2...), kept for provenance and as the natural second Kaggle selection. |

Version: **SADR v9 (final, round 6)**, baked 2026-10-26 from
`../experiments/results/round6/policies/v9_screen2.py` (the frozen copy of
`../experiments/src/policy_candidates/transfer_policy_v9.py` every round-6 run used) + `r6_comp.json`
(`../experiments/src/ship_round6.py`). v9 keeps every v8 rule (the v9 code with all round-6 switches off reproduces v8
bit for bit) and turns on four, one per family of the pre-registered screen: (1) `sb_boost` 1, `sb_boost_h` 8,
`sb_boost_cold` 1: in heating season, within 8 h of a workday start and while the outside air is at or below the zone's
setback floor, the forced minimum air of a set-back zone on a running handler is reheated to the discharge limit
instead of to the zone temperature (1 J of gas per J, against about 1.9 in the zone's own ventilated recovery);
(2) `sb_boost_floor_k` 2: the same at any time for a set-back zone within 2 K of its floor; (3) `margin_pre` 0.5: the
preconditioning target sits 0.5 K (v8: 0.8 K) inside the comfort band; (4) `night_low_ext` 10: weeknight setback floor
10 K (v8: 8 K) below the eco heating setpoint where the adaptive floor does not bind.

Selection (`../experiments/results/round6/PREREG.md`, `screen_summary.json`, `decision_composite.json`,
`decision.json`, `confirm_r6_comp.json`): 9 single changes screened at full length (8,640 steps) on the harsh
screening set HS (18 scenarios: the shipped six under the coldest strips) and 12 public scenarios against v8; 7 helped,
1 was not significant, the frost-floor variant (reported only) was worse; the composite of the best change per family
was chosen and confirmed at full length: harsh confirmation set HC (48 never-used scenarios) 0.01657 -> 0.01623
(-2.05%, CI -2.70% to -1.43%, 40/48 wins); public-30 0.00777 -> 0.00775 (-0.27%, CI -1.35% to +0.65%, 16/30): the
pre-registered rule (public not worse AND HC better) is met, for all 10 bootstrap seeds. Secondary: M -1.28%
(CI -2.45% to -0.31%), HS -2.32%; FD (20 large default-range scenarios) +0.60% (CI -0.37% to +1.36%; n.s.,
comfort up). Cost: v9 is up to +4% on hot public strips (Singapore, two Atlanta strips), which the
screen ledger attributes to `margin_pre` (a post-hoc composite with `lead_safety` 1.15 instead is -0.9% on the
public 30, CI -1.8% to -0.2%; ledger only, not shipped); v8 is the natural second Kaggle selection. Kaggle: probe submitted
2026-10-26 21:19 UTC (ref 57678857, notebook `kaggle/sadr-v9-comp-smart-buildings/`, built from
`../experiments/results/round6/policies/v9_r6_comp.py`, which differs from `transfer_policy.py` only in two docstring
lines, `../experiments/results/round6/shipped_vs_kaggle_scored.diff`); its Kaggle run of building_train_1/atlanta_2
matches the local total to 0.010%.

### Previous version (v8, round 5), kept for reference

v8 baked 2026-10-26 from
`../experiments/src/policy_candidates/transfer_policy_v8.py` + `r5_c12_comp.json`
(`../experiments/src/ship_round5.py`; the shipped v7 file is kept as
`../experiments/results/round5/transfer_policy_v7_shipped_before_round5.py`, its parameters as
`../experiments/results/tune/best_params_v7.json`). v8 keeps every v7 rule (the v8 code with all round-5 switches
off reproduces v7 bit for bit) and turns on two: (1) `wk_ext_lo` 6 K / `wk_ext_hi` 4 K: far from the next workday
start (more than 22 h ahead, i.e. weekends) the setback floor drops by 6 K and the ceiling rises by 4 K, ramped back
linearly over the 12 h that end 10 h before the start, so the Monday recovery starts from the usual floor (in a real
building the floor, near 2 C, would conflict with frost protection); (2) `q_cap_w` 20,000 W per 100 m2 (v7: 12,000):
the per-zone request cap no longer binds below what the box and coil deliver in deep cold.

Selection (`../experiments/results/round5/PREREG.md`, `screen_summary.json`, `decision.json`,
`confirm_r5_c12_comp.json`, `fd_seed_sensitivity.json`): 11 single changes screened at 2,880 steps on 11 held-out +
4 public scenarios against v7; the composite of the two helpful families was confirmed at full length (8,640 steps,
laptop): public-30 0.00777 vs 0.00786 (-1.1%, CI -2.3% to -0.2%, 17/30 wins); the shipped six under the unused
Minneapolis station (12) -4.1% (CI -10.4% to -0.4%; 6 changed winter scenarios, all wins); public + Minneapolis -2.2%
(CI -4.8% to -0.6%); fresh default-range buildings (20) -0.6% with a CI whose upper end is below zero only for the
pre-registered bootstrap seed (1 of 10 seeds) -- a tie; worst single scenarios +0.5% (public) and +0.7% (FD), hot
strips. The rule (public not worse, better on both P+M and FD) is met as written. Kaggle public: 0.01074 (v7 0.01088;
within noise). The submitted Kaggle notebook (`kaggle/sadr-v8-smart-buildings/`) was built from
`../experiments/results/round5/policies/v8_r5_c12_comp.py`, which differs from `transfer_policy.py` only in two
docstring lines (`../experiments/results/round5/regress/shipped_vs_kaggle_scored.diff`); both reproduce the screened
configuration bit for bit (`regress/xcheck_v8_baked.json`, `regress/xcheck_shipped_v8.json`).

### Previous version (v7, round 4), kept for reference

v7 baked 2026-10-23 from
`../experiments/src/policy_candidates/transfer_policy_v7.py` + `r4_c14_comp_a.json`. v7 keeps every
v6 rule (the v7 code with all round-4 switches off reproduces v6 bit for bit) and turns on five:
(1) `disch_margin_k` 0 (v6: 1 K): flows and valves are sized for the simulator's own 308.15 K
discharge cap, so less air, and less outside air to heat, per joule of reheat; (2) `occ_press_dyn`:
an occupied zone may ask for more flow than its box delivers at the 200 Pa pressure floor only in
proportion to how far it is past its target (from 0.1 K, full flow 0.5 K later); (3) `flush_on` +
`flush_heat_guard`: within 8 h before a workday and outside heating season, set-back zones warmer
than the preconditioning target are flushed with 100% outside air at floor pressure (coil off)
while the outside air is at least 3 K colder; (4) `sb_neutral`: in heating season the forced
minimum flow of set-back zones on a running handler is reheated to the zone temperature;
(5) `f_cap_pre` 0.316 (v6: 0.35), the floor-pressure flow.

Selection (`../experiments/results/round4/PREREG.md`, `candidates.json`, `decision.json`): 13 single
changes screened at 2,880 steps on 10 public + 26 held-out scenarios against v6 under a rule written
before any run; the composite of the best change per family was run once at full length (8,640 steps,
Mac + laptop, bit-identical across machines) and shipped because it met the rule (paired bootstrap,
5,000 resamples): 30 public scenarios 0.00786 vs 0.00803 (-2.1%, CI -4.7% to -0.4%, 24/30 wins;
official scorer on `../experiments/results/final_r4`: 0.00786); 34 never-screened old held-out
scenarios -2.6% (CI -4.4% to -1.3%, 33/34); 40 scenarios of 8 freshly generated buildings run only
for this check -2.3% (CI -3.9% to -1.2%, 38/40; shipped-size buildings -1.4%, default-size -3.0%);
the 74 untouched held-out scenarios pooled 0.00971 vs 0.00995 (-2.5%, CI -3.6% to -1.5%, 71/74)
(`../experiments/results/round4/confirm_r4_c14_comp_a.json`).

### Previous version (v6, round 3), kept for reference

v6 baked from `transfer_policy_v6.py` + `r3_c16_pre035_min1.json`
(`f_cap_pre` 0.35, `area_scale_min` 1.0 on top of the v6 defaults). v6 keeps every v5 rule and
adds five mechanisms for large zones: (1) PI gains, request cap and setback burst scaled with the
zone's floor area / 100 m2, read from the metadata `zone_map` (only upwards: zones under 100 m2
keep the v5 gains); (2) each request bounded by what the VAV box can deliver at a flow fraction
(`f_cap_pre` 0.35 while preconditioning or set back, `f_cap_occ` 1 while occupied); (3) heating
requests bounded by the coil's water-side limit; (4) per-zone optimum start; (5) a setback floor
raised for zones that could not recover within the maximum lead. If `zone_map` is missing from the
metadata the area scaling switches off (every zone is treated as 100 m2) and the rest still works.
With the v6 switches off the code reproduces v5 bit for bit.

Selection (`../experiments/results/round3/candidates.json`): 17 v6 variants screened at 2,880 steps
on 6 public + 6 held-out scenarios against v5 and the v6 defaults; the composite with the best
held-out screen among those that met the rule was run once at full length (8,640 steps, Mac) and
shipped because it beat v5 on every set: 30 public scenarios 0.00803 vs 0.00831 (28/30 wins),
generated buildings 0501/0502 0.00944 vs 0.01109 (10/10), six new generated buildings 0.01294 vs
0.01458 (30/30); `pid_water` on the same runs: 0.05498, 0.03989, 0.05467
(`../experiments/results/final_scores.json`, `heldout_scores.json`, `heldout_r3_scores.json`).

## What the policy needs from the harness

Exactly what the starter kit provides and nothing else:

- `building_meta_data` with keys `n_discrete_action`, `n_continuous_action`, `temp_indices`,
  `pressure_indices`, `recirculation_indices`, `water_indices`, `zone_action_indices`,
  `observation_field_names`, `ahu_zone_assignments`, `comfort_temp_window`, `eco_temp_window`,
  `morning_start_hour`, `evening_start_hour`, `observation_normalization_metadata`,
  `action_normalization_metadata`, and (v6, optional) `zone_map`, which the kit's
  `create_building_meta_data` loads from the scenario's `zone_map.npy`. Missing keys fall back to
  the kit's defaults. The zone map is read once in `__init__` (a breadth-first labelling, about
  40 ms on a 120-zone building).
- `obs`: the flat float observation. Fields are located by name once in `__init__`.
- Returns `{"continuous_action": float32[3K+2+2V] in [-1,1], "discrete_action": int32[K+1] in {0,1}}`
  with every slot written explicitly (the zero action is not "off" in this environment).

No files are read, no network, no randomness, no torch. Per-step cost is ~1 ms on a laptop CPU.
The environment variables `SADR_PARAMS_JSON` / `SADR_DEBUG_LOG` are development hooks: when unset
(the case on Kaggle) the policy uses `DEFAULT_PARAMS` and writes nothing. If the Kaggle rules
forbid any file-system access in the policy, delete the two `os.environ.get(...)` blocks in
`__init__` (lines starting `env_path = os.environ.get("SADR_PARAMS_JSON")` and
`dbg_path = os.environ.get("SADR_DEBUG_LOG")`, each with its `if` body) and the
`if self._dbg is not None:` block at the end of `get_action`; nothing else depends on them.

## Local check (exactly what the Kaggle harness does, on the public scenarios)

```bash
cd kit
cp ../submission/transfer_policy.py smart_buildings/baselines/transfer_policy.py
python -m smart_buildings.evaluate --policies transfer --buildings building_train_1 --weathers fairbanks_1
python score_leaderboard.py smart_buildings/results --policy transfer
```

## Kaggle rules (what could be read without a login)

Checked 2026-10-23: the competition's `/rules` and `/overview` pages return only the page title to
an anonymous fetch (login-gated), so no runtime, file-size, package or submission-count constraint
could be recorded here. Verify on the page after logging in; the policy itself is a single
stdlib+numpy file (about 0.5 ms per step, under 50 KB) and the full 30-scenario run of the kit's
loop takes about 2 hours on 12 cores, so a Kaggle session limit on CPU hours is the only plausible
constraint.

## Submitting with the Kaggle CLI (what was actually done, 2026-10-23)

The official template (`ayushrai1114/transferpolicy-notebook`) is one cell: a `TransferPolicy` subclass of
`kaggle_evaluation.smart_buildings_inference_server.Policy`, then
`SmartBuildingsInferenceServer(TransferPolicy).run(competition_data_folder=...)`; it writes `submission.parquet`.
`kaggle/sadr_v7_submission.py` is v7's source unchanged (class renamed `_SADRPolicy`) followed by that wiring, with a
`TransferPolicy(Policy)` wrapper that delegates to `_SADRPolicy`. `kaggle/push/` holds the one-cell notebook and
`kernel-metadata.json` (private, internet off, competition source attached). Commands:

```bash
kaggle kernels push -p submission/kaggle/push
kaggle kernels status neelsiri/sadr-v7-smart-buildings
kaggle competitions submit neurips-2026-smart-buildings -k neelsiri/sadr-v7-smart-buildings -v <version> -f submission.parquet -m "SADR v7"
```
The CLI (2.2.5) lives in `%USERPROFILE%\.kaggle-cli-venv`; credentials in `%USERPROFILE%\.kaggle\access_token`.

## Round 5 (2026-10-25/26): Kaggle probes and the v8 candidate

Notebooks are now built by `../experiments/src/kaggle_build.py` (it rebuilds the v7 cell above byte for byte,
`--check-v7`): `python kaggle_build.py --source <policy.py> --slug <slug> --title "<Title>" --label "<label>"` writes
`kaggle/<slug>/push/` (one-cell notebook + `kernel-metadata.json`, private, internet off, competition source) and
`kaggle/<slug>/<slug>_localtest.py` (the same policy for `run_scenario.py --policy-file`). `--pid-water` builds the
organizers' baseline. `../experiments/src/kaggle_wait_kernels.sh <version> <slug>...` waits for the interactive run and
downloads its log; `kaggle_poll_submissions.sh <ref>...` polls the scores. Submitted (log and scores:
`../experiments/results/kaggle_feedback.json`):

| ref | kernel | policy file | public score |
|---|---|---|---|
| 57580485 | sadr-v7-smart-buildings v1 | v7 (shipped) | 0.01088 |
| 57639894 | sadr-v6-smart-buildings v1 | v6 (`results/round5/policies/v6.py`) | 0.01116 |
| 57639897 | sadr-v5-smart-buildings v1 | v5 (`results/round5/policies/v5.py`) | 0.01161 |
| 57639900 | pid-water-baseline-smart-buildings v1 | kit `pid.py` + `pid_plus.py` | 0.06404 |
| 57647928 | sadr-v8-smart-buildings v1 | v8 (`results/round5/policies/v8_r5_c12_comp.py`; same code as the shipped file) | 0.01074 |

The v8 candidate (`../experiments/src/policy_candidates/transfer_policy_v8.py` + `r5_c12_comp.json`) met the
pre-registered rule at full length on 2026-10-26 03:36 PDT and is shipped (see the version paragraph above).

## Paste-in instructions for the official Kaggle notebook (manual alternative)

The competition page and its notebook template are only readable when logged in; you have
joined, so open the official submission notebook template from the competition's Code tab and
compare it with the kit's `evaluate.py` loop. Then:

1. **Find the policy cell.** The template defines (or imports) a class named `TransferPolicy`
   with `__init__(self, building_meta_data, action_spec)` and `get_action(self, obs)`. That is
   the only contract the kit's `evaluate.py`/`POLICY_MAP` uses.
2. **Replace the whole cell body with the full contents of `transfer_policy.py`** (from the
   module docstring to the end). Keep the class name `TransferPolicy`; keep the imports
   (`json`, `math`, `os`, `re`, `collections.abc.Mapping`, `typing.Any`, `numpy`) -- all
   standard library plus numpy, nothing to install.
3. **If the template imports the policy from a file** (e.g. `from transfer_policy import
   TransferPolicy`), upload `transfer_policy.py` through the notebook's "Add Input" > "Upload"
   dialog instead, and point the import at that path (`/kaggle/input/<dataset-name>/transfer_policy.py`).
4. **Do not change anything else in the template**: scenario loading, the step loop, the
   `validate_action` call and the output format are the organizers' and are what the grader
   expects. The policy writes every action slot itself, so no post-processing is needed.
5. **Run the notebook once end to end** on the public scenarios ("Save & Run All"). Expected
   per-scenario totals at 8,640 steps (v7) are in `../experiments/results/score_leaderboard_final_r4.txt`
   and `../experiments/results/final_r4/<building>/<weather>/transfer/summary.json` (`total_reward`;
   leaderboard score 0.00786 over the 30); a few per cent deviation is normal if the grader's kit
   version differs. A scenario that returns 0.0 for a 36-step smoke run is normal (the
   episode starts at night with the plant off).
6. **Submit** from the notebook's output as the template instructs; check that the run used
   8,640 steps and that the notebook stayed within the session limit (the policy adds about
   1 ms per step; the simulator dominates at 0.07-0.25 s per step).
7. **Keep the version**: the submitted `transfer_policy.py` must be byte-identical to the one in
   this directory at the commit tagged in `STATUS.md`, so that the paper's numbers refer to the
   submitted policy.
