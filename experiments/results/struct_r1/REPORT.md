# struct_r1 report (written by the orchestrator from the exploration agent's hand-back, 2026-11-09)

Identity: all switches off reproduces v13 bit for bit (identity_check.json). PLAN.md hashed before any screen run.

Screen vs v13 (24 seven-day windows; harsh / public-like / mixture; lower is better; files screen_<arm>.json):
- LA late-recovery escalation, cap 1.0: 1.0187 / 1.0173 / 1.0178 (fail)
- LB late-recovery escalation, cap 0.6: 1.0175 / 1.0151 / 1.0159 (fail)
- HA cooling handover ramp, 1 h: 0.9997 / 0.9891 (12/12) / 0.9927 (PASS, finalist)
- HB cooling handover ramp, 3 h: 0.9998 / 0.9897 (12/12) / 0.9931 (pass)
- SA swing-zone precondition target, 0.1 K: 1.0000 / 1.0011 / 1.0008 (fail)
- SB swing-zone precondition target, 0.3 K: 1.0000 / 0.9995 / 0.9997 (fail)
- MA / MB cost-model supply air on mixed handlers: 1.0010 / 0.9990 / 0.9997 (fail)

Mechanism (HA): public-like comfort regret -65% (no overshoot above 297 K at 06:00-06:30) for +0.1% energy.
Late escalation hurts comfort too (agent's unverified guess: higher pressure pushes more cold forced air into the
handler's other zones).

Frost, HA vs v13, full length on all 18 HS scenarios (frost_hs18_HA.json): coldest -9.95 C both; below-5 C 4.240% vs
4.239%; HS-18 loss ratio 0.9996.

Confirmation: CONFIRM_PLAN.md (sha256 8b82778e..., hashed by the orchestrator before any confirmation run), launched
2026-11-09 11:00 UTC via experiments/src/confirm_struct_ha.py; result -> decision_HA.json.

Not run (described only): a pressure-aware recovery coordinator (~1 day of work); MPC recovery on the kit's linear
model (large rewrite).
