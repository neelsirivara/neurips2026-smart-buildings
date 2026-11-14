# Cumulative build-up, current kit (dry run of the round-2 plan), 2026-11-14

Source: `python experiments/src/buildup_launch.py table` -> `table.json` (paired bootstrap, seed 20261115, 2,000 resamples).
Arms remove features cumulatively from the final controller v14 (B0): bu1 = no refinements, bu2 = also no building
awareness (area scaling, water cap, per-zone start, adaptive floor), bu3 = also no coldest supply air (SAT 293 K),
bu4 = also no idling (fixed 24 h lead, no setback widening). P = pid_water. Step ratio = arm / previous arm.
Gap share = the step's loss increase as a share of the B0 -> pid_water gap.

| set | B0 | bu1 | bu2 | bu3 | bu4 | pid_water |
|---|---|---|---|---|---|---|
| public 30 loss | 0.00730 | 0.00764 | 0.00782 | 0.00844 | 0.01138 | 0.05498 |
| step ratio [95% CI] | | 1.045 [1.028, 1.059] | 1.024 [1.010, 1.035] | 1.079 [1.035, 1.140] | 1.348 [1.283, 1.434] | 4.831 [4.105, 5.868] |
| gap share | | 0.7% | 0.4% | 1.3% | 6.2% | 91.5% |
| cold 40 loss | 0.02346 | 0.02590 | 0.02820 | 0.02819 | 0.03535 | 0.11600 |
| step ratio | | 1.104 [1.082, 1.127] | 1.089 [1.061, 1.116] | 1.000 [0.999, 1.000] | 1.254 [1.197, 1.326] | 3.282 [3.077, 3.508] |
| gap share | | 2.6% | 2.5% | 0.0% | 7.7% | 87.2% |
| hot 40 loss | 0.00722 | 0.00734 | 0.00741 | 0.00899 | 0.01191 | 0.05928 |
| step ratio | | 1.018 [1.014, 1.021] | 1.008 [1.006, 1.011] | 1.214 [1.187, 1.242] | 1.325 [1.291, 1.361] | 4.976 [4.317, 5.709] |
| gap share | | 0.2% | 0.1% | 3.0% | 5.6% | 91.0% |

Idling check (bu3 -> bu4, per-step means): energy +33% / +44% / +32% and carbon +44% / +40% / +30% (public / cold / hot);
comfort regret falls on public and cold. bu4 does keep the plant running more, as intended.

Reading. Idling and the coldest supply air together explain only about 7-9% of the gap to pid_water. Roughly 87-92% remains
between bu4 and pid_water: the controller's core structure (zone-level PI loops on net heat with per-zone VAV and reheat,
static pressure from the most demanding damper) against pid_water's per-AHU loop on mean zone temperature. The claim that
"the margin comes from two design facts" is NOT supported; the core zone-level structure carries the margin. A further
ladder step that replaces the zone loops would be needed to split that remainder. Current kit only; rerun on round 2.
