# SB26 submission package (SADR controller)

Files:

| file | purpose |
|---|---|
| `transfer_policy.py` | The policy. Drop-in replacement for `smart_buildings/baselines/transfer_policy.py` in the starter kit. Class `TransferPolicy(building_meta_data, action_spec)` with `get_action(obs)`; pure numpy + stdlib; deterministic; shape-agnostic. |
| `kaggle_notebook_template.py` | A self-contained script mirroring the kit's evaluation loop, with the policy inlined, for adapting to the official Kaggle notebook template. |
| `best_params.json` | The tuned parameter set (random search, 16 configurations, 6 screening scenarios x 1,440 steps; see `../experiments/results/tune/tune_log.json`). Its values are baked into `DEFAULT_PARAMS` by `../experiments/src/bake_params.py`; kept for provenance only, the policy file does not read it. |

Version: SADR v4 (setback bursts), tuned parameters baked 2026-10-22 (`ki_w_per_k_step` 120,
`margin_pre` 0.8, `sat_mix_floor` 292, `sb_hyst_k` 1.0; all other values are the design defaults).

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

No files are read, no network, no randomness, no torch. Per-step cost is ~1-2 ms on a laptop CPU.
The environment variables `SADR_PARAMS_JSON` / `SADR_DEBUG_LOG` are development hooks: when unset
(the case on Kaggle) the policy uses `DEFAULT_PARAMS` and writes nothing.

## Local check

```bash
cd kit
cp ../submission/transfer_policy.py smart_buildings/baselines/transfer_policy.py
python -m smart_buildings.evaluate --policies transfer --buildings building_train_1 --weathers fairbanks_1
python score_leaderboard.py smart_buildings/results --policy transfer
```

## Adapting to the official Kaggle template (user action)

The competition page (https://www.kaggle.com/competitions/neurips-2026-smart-buildings) and
its rules/data tabs are only readable when logged in, so the exact notebook shape could not be
checked here. Expected shape, from the starter kit README: the graded notebook constructs
`TransferPolicy(building_meta_data, action_spec)` once per held-out scenario and calls
`get_action(obs)` 8,640 times. To adapt:

1. Open the official submission notebook template on Kaggle.
2. Replace the body of the template's policy cell with the full contents of `transfer_policy.py`
   (keep the class name `TransferPolicy`; nothing else is registered).
3. If the template imports the policy from a file instead, upload `transfer_policy.py` as a
   notebook input (Kaggle "Add data" > upload) and import it from that path.
4. Run the notebook once end-to-end on the public scenarios before submitting; the policy
   has no dependencies beyond numpy.
5. Confirm in the rules that the episode length (8,640 steps), the scoring function and the
   `POLICY_MAP` key match the kit version used here (pyproject version 0.1.0).
