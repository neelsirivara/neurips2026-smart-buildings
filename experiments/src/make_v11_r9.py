"""Round 9: build the v11 candidate code from the shipped v10 file (switches off = v10 bit for bit).

Reads submission/transfer_policy.py (v10, baked), applies the round-9 patches below with exact-match asserts and
writes experiments/src/policy_candidates/transfer_policy_v11.py.  Round-9 switches (all default off):

  obr_on        occupied band riding in heating: an occupied zone that needs heat is no longer held at
                lo + margin_occ by a PI loop that, at low demand, reheats its forced minimum air below the
                discharge cap all day (g = (T_d - T_sa)/(T_d - T) up to ~3).  Instead it is latched into a
                burst at the cap when it falls below lo_s + obr_start_k and released above lo_s + obr_stop_k;
                zones of a handler that is bursting join while below lo_s + obr_join_k; and while a handler
                runs, the forced air of its heating-regime occupied zones below lo_s + obr_boost_k is reheated
                to the discharge cap (1 J of gas per J: the outside-air share of that air is paid anyway).
                A handler with no burst and no cooling demand stops, so its zones carry no ventilation load.
                Bound (round-9 analysis): the occupied delivery excess (coil duty above every zone-day's
                net need delivered at the cap).
  tw_ramp_k     > 0: while the pump runs, the hot-water setpoint is never more than tw_ramp_k above the tank
                temperature (the tank rises 0.5 K/min = 2.5 K per step anyway) and never below it.  The shipped
                boiler bills the loop flow at (setpoint - return), so a setpoint far above a tank that is still
                warming bills heat the coils never received (an over-charge; PR #2's energy-balanced tank has
                no such term).  Never below the tank keeps clear of the opposite (under-billing) quirk.

  dow_snap      (candidate D, a bug fix) the day-of-week feature is integral but arrives as float32 sin/cos, so it
                decodes to e.g. 4.999999999 on Saturdays and 6.99999998 for the day after Sunday; v10 compares
                the raw float with 5, so it treats every Saturday as a workday (a full recovery from about
                02:00 to 06:00, then back to setback) and every Sunday evening as not before a workday (the Monday
                recovery cannot start before midnight).  dow_snap rounds the decoded day to the nearest integer.
  mpr_on        model-predictive recovery (prototype C): each zone carries a second-order model of its own air
                temperature, fitted online by recursive least squares on its unoccupied 5-minute history,
                    T(k+1) - T(k) = a (T(k) - T(k-1)) + b Q(k) - c (T(k) - T_out(k)) + d,
                (the air jump and the slab's slow charge, which round 7's first-order 30-minute model mixes up).
                Before a workday the zone starts at the latest step from which the model, heating at the
                preconditioning request cap, reaches the preconditioning target (times mpr_safety); like v10's
                model start it may only shorten the learned-rate lead.  With mpr_burst the zone then heats at
                that cap (the model's assumption) instead of ramping a PI up.

    python experiments/src/make_v11_r9.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "submission" / "transfer_policy.py"
DST = ROOT / "experiments" / "src" / "policy_candidates" / "transfer_policy_v11.py"


MODEL_BLOCK = '        # ---------------- round 9: second-order zone model (mpr) ----------------\n        mpr_ok = np.zeros(V, dtype=bool)\n        if V and float(p.get("mpr_on", 0.0)) > 0.5:\n            oat_z9 = oat_f[self.z_a]\n            if self.mpr_T1 is not None and self.mpr_T2 is not None and len(self.mpr_T1) == V:\n                y9 = T - self.mpr_T1\n                q9 = self.mbr_q_prev / 1000.0 if mbr_active else np.zeros(V)\n                x9 = np.stack([self.mpr_T1 - self.mpr_T2, q9, -(self.mpr_T1 - self.mpr_To1), np.ones(V)], axis=1)\n                lam9 = float(p.get("mpr_lambda", 0.9995))\n                Px9 = np.einsum("vij,vj->vi", self.mpr_P, x9)\n                den9 = lam9 + np.einsum("vi,vi->v", x9, Px9)\n                K9 = Px9 / den9[:, None]\n                err9 = y9 - np.einsum("vi,vi->v", x9, self.mpr_th)\n                upd9 = self.mpr_U1 & np.isfinite(err9) & (np.abs(y9) < 2.0) & np.isfinite(x9).all(axis=1)\n                th9 = self.mpr_th + K9 * err9[:, None]\n                P9 = (self.mpr_P - np.einsum("vi,vj->vij", K9, Px9)) / lam9\n                self.mpr_th = np.where(upd9[:, None], th9, self.mpr_th)\n                self.mpr_P = np.where(upd9[:, None, None], P9, self.mpr_P)\n                self.mpr_n = self.mpr_n + upd9\n            a9, b9, c9 = self.mpr_th[:, 0], self.mpr_th[:, 1], self.mpr_th[:, 2]\n            mpr_ok = ((self.mpr_n >= float(p.get("mpr_min_n", 288.0))) & (a9 >= 0.0) & (a9 < 0.98)\n                      & (b9 > 1e-3) & (c9 > 1e-5) & (c9 < 0.05))\n            self.mpr_T2 = self.mpr_T1\n            self.mpr_T1 = T.copy()\n            self.mpr_To1 = oat_z9.copy()\n\n        # ---------------- mode ----------------\n        lo_pre = self.comfort_lo + p["margin_pre"]'
LEAD_BLOCK = '                if float(p.get("mpr_on", 0.0)) > 0.5 and mpr_ok.any() and self.mpr_T2 is not None:\n                    # round 9: simulate the zone heating at the preconditioning request cap from now on\n                    a9, b9, c9, d9 = (self.mpr_th[:, i] for i in range(4))\n                    tz = T.copy()\n                    dz = T - self.mpr_T2\n                    dz = np.where(np.isfinite(dz), np.clip(dz, -0.5, 0.5), 0.0)\n                    sc9 = self.scale[:V]\n                    steps9 = np.full(V, np.inf)\n                    to9 = oat_f[self.z_a]\n                    fcp9 = float(p.get("f_cap_pre", F_FLOOR100))\n                    for k9 in range(int(p["lead_max_h"] * 12)):\n                        qc9 = np.minimum(p["q_cap_w"] * sc9, F_design * fcp9 * np.maximum(DISCHARGE_MAX_K - tz, 0.5)) / 1000.0\n                        dz = a9 * dz + b9 * qc9 - c9 * (tz - to9) + d9\n                        tz = tz + dz\n                        hit = ~np.isfinite(steps9) & (tz >= lo_pre)\n                        steps9 = np.where(hit, k9 + 1.0, steps9)\n                        if np.isfinite(steps9).all():\n                            break\n                    lead_p = float(p.get("mpr_safety", 1.1)) * steps9 / 12.0\n                    use9 = mpr_ok & np.isfinite(lead_p) & (def_h_z > 0.0) & (def_h_z >= def_c_z)\n                    lead_z = np.where(use9, np.clip(np.minimum(lead_p, lead_z), p["lead_min_h"], p["lead_max_h"]),\n                                      lead_z)\n                m_lead = float(p.get("mon_lead_mult", 1.0))\n                if m_lead != 1.0 and self.after_off:'
UNOCC_BLOCK = '        self.mode = mode\n        self.zone_mode = zone_mode\n        if V and float(p.get("mpr_on", 0.0)) > 0.5:\n            self.mpr_U1 = zone_mode[:V] != self.OCCUPIED\n'
BURST_BLOCK = '            if float(p.get("mpr_on", 0.0)) > 0.5 and float(p.get("mpr_burst", 1.0)) > 0.5:\n                q_h_pi = np.where(is_pre & (e_h > 0.3), q_cap_h, q_h_pi)\n            if float(p.get("pre_burst_h", 0.0)) > 0.5:'


DOW_BLOCK = '        dow = self._cyclic(obs, self.dow_sin, self.dow_cos, 7.0)\n        if dow is not None and float(p.get("dow_snap", 0.0)) > 0.5:\n            # round 9: the feature is an integer day sent as float32 sin/cos; Saturday decodes to 4.999999999\n            dow = float(int(round(dow)) % 7)'


def rep(s: str, old: str, new: str) -> str:
    assert s.count(old) == 1, (s.count(old), old[:80])
    return s.replace(old, new, 1)


def main() -> int:
    s = SRC.read_text(encoding="utf-8")
    assert hashlib.md5(SRC.read_bytes()).hexdigest().startswith("7d7f6899"), "submission file is not v10"
    s = rep(s, '"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v10, final; round 8, r7L_mbr2).',
            '"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v11 candidate code, round 9;\n'
            'all round-9 switches off = v10, round 8, r7L_mbr2).\n\n'
            'Round-9 switches (default off): ``obr_on`` (occupied band riding: heat occupied zones in bursts at the\n'
            'discharge cap and let handlers stop between bursts; reheat the forced air of heating-regime zones to the\n'
            'cap while a handler runs) and ``tw_ramp_k`` (hot-water setpoint kept within this many K above the tank\n'
            'temperature, never below it, while the pump runs).\n\nv10:')
    # params
    s = rep(s, '''    "mbr_lead_cap": 1.0,      # 1 = (post hoc, ledger) the model may only shorten the learned-rate lead
}''', '''    "mbr_lead_cap": 1.0,      # 1 = (post hoc, ledger) the model may only shorten the learned-rate lead
    # --- round-9 candidate switches (defaults = v10) ---
    "obr_on": 0.0,            # 1 = occupied band riding (bursts at the cap, handlers stop between bursts)
    "obr_start_k": 0.3,       # a heating-regime occupied zone starts a burst below lo_s + this (K)
    "obr_join_k": 0.6,        # ... joins a burst already running on its handler below lo_s + this
    "obr_stop_k": 0.9,        # ... ends its burst above lo_s + this
    "obr_boost_k": 0.9,       # forced air of heating-regime occupied zones on a running handler is reheated to
                              #     the discharge cap below lo_s + this
    "obr_cool_guard_k": 1.0,  # a zone within this of its cooling target is never in the heating regime
    "tw_ramp_k": 0.0,         # > 0: pump on -> setpoint within [tank, tank + tw_ramp_k]
    "dow_snap": 0.0,          # 1 = round the decoded day of week (fixes Saturday = workday, Sunday evening)
    "mpr_on": 0.0,            # 1 = model-predictive recovery start (second-order online zone model)
    "mpr_safety": 1.1,        # multiplier on the model's recovery time
    "mpr_min_n": 288.0,       # unoccupied 5-min samples a zone needs before its model is used
    "mpr_lambda": 0.9995,     # RLS forgetting factor per sample
    "mpr_burst": 1.0,         # 1 = (with mpr_on) a preconditioning zone below target heats at the request cap
}''')
    # state
    s = rep(s, '''        self.mbr_floor_cache = np.full(Vn, np.nan)
        self.mbr_floor_age = 10 ** 6
''', '''        self.mbr_floor_cache = np.full(Vn, np.nan)
        self.mbr_floor_age = 10 ** 6
        self.obr_latch = np.zeros(Vn, dtype=bool)        # round 9: occupied burst latches
        self.obr_regime = np.zeros(Vn, dtype=bool)       # round 9: zone in the occupied heating regime
        # round 9 (mpr): second-order zone model dT(k+1) = a dT(k) + b Q(k)[kW] - c (T - Tout) + d, RLS state
        self.mpr_th = np.tile(np.array([0.5, 0.05, 0.002, 0.0]), (Vn, 1))
        self.mpr_P = np.tile(np.diag([1.0, 1.0, 0.01, 0.1]), (Vn, 1, 1))
        self.mpr_n = np.zeros(Vn)
        self.mpr_T1 = None                               # T at the previous step
        self.mpr_T2 = None                               # T two steps back
        self.mpr_To1 = None                              # outside air at the previous step
        self.mpr_U1 = np.zeros(Vn, dtype=bool)           # previous step was unoccupied (setback / precondition)
''')
    # zone loop: band riding replaces the occupied heating PI
    s = rep(s, '''            q_c_pi = np.clip(kq_z * np.maximum(e_c, 0.0) + self.I_c, 0.0, q_cap_c)
            # a zone cannot be heated and cooled at once: the larger request wins''',
            '''            q_c_pi = np.clip(kq_z * np.maximum(e_c, 0.0) + self.I_c, 0.0, q_cap_c)
            obr = float(p.get("obr_on", 0.0)) > 0.5
            if obr:
                # round 9: occupied band riding.  Heating regime = occupied, not near the cooling target and
                # not cooling; there the PI is replaced by bursts at the cap (q_cap_h at the occupied flow cap).
                reg = is_occ & (T < hi - float(p.get("obr_cool_guard_k", 1.0))) & (self.I_c <= 0.0) & (e_c <= 0.0)
                start = reg & (T < lo_s + float(p.get("obr_start_k", 0.3)))
                stop = T > lo_s + float(p.get("obr_stop_k", 0.9))
                latch = reg & ~stop & (self.obr_latch | start)
                burst_ahu = np.zeros(K, dtype=bool)
                np.logical_or.at(burst_ahu, self.z_a, latch)
                latch = latch | (reg & burst_ahu[self.z_a] & (T < lo_s + float(p.get("obr_join_k", 0.6))))
                self.obr_latch = latch
                self.obr_regime = reg
                self.I_h = np.where(reg, 0.0, self.I_h)
                q_h_pi = np.where(reg, np.where(latch, q_cap_h, 0.0), q_h_pi)
            else:
                self.obr_regime = np.zeros(V, dtype=bool)
            # a zone cannot be heated and cooled at once: the larger request wins''')
    # forced-air boost for heating-regime occupied zones on running handlers
    s = rep(s, '''            bfk = float(p.get("sb_boost_floor_k", 0.0))
            if bfk > 0.0 and neutral.any():''', '''            if float(p.get("obr_on", 0.0)) > 0.5:
                # round 9: forced air of heating-regime occupied zones on a running handler goes in at the cap
                occ_boost = (zone_on & self.obr_regime & ~heat_zone & ~cool_zone & (T > t_sa_z + 0.5)
                             & (T < lo_s + float(p.get("obr_boost_k", 0.9))))
                neutral = neutral | occ_boost
                boost = boost | occ_boost
            bfk = float(p.get("sb_boost_floor_k", 0.0))
            if bfk > 0.0 and neutral.any():''')
    # mpr (prototype C): model update before the mode section, model start, sample flags, burst recovery
    s = rep(s, """        # ---------------- mode ----------------
        lo_pre = self.comfort_lo + p["margin_pre"]""", MODEL_BLOCK)
    s = rep(s, """                m_lead = float(p.get("mon_lead_mult", 1.0))
                if m_lead != 1.0 and self.after_off:""", LEAD_BLOCK)
    s = rep(s, """        self.mode = mode
        self.zone_mode = zone_mode
""", UNOCC_BLOCK)
    s = rep(s, """            if float(p.get("pre_burst_h", 0.0)) > 0.5:""", BURST_BLOCK)
    # dow_snap (candidate D): round the decoded day of week
    s = rep(s, """        dow = self._cyclic(obs, self.dow_sin, self.dow_cos, 7.0)""", DOW_BLOCK)
    # hot-water setpoint ramp
    s = rep(s, '''        if self.water_temp_idx >= 0:
            cont[self.water_temp_idx] = self._norm(tw, *self.tw_rng)''', '''        twr = float(p.get("tw_ramp_k", 0.0))
        if twr > 0.0 and pump_on:
            # round 9: never bill the loop for a setpoint the tank cannot reach this step, never go below the tank
            tw = float(np.clip(tw, tw_obs, tw_obs + twr))
            tw = float(np.clip(tw, self.tw_rng[0], self.tw_rng[1]))
        if self.water_temp_idx >= 0:
            cont[self.water_temp_idx] = self._norm(tw, *self.tw_rng)''')
    DST.write_text(s, encoding="utf-8", newline="\n")
    print(DST, hashlib.md5(DST.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
