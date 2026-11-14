# SADR: a structured rule-based HVAC controller for cross-building transfer

Code, results and paper for our entry to the NeurIPS 2026 Smart Buildings Challenge (Kaggle code competition and OpenReview paper track). SADR (Schedule-Aware Demand-Based Reset) is a deterministic HVAC controller that reads the plant topology from the building metadata and otherwise encodes only physics shared by every generated building: occupancy-gated modes with optimum start, per-zone PI loops on net heat, closed-form supply-air and static-pressure resets, reheat and hot-water control, all scaled with zone floor area.

**Headline (local, 30 public scenarios, lower is better).** Final controller 0.00730; base controller 0.00745; organizers' strongest baseline `pid_water` 0.0550 (about 7.5 times higher, lower on all 30 scenarios). Kaggle public leaderboard: 0.01018 (final controller).

**Paper.** `paper/main.pdf` (NeurIPS 2026 workshop style). The paper's "base", "tuned" and "final" controllers are v12, v13 and v14 in the development record.

**Policies.** The final controller is `submission/candidates/transfer_policy_v14.py`; the tuned and base controllers are `transfer_policy_v13.py` in the same folder and `submission/transfer_policy.py`. Each is a drop-in policy file for the starter kit; `submission/kaggle_notebook_template.py` wraps one for Kaggle.

## Layout
```
STATUS.md            development log: every round, its plan, numbers and decisions
experiments/src/     evaluation harness, tuning (CMA-ES), confirmation and frost scripts
experiments/results/ result JSON/CSV the paper is generated from (time series and caches are git-ignored)
paper/               LaTeX source, generated macro files (make_macros_*.py), main.pdf, AUDIT.md
submission/          policy files, Kaggle notebooks and the OpenReview form fields
```

## Reproduce
The starter kit (https://github.com/smart-buildings-2026/starter-kit) runs in a Python 3.12 environment. Scenario runs go through `experiments/src/run_scenario.py` and the round-specific job builders; `paper/make_macros_*.py` turns the result files into the numbers in the paper, and `paper/AUDIT.md` checks each claim against its source file. STATUS.md records the exact command of every round. Per-step logs (`diag.csv`, `ahu_log.csv`, time series) are left out for size; every run's `summary.json` is included, and re-running a scenario regenerates its logs.

## Provenance
Runs used a Windows laptop, an Apple M5 Pro and private Kaggle CPU kernels; seeds are fixed and runs reproduce across machines. We used AI as an assistant. Competition rules, the starter kit and the LaTeX style belong to their respective organizers; our code is MIT-licensed. As the competition rules require of a winning entry, the submission and the source code used to generate it are also licensed under CC-BY 4.0. Competition data (the starter kit's scenarios and building files) is not redistributed here; get it from the competition page.
