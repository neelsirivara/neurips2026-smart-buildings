"""Round 10: build the v12 candidate code from the shipped v11 file (switches off = v11 bit for bit).

Reads submission/transfer_policy.py (v11, baked; md5 6335742f...), applies the round-10 patches below with exact-match
asserts and writes experiments/src/policy_candidates/transfer_policy_v12.py.  Round-10 switches (all default off):

  wk_free        weekend free-float (aimed at the largest slack the round-9 perfect-foresight LP finds: it puts
                 essentially no heat into the building on Saturdays and Sundays, 8-16% of v10/v11's heat, and
                 recovers on Monday morning instead).  While the coming workday follows a non-workday (Friday
                 evening to Monday's lead), a set-back zone has no heating floor beyond ``wk_free_ext_k`` below the
                 eco heating setpoint (``frost_floor_k`` still applies if set).
  wk_lead_max_h  > 0: for the recovery into a workday that follows a non-workday, the lead may be up to this long
                 (instead of ``lead_max_h``); the learned-rate lead and the model lead (mbr) are both clipped to it.
  wk_no_mbr      1 = for that recovery the first-order model lead (mbr) is not used (the learned-rate lead only).
  ki_c_mult      multiplier on the zone cooling loop's integral gain (wind-up and unwinding; heating unchanged).
                 Aimed at hot strips: the occupied cooling integral adds only 30-60 W per step at the morning load
                 ramp, so zones sit 0.1-0.3 K above the band for hours (round 9, debug_cooling_pi_r9.py).
  kq_c_mult      multiplier on the zone cooling loop's proportional gain.
  tw_hold_steps  > 0: keep the hot-water setpoint at tw_hot_k this many steps after the last heating demand WITHOUT
                 lengthening the heating season (heat_season_steps), which also gates the night-flush guard and the
                 set-back reheat (sb_neutral / sb_boost). Round 9's candidate B lengthened heat_season_steps itself,
                 which also switched off the night flush for a week after any heating (round-10 dev: +0.4-0.6% on
                 Phoenix October strips, energy up).
  tw_hold_oat_k  > 0 (with tw_hold_steps): the hold applies only while the outside air has been below this temperature
                 (K) at some step of the last 24 h (no hold in a warm spell: B+E dev, Singapore +0.1-0.6%, 0/6, carbon
                 up after a stray heating demand kept the tank hot for a week).
  season_ext_steps > 0: the heating season (loop hot, night-flush guard, set-back reheat) lasts this many steps after
                 the last heating demand instead of heat_season_steps -- round 9's B -- but only while the outside air
                 was below season_oat_k at some step of the last 24 h (season_oat_k <= 0: always, = B exactly).
                 B+E dev: the long season pays in cool spells (atlanta_7 / denver_4 -1 to -3.8%) and costs in warm
                 ones (atlanta_4 +1.2 / +2.9%, Singapore +0.1-0.6%, Phoenix October mixed).
  season_oat_k   the outside-air threshold (K) of season_ext_steps.
(ki_c_mult / kq_c_mult added 2026-11-01, round 10; at 1.0 the products are exact, so v11 is reproduced bit for bit;
tw_hold_steps added 2026-11-01 ~11:30 UTC after the first dev rows of B+E, tw_hold_oat_k ~11:50 UTC after all 30,
season_ext_steps / season_oat_k ~14:20 UTC after the B'+E (tw_hold) dev rows)

    python experiments/src/make_v12_r10.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "submission" / "transfer_policy.py"
DST = ROOT / "experiments" / "src" / "policy_candidates" / "transfer_policy_v12.py"
V11_MD5 = "6335742f663a5e6c8dfd736010074a05"


def rep(s: str, old: str, new: str) -> str:
    assert s.count(old) == 1, (s.count(old), old[:80])
    return s.replace(old, new, 1)


def main() -> int:
    raw = SRC.read_bytes()
    assert hashlib.md5(raw).hexdigest() == V11_MD5, "submission/transfer_policy.py is not the shipped v11"
    s = raw.decode("utf-8")
    s = rep(s, '''"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v11, final; round 9, r9_dow:
dow_snap 1 on top of v10; every other round-9 switch off).
''', '''"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v12 candidate code, round 10;
all round-10 switches off = v11, round 9, r9_dow).

Round-10 switches (default off): ``wk_free`` (weekend free-float: from the last workday's end until the lead into
the workday that follows a non-workday, a set-back zone has no heating floor beyond ``wk_free_ext_k`` below the eco
heating setpoint), ``wk_lead_max_h`` (> 0: that recovery's lead may be up to this long) and ``wk_no_mbr`` (1 = that
recovery uses the learned-rate lead only, not the first-order model lead), ``ki_c_mult`` / ``kq_c_mult``
(multipliers on the zone cooling loop's integral / proportional gain), ``tw_hold_steps`` (> 0: the loop is kept
hot this long after the last heating demand, separately from the heating season that gates the night flush) and
``tw_hold_oat_k`` (> 0: that hold only while the outside air was below this temperature in the last 24 h),
``season_ext_steps`` / ``season_oat_k`` (> 0: the whole heating season is extended to this many steps after the last
heating demand, only while the outside air was below season_oat_k in the last 24 h).
''')
    s = rep(s, '''    "dow_snap": 1.0,          # 1 = round the decoded day of week (fixes Saturday = workday, Sunday evening)
''', '''    "dow_snap": 1.0,          # 1 = round the decoded day of week (fixes Saturday = workday, Sunday evening)
    # --- round-10 candidate switches (defaults = v11) ---
    "wk_free": 0.0,           # 1 = weekend free-float (no heating floor from Friday evening to Monday's lead)
    "wk_free_ext_k": 30.0,    # ... the floor is then this many K below the eco heating setpoint
    "wk_lead_max_h": 0.0,     # > 0: lead cap (h) of the recovery into a workday that follows a non-workday
    "wk_no_mbr": 0.0,         # 1 = that recovery does not use the model lead (mbr)
    "ki_c_mult": 1.0,         # multiplier on the zone cooling loop's integral gain
    "kq_c_mult": 1.0,         # multiplier on the zone cooling loop's proportional gain
    "tw_hold_steps": 0.0,     # > 0: loop kept hot this long after the last heating demand (heating season unchanged)
    "tw_hold_oat_k": 0.0,     # > 0: ... only while the outside air was below this (K) at some step of the last 24 h
    "season_ext_steps": 0.0,  # > 0: heating season this long after the last heating demand (while cold, below)
    "season_oat_k": 0.0,      # > 0: ... only while the outside air was below this (K) at some step of the last 24 h
''')
    # lead cap for the recovery after a non-workday
    s = rep(s, '''                lead_z = np.clip(lead_z, p["lead_min_h"], p["lead_max_h"])
                if mbr_active and float(p.get("mbr_on", 0.0)) > 0.5 and mbr_ok.any():''',
            '''                lead_cap = p["lead_max_h"]
                wk_after = bool(self.after_off) and workday_ahead
                if float(p.get("wk_lead_max_h", 0.0)) > 0.0 and wk_after:
                    # round 10: the recovery into a workday that follows a non-workday may start earlier
                    lead_cap = max(lead_cap, float(p["wk_lead_max_h"]))
                lead_z = np.clip(lead_z, p["lead_min_h"], lead_cap)
                if (mbr_active and float(p.get("mbr_on", 0.0)) > 0.5 and mbr_ok.any()
                        and not (float(p.get("wk_no_mbr", 0.0)) > 0.5 and wk_after)):''')
    s = rep(s, '''                    lead_m = np.clip(p["lead_base_h"] + float(p.get("mbr_safety", 1.1)) * t_rec,
                                     p["lead_min_h"], p["lead_max_h"])''',
            '''                    lead_m = np.clip(p["lead_base_h"] + float(p.get("mbr_safety", 1.1)) * t_rec,
                                     p["lead_min_h"], lead_cap)''')
    # weekend free-float floor
    s = rep(s, '''            frost = float(p.get("frost_floor_k", 0.0))
            if frost > 0.0:''', '''            if float(p.get("wk_free", 0.0)) > 0.5 and not now and self.after_off:
                # round 10: weekend free-float (the LP bound heats almost nothing on Saturdays and Sundays)
                floor_z = np.minimum(floor_z, self.eco_lo - float(p.get("wk_free_ext_k", 30.0)))
            frost = float(p.get("frost_floor_k", 0.0))
            if frost > 0.0:''')
    # cooling loop gains (round 10, hot strips)
    s = rep(s, '''            dI_c = np.where(e_c > 0.0, ki_z * e_c, dec * ki_z * e_c)''',
            '''            ki_cz = ki_z * max(float(p.get("ki_c_mult", 1.0)), 0.0)   # round 10 (1.0 = v11 exactly)
            dI_c = np.where(e_c > 0.0, ki_cz * e_c, dec * ki_cz * e_c)''')
    s = rep(s, '''            q_c_pi = np.clip(kq_z * np.maximum(e_c, 0.0) + self.I_c, 0.0, q_cap_c)''',
            '''            q_c_pi = np.clip(kq_z * max(float(p.get("kq_c_mult", 1.0)), 0.0) * np.maximum(e_c, 0.0) + self.I_c,
                             0.0, q_cap_c)''')
    # hot-water loop hold, decoupled from the heating season (round 10)
    s = rep(s, '''        self.heat_timer = 0
''', '''        self.heat_timer = 0
        self.tw_timer = 0          # round 10: loop-hold timer (tw_hold_steps)
        self.oat_min_hist = deque(maxlen=288)   # round 10: per-step minimum outside air, last 24 h (tw_hold_oat_k)
        self.season_timer = 0      # round 10: extended heating season (season_ext_steps)
        self.season_on = False     # round 10: extended season active (previous step's value at the flush guard)
''')
    s = rep(s, '''            self.heat_timer = max(self.heat_timer - 1, 0)
        tw = p["tw_hot_k"] if self.heat_timer > 0 else p["tw_idle_k"]
''', '''            self.heat_timer = max(self.heat_timer - 1, 0)
        hold = int(float(p.get("tw_hold_steps", 0.0)))
        if hold > 0:
            # round 10: keep the loop hot after the last heating demand without lengthening the heating season
            # (heat_timer also gates the night-flush guard and the set-back reheat)
            if any_heat_now or (mode == self.PRECOND and deficit_h > 0.0):
                self.tw_timer = hold
            else:
                self.tw_timer = max(self.tw_timer - 1, 0)
        hold_ok = hold > 0 and self.tw_timer > 0
        thr = float(p.get("tw_hold_oat_k", 0.0))
        ext = int(float(p.get("season_ext_steps", 0.0)))
        thr_s = float(p.get("season_oat_k", 0.0))
        if (hold > 0 and thr > 0.0) or (ext > 0 and thr_s > 0.0):
            # round 10: per-step minimum outside air over the last 24 h (one entry per step)
            fin = np.isfinite(oat)
            if fin.any():
                self.oat_min_hist.append(float(oat[fin].min()))
        oat24 = min(self.oat_min_hist) if self.oat_min_hist else float("inf")
        if hold > 0 and thr > 0.0:
            # round 10: no hold in a warm spell (no step of the last 24 h below thr)
            hold_ok = hold_ok and oat24 < thr
        if ext > 0:
            # round 10: round 9's long heating season, only while some step of the last 24 h was below season_oat_k
            if any_heat_now or (mode == self.PRECOND and deficit_h > 0.0):
                self.season_timer = ext
            else:
                self.season_timer = max(self.season_timer - 1, 0)
            self.season_on = self.season_timer > 0 and (thr_s <= 0.0 or oat24 < thr_s)
        tw = p["tw_hot_k"] if (self.heat_timer > 0 or self.season_on or hold_ok) else p["tw_idle_k"]
''')
    s = rep(s, '''            if float(p.get("flush_heat_guard", 0.0)) > 0.5 and self.heat_timer > 0:''',
            '''            if float(p.get("flush_heat_guard", 0.0)) > 0.5 and (self.heat_timer > 0 or self.season_on):''')
    s = rep(s, '''            if float(p.get("sb_neutral", 0.0)) > 0.5 and self.heat_timer > 0:''',
            '''            if float(p.get("sb_neutral", 0.0)) > 0.5 and (self.heat_timer > 0 or self.season_on):''')
    DST.write_text(s, encoding="utf-8", newline="\n")
    print(DST, hashlib.md5(DST.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
