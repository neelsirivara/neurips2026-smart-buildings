# SB26 submission package (SADR controller)

Repository: https://github.com/neelsirivara/neurips2026-smart-buildings (private while the
competition runs). The starter kit (`kit/`) and per-scenario time series are not tracked there.

Files:

| file | purpose |
|---|---|
| `transfer_policy.py` | The policy. Drop-in replacement for `smart_buildings/baselines/transfer_policy.py` in the starter kit. Class `TransferPolicy(building_meta_data, action_spec)` with `get_action(obs)`; pure numpy + stdlib; deterministic; shape-agnostic. |
| `kaggle_notebook_template.py` | A self-contained script mirroring the kit's evaluation loop, with the policy inlined, for adapting to the official Kaggle notebook template. |
| `best_params.json` | The final parameter set (v4 random search + the v5 overrides). Its values are baked into `DEFAULT_PARAMS` by `../experiments/src/bake_params.py`; kept for provenance only, the policy file does not read it. The v4 set is `../experiments/results/tune/best_params_v4.json`. |

Version: **SADR v5 (final)**, baked 2026-10-23. Relative to the design defaults: `ki_w_per_k_step`
120 (random search, 2026-10-21/22), `margin_pre` 0.8, `sat_mix_floor` 292, `sb_hyst_k` 1.0 (same
search, individually neutral), and the analysis-driven v5 changes `sat_cool_hi` 285 (coldest supply
air whenever a handler cools), `night_low_ext` 8 and `night_high_ext` 6 (deeper night setback). The
v5 code differs from v4 in one line: the mixed-handler SAT floor no longer depends on the cooling
ceiling. Candidate `c10_satcold_night8_hi6` won on the 30 public scenarios at full length
(0.00831 vs 0.00920 for v4; `../experiments/results/candidates_summary.json`).

## What the policy needs from the harness

Exactly what the starter kit provides and nothing else:

- `building_meta_data` with keys `n_discrete_action`, `n_continuous_action`, `temp_indices`,
  `pressure_indices`, `recirculation_indices`, `water_indices`, `zone_action_indices`,
  `observation_field_names`, `ahu_zone_assignments`, `comfort_temp_window`, `eco_temp_window`,
  `morning_start_hour`, `evening_start_hour`, `observation_normalization_metadata`,
  `action_normalization_metadata`. Missing keys fall back to the kit's defaults.
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
   per-scenario totals at 8,640 steps are listed in `../experiments/results/final_scores.json`
   (`policies.transfer.per_scenario`); a few per cent deviation is normal if the grader's kit
   version differs. A scenario that returns 0.0 for a 36-step smoke run is normal (the
   episode starts at night with the plant off).
6. **Submit** from the notebook's output as the template instructs; check that the run used
   8,640 steps and that the notebook stayed within the session limit (the policy adds about
   1 ms per step; the simulator dominates at 0.07-0.25 s per step).
7. **Keep the version**: the submitted `transfer_policy.py` must be byte-identical to the one in
   this directory at the commit tagged in `STATUS.md`, so that the paper's numbers refer to the
   submitted policy.
