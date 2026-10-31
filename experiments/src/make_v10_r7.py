"""Round 7: build policy_candidates/transfer_policy_v10.py = the frozen v9 code (results/round6/policies/v9_screen2.py)
+ the round-7 model-based recovery switches, all off by default (off reproduces the v9 code bit for bit).

    python make_v10_r7.py      # rewrites policy_candidates/transfer_policy_v10.py from v9_screen2.py

Switches (ANALYSIS.md, round 7):
  mbr_on     per zone, a first-order thermal model dT/dt = a Q - k (T - Tout) + c (K/h; Q = the net heat the policy
             delivered, kW), fitted online by recursive least squares on 30-minute windows of the zone's own
             unoccupied history; once a zone has mbr_min_n heated windows its optimum-start lead is the model's
             recovery time at the preconditioning request cap (closed form: a first-order approach to
             T_inf = (a A Td + k Tout + c) / (a A + k) with rate a A + k, A = the cap's capacity rate) x mbr_safety,
             i.e. the latest start that reaches the target at occupancy; before that, the v9 learned-rate lead.
  mbr_floor  per zone and every 30 min while set back before a workday, the setback floor is chosen among the v9 floor
             and up to (mbr_floor_ext_max - night_low_ext) K deeper, by minimising the model's predicted gas until
             the workday: holding the floor (heat U (F - Tout) - G at g(F) = 1 + 0.3 (F - Tout)/(Td - F) J of gas per J)
             plus the recovery from it at the cap (gas rate A (Td - 0.3 Tout - 0.7 T), integrated in closed form along
             the first-order trajectory), among floors that the zone reaches in time and recovers from within the lead
             limit (x mbr_safety).
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "results" / "round6" / "policies" / "v9_screen2.py"
DST = HERE / "policy_candidates" / "transfer_policy_v10.py"


def sub(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)


def main() -> int:
    t = SRC.read_text(encoding="utf-8")
    t = sub(t, '"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v9 candidate code, round 6).\n',
            '"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v10 candidate code, round 7).\n\n'
            'Round-7 switches (all off by default, which reproduces the v9 code bit for bit): ``mbr_on`` (model-based\n'
            'optimum start: a per-zone first-order thermal model dT/dt = a Q - k (T - Tout) + c fitted online by recursive\n'
            'least squares on the zone\'s own unoccupied history; the lead is the model\'s recovery time at the request cap\n'
            'times ``mbr_safety``) and ``mbr_floor`` (model-based setback depth: the floor that minimises the model\'s\n'
            'predicted gas for holding it plus recovering from it, among floors reached in time and recoverable within the\n'
            'lead limit, down to ``mbr_floor_ext_max`` below the eco heating setpoint).\n\n'
            'v9 candidate code (round 6):\n')
    t = sub(t, '    "margin_occ_heat_oat": 273.15,\n',
            '    "margin_occ_heat_oat": 273.15,\n'
            '    # --- round-7 candidate switches (defaults = the v9 code) ---\n'
            '    "mbr_on": 0.0,            # 1 = model-based optimum start (per-zone first-order model, RLS)\n'
            '    "mbr_floor": 0.0,         # 1 = model-based setback depth (min predicted hold + recovery gas)\n'
            '    "mbr_safety": 1.1,        # multiplier on the model-predicted recovery time\n'
            '    "mbr_min_n": 36.0,        # heated 30-min windows a zone needs before its model is used\n'
            '    "mbr_lambda": 0.998,      # RLS forgetting factor per update\n'
            '    "mbr_floor_ext_max": 16.0,  # deepest floor considered, K below the eco heating setpoint\n'
            '    "mbr_lead_cap": 0.0,      # 1 = (post hoc, ledger) the model may only shorten the learned-rate lead\n')
    t = sub(t, '        self._lead_dbg = -1.0\n',
            '        self._lead_dbg = -1.0\n'
            '        # round 7: per-zone first-order model dT/dt [K/h] = a Q[kW] - k (T - Tout) + c, RLS state\n'
            '        self.mbr_W = 6                                   # steps per window (30 min)\n'
            '        self.mbr_th = np.tile(np.array([0.5, 0.1, 0.0]), (Vn, 1))\n'
            '        self.mbr_P = np.tile(np.diag([10.0, 1.0, 1.0]), (Vn, 1, 1))\n'
            '        self.mbr_n = np.zeros(Vn)                        # heated windows seen\n'
            '        self.mbr_hT = np.full((self.mbr_W + 1, Vn), np.nan)\n'
            '        self.mbr_hX = np.full((self.mbr_W + 1, Vn), np.nan)   # T - Tout\n'
            '        self.mbr_hQ = np.full((self.mbr_W + 1, Vn), np.nan)   # kW delivered in the step that follows\n'
            '        self.mbr_hU = np.zeros((self.mbr_W + 1, Vn), dtype=bool)  # unoccupied mode in that step\n'
            '        self.mbr_q_prev = np.zeros(Vn)\n'
            '        self.mbr_floor_cache = np.full(Vn, np.nan)\n'
            '        self.mbr_floor_age = 10 ** 6\n')
    # ---- model update, before the mode section (uses the previous step's delivered heat and mode)
    t = sub(t, '        # ---------------- mode ----------------\n',
            '        # ---------------- round 7: per-zone first-order model (RLS) ----------------\n'
            '        mbr_active = bool(V) and (float(p.get("mbr_on", 0.0)) > 0.5 or float(p.get("mbr_floor", 0.0)) > 0.5)\n'
            '        mbr_ok = np.zeros(V, dtype=bool)\n'
            '        if mbr_active:\n'
            '            Wn = self.mbr_W\n'
            '            oat_zone0 = oat_f[self.z_a]\n'
            '            # shift the history: row 0 oldest; the row appended now pairs this step\'s T with the heat and the\n'
            '            # mode of the step that just ended (stored at the end of the previous call)\n'
            '            self.mbr_hT = np.roll(self.mbr_hT, -1, axis=0)\n'
            '            self.mbr_hX = np.roll(self.mbr_hX, -1, axis=0)\n'
            '            self.mbr_hQ = np.roll(self.mbr_hQ, -1, axis=0)\n'
            '            self.mbr_hU = np.roll(self.mbr_hU, -1, axis=0)\n'
            '            self.mbr_hT[-1] = T\n'
            '            self.mbr_hX[-1] = T - oat_zone0\n'
            '            self.mbr_hQ[-2] = self.mbr_q_prev / 1000.0\n'
            '            self.mbr_hU[-2] = self.zone_mode != self.OCCUPIED\n'
            '            okw = (np.isfinite(self.mbr_hT).all(axis=0) & np.isfinite(self.mbr_hQ[:-1]).all(axis=0)\n'
            '                   & self.mbr_hU[:-1].all(axis=0))\n'
            '            if okw.any():\n'
            '                y = (self.mbr_hT[-1] - self.mbr_hT[0]) / (Wn * 300.0 / 3600.0)\n'
            '                x = np.stack([self.mbr_hQ[:-1].mean(axis=0), -self.mbr_hX[:-1].mean(axis=0), np.ones(V)], axis=1)\n'
            '                lam = float(p.get("mbr_lambda", 0.998))\n'
            '                Px = np.einsum("vij,vj->vi", self.mbr_P, x)\n'
            '                den = lam + np.einsum("vi,vi->v", x, Px)\n'
            '                Kg = Px / den[:, None]\n'
            '                err = y - np.einsum("vi,vi->v", x, self.mbr_th)\n'
            '                th_new = self.mbr_th + Kg * err[:, None]\n'
            '                P_new = (self.mbr_P - np.einsum("vi,vj->vij", Kg, Px)) / lam\n'
            '                upd = okw & np.isfinite(err) & (np.abs(err) < 20.0)\n'
            '                self.mbr_th = np.where(upd[:, None], th_new, self.mbr_th)\n'
            '                self.mbr_P = np.where(upd[:, None, None], P_new, self.mbr_P)\n'
            '                self.mbr_n = self.mbr_n + (upd & (x[:, 0] > 0.2))\n'
            '            a_m, k_m = self.mbr_th[:, 0], self.mbr_th[:, 1]\n'
            '            mbr_ok = (self.mbr_n >= float(p.get("mbr_min_n", 36.0))) & (a_m > 1e-3) & (k_m > 1e-3) & (k_m < 3.0)\n'
            '\n'
            '        # ---------------- mode ----------------\n')
    # ---- model-based lead
    t = sub(t, '                lead_z = np.clip(lead_z, p["lead_min_h"], p["lead_max_h"])\n',
            '                lead_z = np.clip(lead_z, p["lead_min_h"], p["lead_max_h"])\n'
            '                if mbr_active and float(p.get("mbr_on", 0.0)) > 0.5 and mbr_ok.any():\n'
            '                    # round 7: the model\'s recovery time to lo_pre at the preconditioning request cap\n'
            '                    t_rec = self._mbr_trec(T, lo_pre, oat_f[self.z_a], F_design, p)\n'
            '                    lead_m = np.clip(p["lead_base_h"] + float(p.get("mbr_safety", 1.1)) * t_rec,\n'
            '                                     p["lead_min_h"], p["lead_max_h"])\n'
            '                    use = mbr_ok & (def_h_z > 0.0) & (def_h_z >= def_c_z)\n'
            '                    if float(p.get("mbr_lead_cap", 0.0)) > 0.5:\n'
            '                        # post hoc (round 7 ledger): the latest feasible start -- the model may delay the start,\n'
            '                        # never advance it past the learned-rate lead; an unreachable model target changes nothing\n'
            '                        use = use & np.isfinite(t_rec)\n'
            '                        lead_m = np.minimum(lead_m, lead_z)\n'
            '                    lead_z = np.where(use, lead_m, lead_z)\n')
    # ---- model-based floor
    t = sub(t, '            frost = float(p.get("frost_floor_k", 0.0))\n',
            '            if (mbr_active and float(p.get("mbr_floor", 0.0)) > 0.5 and not now and workday_ahead\n'
            '                    and mbr_ok.any()):\n'
            '                self.mbr_floor_age += 1\n'
            '                if self.mbr_floor_age >= self.mbr_W or not np.isfinite(self.mbr_floor_cache).any():\n'
            '                    self.mbr_floor_cache = self._mbr_floor(T, floor_z, lo_pre, oat_f[self.z_a], F_design,\n'
            '                                                           hours_to_workday, p)\n'
            '                    self.mbr_floor_age = 0\n'
            '                fc = self.mbr_floor_cache\n'
            '                floor_z = np.where(mbr_ok & is_sb & np.isfinite(fc), np.minimum(floor_z, fc), floor_z)\n'
            '            frost = float(p.get("frost_floor_k", 0.0))\n')
    # ---- delivered-heat estimate for the model (after the valve sizing)
    t = sub(t, '                pump_on = bool(valve.max() > 0.0)\n        else:\n            damper = np.zeros(0)\n',
            '                pump_on = bool(valve.max() > 0.0)\n'
            '            if mbr_active:\n'
            '                # round 7: the policy\'s own estimate of the net heat each zone receives this step\n'
            '                td_eff = t_sa_z\n'
            '                if any_heat_now or neutral.any():\n'
            '                    td_eff = np.where((heat_zone | neutral | boost) & zone_on, t_disch, t_sa_z)\n'
            '                self.mbr_q_prev = np.where(zone_on, F_act * (td_eff - T), 0.0)\n'
            '        else:\n            damper = np.zeros(0)\n')
    # ---- helper methods (before _norm)
    t = sub(t, '    @staticmethod\n    def _norm(x, lo, hi):\n',
            '    # ---------------- round 7: first-order model helpers ----------------\n'
            '    def _mbr_A(self, F_design, p):\n'
            '        """kW/K: capacity rate of the preconditioning request cap (flow fraction f_cap_pre at the discharge limit)."""\n'
            '        f = float(np.clip(p.get("f_cap_pre", F_FLOOR100), max(float(p.get("f_cap_min", F_FLOOR100)), 0.0), 1.0))\n'
            '        return F_design * f / 1000.0\n'
            '\n'
            '    def _mbr_trec(self, T0, T1, Tout, F_design, p):\n'
            '        """Hours to heat from T0 to T1 at the cap, first-order model (inf where the cap cannot get there)."""\n'
            '        a, k, c = self.mbr_th[:, 0], self.mbr_th[:, 1], self.mbr_th[:, 2]\n'
            '        A = self._mbr_A(F_design, p)\n'
            '        td = DISCHARGE_MAX_K - max(p["disch_margin_k"], 0.0)\n'
            '        beta = np.maximum(a * A + k, 1e-6)\n'
            '        tinf = (a * A * td + k * Tout + c) / beta\n'
            '        T1 = np.broadcast_to(T1, np.shape(T0))\n'
            '        ok = tinf > T1 + 0.05\n'
            '        num = np.where(ok, tinf - T0, 1.0)\n'
            '        den = np.where(ok, tinf - T1, 1.0)\n'
            '        t = np.where(T0 >= T1, 0.0, np.log(np.maximum(num, 1e-6) / np.maximum(den, 1e-6)) / beta)\n'
            '        return np.where(ok | (T0 >= T1), np.maximum(t, 0.0), np.inf)\n'
            '\n'
            '    def _mbr_floor(self, T, base, lo_pre, Tout, F_design, hours_to_workday, p):\n'
            '        """Per zone, the setback floor with the least predicted gas until the next workday start."""\n'
            '        a, k, c = self.mbr_th[:, 0], self.mbr_th[:, 1], self.mbr_th[:, 2]\n'
            '        A = self._mbr_A(F_design, p)\n'
            '        td = DISCHARGE_MAX_K - max(p["disch_margin_k"], 0.0)\n'
            '        safety = float(p.get("mbr_safety", 1.1))\n'
            '        lowest = self.eco_lo - float(p.get("mbr_floor_ext_max", 16.0))\n'
            '        H = max(hours_to_workday - p["lead_base_h"], 0.0)\n'
            '        rec_max = max(p["lead_max_h"] - p["lead_base_h"], 0.5)\n'
            '        best = np.array(base, dtype=float).copy()\n'
            '        best_cost = np.full(len(best), np.inf)\n'
            '        beta = np.maximum(a * A + k, 1e-6)\n'
            '        tinf = (a * A * td + k * Tout + c) / beta\n'
            '        teq = Tout + c / np.maximum(k, 1e-6)                # unheated equilibrium\n'
            '        for j in range(0, 33):\n'
            '            F = base - 0.5 * j\n'
            '            if j > 0 and np.all(F < lowest):\n'
            '                break\n'
            '            t_rec = self._mbr_trec(F, lo_pre, Tout, F_design, p)\n'
            '            ok = np.isfinite(t_rec) & (safety * t_rec <= min(rec_max, H)) & (F >= lowest - 1e-9)\n'
            '            tr = np.where(ok, t_rec, 0.0)\n'
            '            # recovery gas: integral of A (Td - 0.3 Tout - 0.7 T(t)) along T(t) = tinf - (tinf - F) e^(-beta t)\n'
            '            g_rec = A * ((td - 0.3 * Tout - 0.7 * tinf) * tr\n'
            '                         + 0.7 * (tinf - F) * (1.0 - np.exp(-beta * tr)) / beta)\n'
            '            # free float from T down to F, then hold F until the recovery must start\n'
            '            reach = (F > teq + 0.05) & (T > F)\n'
            '            t_ff = np.where(reach, np.log(np.maximum(T - teq, 1e-6) / np.maximum(F - teq, 1e-6))\n'
            '                            / np.maximum(k, 1e-6), np.where(T <= F, 0.0, np.inf))\n'
            '            t_hold = np.clip(H - safety * tr - t_ff, 0.0, H)\n'
            '            q_hold = np.maximum((k * (F - Tout) - c) / np.maximum(a, 1e-6), 0.0)\n'
            '            g_hold = 1.0 + 0.3 * (F - Tout) / np.maximum(td - F, 0.5)\n'
            '            cost = g_hold * q_hold * t_hold + g_rec\n'
            '            if j > 0:\n'
            '                ok &= t_hold > 0.0                           # a floor never reached changes nothing\n'
            '            better = ok & (cost < best_cost - 1e-9)\n'
            '            best = np.where(better, F, best)\n'
            '            best_cost = np.where(better, cost, best_cost)\n'
            '        return best\n'
            '\n'
            '    @staticmethod\n    def _norm(x, lo, hi):\n')
    DST.write_text(t, encoding="utf-8", newline="\n")
    print(f"wrote {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
