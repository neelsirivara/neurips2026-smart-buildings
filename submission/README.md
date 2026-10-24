# SB26 submission package (SADR controller)

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private while the
competition runs). The starter kit (`kit/`) and per-scenario time series are not tracked there.

Files:

| file | purpose |
|---|---|
| `transfer_policy.py` | The policy. Drop-in replacement for `smart_buildings/baselines/transfer_policy.py` in the starter kit. Class `TransferPolicy(building_meta_data, action_spec)` with `get_action(obs)`; pure numpy + stdlib; deterministic; shape-agnostic. |
| `kaggle_notebook_template.py` | A self-contained script mirroring the kit's evaluation loop, with the policy inlined, for adapting to the official Kaggle notebook template. |
| `best_params.json` | The final parameter set (v7: the v6 set + the round-4 overrides of `r4_c14_comp_a`). Its values are baked into `DEFAULT_PARAMS` by `../experiments/src/ship_round4.py` / `bake_params.py`; kept for provenance only, the policy file does not read it. Earlier sets: `../experiments/results/tune/best_params_v6.json`, `best_params_v5.json`, `best_params_v4.json`; the shipped v6 file is `../experiments/results/round4/transfer_policy_v6_shipped_before_round4.py`, the shipped v5 file `../experiments/results/round3/transfer_policy_v5_shipped_before_round3.py`. |

Version: **SADR v7 (final, round 4)**, baked 2026-10-23 from
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

## Paste-in instructions for the official Kaggle notebook (user action)

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
