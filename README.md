# Smart Buildings Challenge 2026: SADR controller

Entry for the NeurIPS 2026 Smart Buildings Challenge (Kaggle code competition + OpenReview paper track): a Schedule-Aware Demand-based Reset (SADR) HVAC controller that reads the building metadata, with occupancy-gated modes, per-zone net-heat PI loops, supply-air-temperature and static-pressure resets, economizer logic and hot-water reset; tuned by random search with held-out buildings.

**Deadlines.** Poster-paper round 2026-11-13 (OpenReview SB26_Challenge); Kaggle leaderboard + final paper 2027-01-15.

**Headline (local evaluation).** Full 30-scenario evaluation in progress at the time of the first commit; see STATUS.md for the current numbers.

**Submission artifact.** `submission/transfer_policy.py (drop-in for the kit's policy file) + submission/kaggle_notebook_template.py`

## Layout
```
STATUS.md            what is built, verified numbers, user to-dos, risks (start here)
experiments/src/     pipeline code (data, evaluation harness, make_macros.py, make_figures.py, make_audit.py)
experiments/results/ result JSON/CSV the paper is generated from (caches are git-ignored)
paper/               NeurIPS 2026 LaTeX source, results_macros.tex (generated), main.pdf, AUDIT.md, review/
submission/          the bundle and upload instructions (README.md)
```

## Reproduce
`see STATUS.md (kit/.venv Python 3.12; experiments/src/run_eval_parallel.py; score_all.py; make_macros.py; paper build)`

Every number in `paper/main.pdf` is a macro emitted by `experiments/src/make_macros.py` from the result files;
`paper/AUDIT.md` re-derives each directional claim from the same files. `paper/bib_verification_log.json`
records how every reference was verified.

## Provenance and disclosure
Built on a CPU-only laptop (8 cores, 34 GB RAM, no GPU) with an LLM coding assistant (Claude) for code and
drafting; see the paper's disclosure section. Competition rules, starter kits and style files belong to their
respective organizers. Repository created 2026-10-22 by `make_repos.py`; owner `neelsirivara`.
