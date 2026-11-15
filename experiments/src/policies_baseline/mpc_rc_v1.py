"""[v1, superseded by mpc_rc.py per PLAN.md Amendment 2; kept for provenance] MPC baseline: per-zone online-identified RC model + enumerated move-blocked MPC (results/baseline_mpc/PLAN.md).

A generic, non-rule baseline for the final-round paper. Same interface as the submission
(class TransferPolicy, __init__(building_meta_data, action_spec), get_action(obs)); numpy only; no files, no network,
no randomness, no pretraining. Every zone fits

    T[t+1] - T[t] = th0 + th1 (T_oa - T[t]) + th2 h_f[t] + th3 c_f[t] + th4 occ[t] + th5 idle_on[t]

(h_f, c_f: first-order filtered heating/cooling commands; idle_on: own AHU runs while the zone is idle) by projected
recursive least squares from the episode's own observations, then picks, every step, the cheapest of 125
move-blocked heat/cool sequences over a 6 h horizon under a cost that mirrors the reward (0.6 comfort shape on
predicted comfort hours, 0.4 x e x |u| energy) plus a small out-of-hours frost/overheat guard. The first block's
level is mapped to actuators by a fixed textbook rule. Constants are fixed in PLAN.md and are not tuned.

Optional overrides (for later dev-only sensitivity runs, never on evaluation sets): JSON file named by the
environment variable MPC_PARAMS_JSON with any of the keys in DEFAULTS.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import re
from collections.abc import Mapping
from typing import Any

import numpy as np

DEFAULTS = {
    "e_heat": 0.5,            # energy cost of full heating, in units of a zone's share of the plant maximum
    "e_cool": 0.5,
    "w_guard": 0.06,          # out-of-hours band weight (the reward's comfort weight is 0.6)
    "blocks": [6, 18, 48],    # move-blocking, steps of 5 min: 0.5 h, 1.5 h, 4 h -> 6 h horizon
    "levels": [-1.0, -0.5, 0.0, 0.5, 1.0],
    "forget": 0.999,
    "sat_cool_k": 285.93,     # 55 F design supply air
    "sat_idle_k": 305.0,
}
# RLS prior: mean and std per parameter [1, T_oa - T, h_f, c_f, occ, ahu_on_idle]; noise std sigma (K/step)
PRIOR_MEAN = np.array([0.0, 0.002, 0.05, -0.05, 0.002, 0.0])
PRIOR_STD = np.array([0.02, 0.002, 0.05, 0.05, 0.01, 0.03])
SIGMA = 0.02
# Amendment 1: physical box for projected RLS, and the command filter gain
THETA_LO = np.array([-0.1, 0.0, 0.002, -0.4, -0.05, -0.3])
THETA_HI = np.array([0.1, 0.02, 0.4, -0.002, 0.1, 0.3])
ALPHA = 0.3


def _num(name: str) -> int:
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else 0


def _shape(dev: np.ndarray) -> np.ndarray:
    """The kit's productivity-regret shape for a deviation (K) from the band."""
    return np.where(dev <= 5.0, dev / 5.0, 1.0 + ((dev - 5.0) / 5.0) ** 2)


class TransferPolicy:
    name = "mpc_rc"

    def __init__(self, building_meta_data: Mapping[str, Any], action_spec: Any = None) -> None:
        md = building_meta_data
        p = dict(DEFAULTS)
        path = os.environ.get("MPC_PARAMS_JSON")
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                p.update(json.load(f))
        self.p = p
        self.n_cont = int(md["n_continuous_action"])
        self.n_disc = int(md["n_discrete_action"])
        names = list(md["observation_field_names"])
        ix = {n: i for i, n in enumerate(names)}
        self.comfort = tuple(float(x) for x in md.get("comfort_temp_window", (294.0, 297.0)))
        self.eco = tuple(float(x) for x in md.get("eco_temp_window", (289.0, 298.0)))
        self.h_on = float(md.get("morning_start_hour", 6))
        self.h_off = float(md.get("evening_start_hour", 19))

        # action ranges from the normalization metadata (generic per kind)
        an = md.get("action_normalization_metadata", {}) or {}

        def rng(kind, lo, hi):
            for k, v in an.items():
                if k.endswith(kind):
                    return float(v["min_native_value"]), float(v["max_native_value"])
            return lo, hi
        self.r_sat = rng("supply_air_temperature_setpoint", 285.0, 305.0)
        self.r_sp = rng("supply_air_static_pressure_setpoint", 0.0, 2000.0)
        self.r_rec = rng("recirculation_percentage_command", 0.0, 1.0)
        self.r_tw = rng("supply_water_temperature_setpoint", 310.0, 350.0)
        self.r_dp = rng("differential_pressure_setpoint", 0.0, 20.0)
        self.r_d = rng("supply_air_damper_percentage_command", 0.0, 1.0)
        self.r_v = rng("reheat_valve_percentage_command", 0.0, 1.0)

        on = md.get("observation_normalization_metadata", {}) or {}
        zt = on.get("zone_air_temperature_sensor", {})
        self.zt_mean = float(zt.get("sample_mean", 295.0))
        self.zt_std = float(zt.get("sample_std", 5.0)) or 5.0
        oa = on.get("outside_air_temperature_sensor", {})
        self.oa_mean = float(oa.get("sample_mean", 295.0))
        self.oa_std = float(oa.get("sample_std", 10.0)) or 10.0

        temp_i = list(md["temp_indices"])
        press_i = list(md["pressure_indices"])
        rec_i = list(md["recirculation_indices"])
        water_i = list(md["water_indices"])
        assign = md.get("ahu_zone_assignments", {}) or {}
        ahus = sorted(assign.keys(), key=_num)
        self.K = len(temp_i)
        ahus = ahus[: self.K]
        self.ahu_sat = temp_i
        self.ahu_sp = [press_i[i] if i < len(press_i) else -1 for i in range(self.K)]
        self.ahu_rec = [rec_i[i] if i < len(rec_i) else -1 for i in range(self.K)]
        self.water_t = water_i[0] if water_i else -1
        self.water_dp = press_i[-1] if len(press_i) > self.K else -1
        self.ahu_oat = [ix.get(f"ahs_{a}_outside_air_temperature_sensor", -1) for a in ahus] + [-1] * (self.K - len(ahus))
        bare = [n for n in names if n.endswith("outside_air_temperature_sensor") and not n.startswith("ahs_")]
        self.bare_oat = ix[bare[0]] if bare else -1

        vav_ahu = {}
        for a, aid in enumerate(ahus):
            for room in assign[aid]:
                vav_ahu[room.replace("room_", "VAV_")] = a
        zt_i, zd, zv, za = [], [], [], []
        self.orphan = []
        for vav, acts in (md.get("zone_action_indices", {}) or {}).items():
            d, v = acts.get("supply_air_damper_percentage_command"), acts.get("reheat_valve_percentage_command")
            t = ix.get(f"{vav}_zone_air_temperature_sensor")
            a = vav_ahu.get(vav)
            if t is None or a is None:
                self.orphan += [s for s in (d, v) if s is not None]
                continue
            zt_i.append(t); zd.append(-1 if d is None else d); zv.append(-1 if v is None else v); za.append(a)
        self.zt_i = np.array(zt_i, dtype=int)
        self.zd = np.array(zd, dtype=int)
        self.zv = np.array(zv, dtype=int)
        self.za = np.array(za, dtype=int)
        self.V = len(zt_i)

        self.hs, self.hc = ix.get("hod_sin_000", -1), ix.get("hod_cos_000", -1)
        self.ds, self.dc = ix.get("dow_sin_000", -1), ix.get("dow_cos_000", -1)
        self.i_cnow = ix.get("comfort_mode_now", -1)

        # RLS state, one 5-parameter model per zone
        n = len(PRIOR_MEAN)
        self.theta = np.tile(PRIOR_MEAN, (self.V, 1))
        self.P0 = np.diag((PRIOR_STD / SIGMA) ** 2)
        self.P = np.tile(self.P0, (self.V, 1, 1))
        self.trP0 = float(np.trace(self.P0))
        self.prev_T = None
        self.prev_x = None
        self.u = np.zeros(self.V)
        self.hf = np.zeros(self.V)        # filtered commands (Amendment 1)
        self.cf = np.zeros(self.V)
        self.ahu_ran = np.zeros(self.K, dtype=bool)

        # move-blocked candidate sequences, expanded to per-step inputs (S, H)
        blocks = [int(b) for b in p["blocks"]]
        self.H = int(sum(blocks))
        seqs = list(itertools.product([float(x) for x in p["levels"]], repeat=len(blocks)))
        self.seq_first = np.array([s[0] for s in seqs])
        self.U = np.array([np.repeat(s, blocks) for s in seqs])            # (S, H)
        self.Uh = np.maximum(self.U, 0.0)
        self.Uc = np.maximum(-self.U, 0.0)
        self.E = (p["e_heat"] * self.Uh + p["e_cool"] * self.Uc).sum(axis=1)  # (S,)
        _ = n

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _norm(x, r):
        lo, hi = r
        return float(np.clip(2.0 * (x - lo) / (hi - lo) - 1.0, -1.0, 1.0)) if hi > lo else 0.0

    def _cyc(self, obs, si, ci, period):
        if si < 0 or ci < 0:
            return None
        s, c = float(obs[si]), float(obs[ci])
        if not (math.isfinite(s) and math.isfinite(c)):
            return None
        a = math.atan2(s, c)
        if a < 0:
            a += 2 * math.pi
        return period * a / (2 * math.pi)

    def _oat(self, obs):
        out = np.full(self.K, np.nan)
        for k, i in enumerate(self.ahu_oat):
            if i >= 0:
                out[k] = obs[i]
        if self.bare_oat >= 0:
            out[np.isnan(out)] = float(obs[self.bare_oat]) * self.oa_std + self.oa_mean
        ok = np.isfinite(out) & (out > 150) & (out < 350)
        fill = float(np.nanmean(out[ok])) if ok.any() else 283.0
        return np.where(ok, out, fill)

    def _occ_schedule(self, hod, dow, cnow):
        """Predicted comfort-hours flag for steps t+1..t+H (and t)."""
        H = self.H
        if hod is None or dow is None:
            return np.zeros(H + 1)
        d0 = int(round(dow)) % 7
        hrs = hod + np.arange(H + 1) / 12.0
        day = (d0 + np.floor(hrs / 24.0).astype(int)) % 7
        h = hrs % 24.0
        occ = ((day < 5) & (h >= self.h_on) & (h < self.h_off)).astype(float)
        # today's comfort mode is off although the schedule says on: holiday/closed, drop the rest of today
        if cnow is not None and cnow < 0.5 and occ[0] > 0.5:
            occ[hrs < 24.0 * (math.floor(hod / 24.0) + 1)] = 0.0
        return occ

    # ------------------------------------------------------------------ step
    def get_action(self, obs: np.ndarray) -> dict[str, np.ndarray]:
        obs = np.asarray(obs, dtype=np.float64)
        p = self.p
        cont = np.zeros(self.n_cont, dtype=np.float32)
        disc = np.zeros(self.n_disc, dtype=np.int32)
        if self.V == 0:
            return {"continuous_action": cont, "discrete_action": disc}

        T = obs[self.zt_i] * self.zt_std + self.zt_mean
        T = np.where(np.isfinite(T), T, 295.0)
        oat_k = self._oat(obs)
        Toa = oat_k[self.za]
        hod = self._cyc(obs, self.hs, self.hc, 24.0)
        dow = self._cyc(obs, self.ds, self.dc, 7.0)
        cnow = float(obs[self.i_cnow]) if self.i_cnow >= 0 and math.isfinite(obs[self.i_cnow]) else None
        occ = self._occ_schedule(hod, dow, cnow)

        # ---- RLS update with the transition just observed
        if self.prev_T is not None:
            x = self.prev_x                                  # (V, 5)
            y = T - self.prev_T
            lam = float(p["forget"])
            Px = np.einsum("vij,vj->vi", self.P, x)
            den = lam + np.einsum("vi,vi->v", x, Px)
            g = Px / den[:, None]
            err = y - np.einsum("vi,vi->v", x, self.theta)
            ok = np.isfinite(err) & (np.abs(err) < 3.0)      # skip sensor glitches
            self.theta[ok] += g[ok] * err[ok, None]
            self.theta = np.clip(self.theta, THETA_LO, THETA_HI)   # projected RLS (Amendment 1)
            Pn = (self.P - np.einsum("vi,vj->vij", g, Px)) / lam
            tr = np.trace(Pn, axis1=1, axis2=2)
            scale = np.where(tr > self.trP0, self.trP0 / np.maximum(tr, 1e-12), 1.0)
            Pn = Pn * scale[:, None, None]
            self.P[ok] = 0.5 * (Pn[ok] + np.transpose(Pn[ok], (0, 2, 1)))

        th = self.theta

        # ---- enumerate sequences, all zones at once: Tp (V, S); filtered inputs roll forward with the plan
        S = self.U.shape[0]
        Tp = np.repeat(T[:, None], S, axis=1)
        hf = np.repeat(self.hf[:, None], S, axis=1)
        cf = np.repeat(self.cf[:, None], S, axis=1)
        ran = self.ahu_ran[self.za].astype(float)[:, None]          # (V, 1)
        cost = np.zeros((self.V, S))
        lo_c, hi_c = self.comfort
        lo_e, hi_e = self.eco
        wg = float(p["w_guard"])
        for k in range(self.H):
            hf = hf + ALPHA * (self.Uh[None, :, k] - hf)
            cf = cf + ALPHA * (self.Uc[None, :, k] - cf)
            idle = (np.abs(self.U[None, :, k]) < 1e-9) * ran
            drift = th[:, 0:1] + th[:, 1:2] * (Toa[:, None] - Tp) + th[:, 4:5] * occ[k] + th[:, 5:6] * idle
            Tp = Tp + drift + th[:, 2:3] * hf + th[:, 3:4] * cf
            o = occ[k + 1]
            if o > 0.5:
                dev = np.maximum(lo_c - Tp, 0.0) + np.maximum(Tp - hi_c, 0.0)
                cost += 0.6 * _shape(dev)
            else:
                dev = np.maximum(lo_e - Tp, 0.0) + np.maximum(Tp - hi_e, 0.0)
                cost += wg * _shape(dev)
        cost += 0.4 * self.E[None, :]
        best = np.argmin(cost, axis=1)
        u = self.seq_first[best]
        u = np.where(np.isfinite(u), u, 0.0)
        h = np.maximum(u, 0.0)
        c = np.maximum(-u, 0.0)

        # ---- actuators
        run = np.zeros(self.K, dtype=bool)
        for k in range(self.K):
            m = self.za == k
            if not m.any():
                continue
            run[k] = bool(np.any(np.abs(u[m]) > 1e-9))
            cooling = bool(np.any(c[m] > 0))
            sat = float(p["sat_cool_k"]) if cooling else float(p["sat_idle_k"])
            cont[self.ahu_sat[k]] = self._norm(sat, self.r_sat)
            if self.ahu_sp[k] >= 0:
                cont[self.ahu_sp[k]] = self._norm(300.0 + 1200.0 * float(np.max(np.abs(u[m]))), self.r_sp)
            if self.ahu_rec[k] >= 0:
                t_ret = float(np.mean(T[m]))
                rec = 1.0                                     # simulator caps recirculation at 0.7
                if cooling and oat_k[k] < t_ret - 1.0:
                    f_oa = (t_ret - sat) / max(t_ret - oat_k[k], 1e-3)
                    rec = 1.0 - float(np.clip(f_oa, 0.3, 1.0))
                cont[self.ahu_rec[k]] = self._norm(rec, self.r_rec)
            disc[k] = 1 if run[k] else 0
        damper = np.where(c > 0, 0.1 + 0.9 * c, np.where(h > 0, 0.15 + 0.35 * h, 0.1))
        valve = np.where(h > 0, 0.3 + 0.7 * h, 0.0)
        for z in range(self.V):
            if self.zd[z] >= 0:
                cont[self.zd[z]] = self._norm(float(damper[z]), self.r_d)
            if self.zv[z] >= 0:
                cont[self.zv[z]] = self._norm(float(valve[z]), self.r_v)
        for s in self.orphan:
            cont[s] = -1.0
        hmax = float(np.max(h)) if h.size else 0.0
        if self.water_t >= 0:
            cont[self.water_t] = self._norm(310.0 + 40.0 * hmax, self.r_tw)
        if self.water_dp >= 0:
            cont[self.water_dp] = self._norm(4.0 + 16.0 * hmax, self.r_dp)
        if self.n_disc > self.K:
            disc[self.n_disc - 1] = 1 if hmax > 0 else 0

        # ---- regressors for the next RLS update: heating/cooling only count if the zone's AHU actually runs
        on = run[self.za].astype(float)
        self.hf = self.hf + ALPHA * (h * on - self.hf)
        self.cf = self.cf + ALPHA * (c * on - self.cf)
        idle_on = on * (np.abs(u) < 1e-9)
        self.prev_x = np.stack([np.ones(self.V), Toa - T, self.hf, self.cf, np.full(self.V, occ[0]), idle_on], axis=1)
        self.ahu_ran = run
        self.prev_T = T
        self.u = u
        return {"continuous_action": np.clip(cont, -1.0, 1.0).astype(np.float32), "discrete_action": disc}
