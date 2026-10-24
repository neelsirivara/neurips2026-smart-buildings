from __future__ import annotations
import json
import math
import os
import re
from collections import deque
from collections.abc import Mapping
from typing import Any
import numpy as np
SAT_MIN_K = 285.0
SAT_MAX_K = 305.0
P_MAX_PA = 2000.0
P_FLOOR_PA = 200.0
DAMPER_FLOOR = 0.1
RECIRC_MAX = 0.7
TW_MIN_K = 310.0
TW_MAX_K = 350.0
DP_MAX_BAR = 20.0
DISCHARGE_MAX_K = 308.15
AIR_RHO_CP = 1.2 * 1006.0
WATER_RHO_CP = 1000.0 * 4180.0
ECON_K_PER_PA = 0.00322
CV_AREA_M2 = 0.04
F_FLOOR100 = math.sqrt(P_FLOOR_PA / P_MAX_PA)
F_MIN = DAMPER_FLOOR * F_FLOOR100
DEFAULT_PARAMS: dict[str, float] = {'margin_occ': 0.3, 'margin_pre': 0.8, 'night_low_ext': 8.0, 'night_high_ext': 6.0, 'sb_hyst_k': 1.0, 'q_sb_w': 4000.0, 'e_full_k': 1.0, 'e_full2_k': 4.0, 'lead_base_h': 0.5, 'lead_min_h': 0.75, 'lead_max_h': 8.0, 'rate0_kph': 2.0, 'rate_min_kph': 0.4, 'rate_max_kph': 8.0, 'rate_ema': 0.5, 'lead_safety': 1.3, 'holiday_check_h': 7.0, 'per_zone_start': 1.0, 'adaptive_floor': 1.0, 'pre_latch': 0.0, 'kq_w_per_k': 400.0, 'ki_w_per_k_step': 120.0, 'i_decay_mult': 1.0, 'q_cap_w': 12000.0, 'q_on_w': 50.0, 'area_ref_m2': 100.0, 'gain_area_scaling': 1.0, 'area_scale_min': 1.0, 'area_scale_max': 6.0, 'f_cap_pre': 0.31622776601683794, 'f_cap_occ': 1.0, 'water_cap': 1.0, 'water_cap_frac': 0.97, 'min_on_steps': 3, 'min_off_steps': 2, 'sat_cool_hi': 285.0, 'sat_mix_floor': 292.0, 'disch_margin_k': 0.0, 'econ_on': 1.0, 'kv_valve': 0.108, 'valve_target': 0.9, 'dp_lo_bar': 0.1, 'dp_hi_bar': 20.0, 'tw_idle_k': 310.0, 'tw_hot_k': 350.0, 'heat_season_steps': 288, 'f_cap_min': 0.31622776601683794, 'occ_press_dyn': 1.0, 'f_cap_occ_lo': 0.31622776601683794, 'occ_press_e0': 0.1, 'occ_press_span': 0.5, 'sat_mix_relief': 0.0, 'sat_mix_relief_min': 285.0, 'flush_on': 1.0, 'flush_dt_k': 3.0, 'flush_depth_k': 1.0, 'flush_lo_margin_k': 0.5, 'flush_window_h': 8.0, 'flush_heat_guard': 1.0, 'sb_neutral': 1.0, 'sb_neutral_cold': 0.0}

def _num_suffix(name: str) -> int:
    m = re.search('(\\d+)', name)
    return int(m.group(1)) if m else 0

def _clip01(x):
    return np.clip(x, 0.0, 1.0)

def _room_areas(zone_map) -> np.ndarray | None:
    try:
        zm = np.asarray(zone_map)
    except Exception:
        return None
    if zm.ndim != 2 or zm.size == 0 or zm.size > 20000000:
        return None
    free = zm == 0
    if not free.any():
        return None
    H, W = free.shape
    lab = np.zeros((H, W), dtype=np.int32)
    counts: list[int] = []
    rows, cols = np.nonzero(free)
    for r0, c0 in zip(rows.tolist(), cols.tolist()):
        if lab[r0, c0]:
            continue
        n = len(counts) + 1
        lab[r0, c0] = n
        size = 1
        dq = deque([(r0, c0)])
        while dq:
            r, c = dq.popleft()
            if r + 1 < H and free[r + 1, c] and (not lab[r + 1, c]):
                lab[r + 1, c] = n
                size += 1
                dq.append((r + 1, c))
            if r > 0 and free[r - 1, c] and (not lab[r - 1, c]):
                lab[r - 1, c] = n
                size += 1
                dq.append((r - 1, c))
            if c + 1 < W and free[r, c + 1] and (not lab[r, c + 1]):
                lab[r, c + 1] = n
                size += 1
                dq.append((r, c + 1))
            if c > 0 and free[r, c - 1] and (not lab[r, c - 1]):
                lab[r, c - 1] = n
                size += 1
                dq.append((r, c - 1))
        counts.append(size)
    return np.asarray(counts, dtype=float) * CV_AREA_M2

class _SADRPolicy:
    name = 'transfer'
    OCCUPIED, PRECOND, SETBACK = (0, 1, 2)

    def __init__(self, building_meta_data: Mapping[str, Any], action_spec: Any, params: Mapping[str, float] | None=None) -> None:
        md = building_meta_data
        self.metadata = md
        self.action_spec = action_spec
        self.p = dict(DEFAULT_PARAMS)
        if params:
            self.p.update(params)
        env_path = os.environ.get('SADR_PARAMS_JSON')
        if env_path:
            try:
                with open(env_path) as f:
                    self.p.update(json.load(f))
            except (OSError, ValueError):
                pass
        p = self.p
        self.n_discrete = int(md['n_discrete_action'])
        self.n_continuous = int(md['n_continuous_action'])
        names = list(md['observation_field_names'])
        self.ix = {n: i for i, n in enumerate(names)}
        temp_indices = list(md['temp_indices'])
        pressure_indices = list(md['pressure_indices'])
        recirc_indices = list(md['recirculation_indices'])
        water_indices = list(md['water_indices'])
        zone_action_indices = md['zone_action_indices']
        assignments = md.get('ahu_zone_assignments', {}) or {}
        ahu_ids = sorted(assignments.keys(), key=_num_suffix)
        self.K = len(temp_indices)
        if len(ahu_ids) > self.K:
            ahu_ids = ahu_ids[:self.K]
        self.ahu_temp_idx = np.array(temp_indices[:self.K], dtype=int)
        self.ahu_press_idx = np.array([pressure_indices[i] if i < len(pressure_indices) else -1 for i in range(self.K)], dtype=int)
        self.ahu_recirc_idx = np.array([recirc_indices[i] if i < len(recirc_indices) else -1 for i in range(self.K)], dtype=int)
        self.ahu_oat_idx = np.array([self.ix.get(f'ahs_{aid}_outside_air_temperature_sensor', -1) for aid in ahu_ids] + [-1] * (self.K - len(ahu_ids)), dtype=int)
        bare = [n for n in names if n.endswith('outside_air_temperature_sensor') and (not n.startswith('ahs_'))]
        self.bare_oat_idx = self.ix[bare[0]] if bare else -1
        onorm = md.get('observation_normalization_metadata', {}) or {}
        oat_n = onorm.get('outside_air_temperature_sensor', {})
        self.oat_mean = float(oat_n.get('sample_mean', 295.0))
        self.oat_std = float(oat_n.get('sample_std', 10.0)) or 10.0
        zt = onorm.get('zone_air_temperature_sensor', {})
        self.zt_mean = float(zt.get('sample_mean', 295.0))
        self.zt_std = float(zt.get('sample_std', 5.0)) or 5.0
        vav_to_ahu: dict[str, int] = {}
        for a, aid in enumerate(ahu_ids):
            for room in assignments[aid]:
                vav_to_ahu[room.replace('room_', 'VAV_')] = a
        z_t, z_lo, z_hi, z_d, z_v, z_a, z_mf, z_num = ([], [], [], [], [], [], [], [])
        self.orphan_slots: list[int] = []
        for vav_id, acts in zone_action_indices.items():
            d_idx = acts.get('supply_air_damper_percentage_command')
            v_idx = acts.get('reheat_valve_percentage_command')
            t_idx = self.ix.get(f'{vav_id}_zone_air_temperature_sensor')
            a_idx = vav_to_ahu.get(vav_id)
            if t_idx is None or a_idx is None:
                for s in (d_idx, v_idx):
                    if s is not None:
                        self.orphan_slots.append(int(s))
                continue
            z_t.append(t_idx)
            z_lo.append(self.ix.get(f'{vav_id}_zone_air_heating_temperature_setpoint_sensor', -1))
            z_hi.append(self.ix.get(f'{vav_id}_zone_air_cooling_temperature_setpoint_sensor', -1))
            z_d.append(-1 if d_idx is None else int(d_idx))
            z_v.append(-1 if v_idx is None else int(v_idx))
            z_a.append(a_idx)
            z_mf.append(self.ix.get(f'{vav_id}_supply_air_flowrate_setpoint', -1))
            z_num.append(_num_suffix(vav_id))
        self.V = len(z_t)
        self.z_t = np.array(z_t, dtype=int)
        self.z_lo = np.array(z_lo, dtype=int)
        self.z_hi = np.array(z_hi, dtype=int)
        self.z_d = np.array(z_d, dtype=int)
        self.z_v = np.array(z_v, dtype=int)
        self.z_a = np.array(z_a, dtype=int)
        self.z_mf = np.array(z_mf, dtype=int)
        self.member = np.zeros((self.K, max(self.V, 1)), dtype=bool)
        if self.V:
            self.member[self.z_a, np.arange(self.V)] = True
        self.ahu_has_zones = self.member.any(axis=1)
        self.ahu_zone_count = np.maximum(self.member.sum(axis=1), 1)
        area_ref = max(float(p.get('area_ref_m2', 100.0)), 1.0)
        self.area_m2 = np.full(max(self.V, 1), area_ref)
        self.area_known = False
        if self.V and float(p.get('gain_area_scaling', 1.0)) > 0.5:
            areas = _room_areas(md.get('zone_map'))
            if areas is not None and len(areas) >= max(z_num) >= 1 and (min(z_num) >= 1):
                cand = areas[np.array(z_num, dtype=int) - 1]
                if np.all(np.isfinite(cand)) and np.all(cand > 0) and (len(areas) == self.V):
                    self.area_m2 = cand.astype(float)
                    self.area_known = True
        if self.V and self.area_known:
            self.scale = np.clip(self.area_m2 / area_ref, float(p.get('area_scale_min', 0.3)), float(p.get('area_scale_max', 6.0)))
        else:
            self.scale = np.ones(max(self.V, 1))
        self.water_temp_idx = int(water_indices[0]) if water_indices else -1
        self.water_press_idx = int(pressure_indices[-1]) if len(pressure_indices) > self.K else -1
        self.water_disc_idx = self.n_discrete - 1
        self.hws_temp_obs_idx = self.ix.get('hws_supply_water_temperature_sensor', -1)
        cw = md.get('comfort_temp_window', (294.0, 297.0))
        ew = md.get('eco_temp_window', (289.0, 298.0))
        self.comfort_lo, self.comfort_hi = (float(cw[0]), float(cw[1]))
        self.eco_lo, self.eco_hi = (float(ew[0]), float(ew[1]))
        self.morning_start = float(md.get('morning_start_hour', 6))
        self.evening_start = float(md.get('evening_start_hour', 19))
        self.hod_sin = self.ix.get('hod_sin_000', -1)
        self.hod_cos = self.ix.get('hod_cos_000', -1)
        self.dow_sin = self.ix.get('dow_sin_000', -1)
        self.dow_cos = self.ix.get('dow_cos_000', -1)
        self.now_idx = self.ix.get('comfort_mode_now', -1)
        self.soon_idx = self.ix.get('comfort_mode_soon', -1)
        self.occ_idx = self.ix.get('num_occupants', -1)
        anorm = md.get('action_normalization_metadata', {}) or {}

        def rng(key_sub, lo, hi):
            for k, v in anorm.items():
                if key_sub in k:
                    try:
                        return (float(v['min_native_value']), float(v['max_native_value']))
                    except (KeyError, TypeError, ValueError):
                        return (lo, hi)
            return (lo, hi)
        self.sat_rng = rng('supply_air_temperature_setpoint', SAT_MIN_K, SAT_MAX_K)
        self.p_rng = rng('static_pressure_setpoint', 0.0, P_MAX_PA)
        self.tw_rng = rng('supply_water_temperature_setpoint', TW_MIN_K, TW_MAX_K)
        self.dp_rng = rng('differential_pressure_setpoint', 0.0, DP_MAX_BAR)
        self._dbg = None
        dbg_path = os.environ.get('SADR_DEBUG_LOG')
        if dbg_path:
            try:
                self._dbg = open(dbg_path, 'w')
                self._dbg.write('step,hod,dow,now,soon,occupied,mode,holiday,lead_h,rate_h,rate_c,deficit_h,deficit_c,Tmin,Tmax,Tmean,n_heat,n_cool,maxP,n_on,tw,dp,pump,max_valve,max_damper,sat_min,recirc_min,n_pre\n')
            except OSError:
                self._dbg = None
        self.reset()

    def reset(self) -> None:
        p = self.p
        Vn = max(self.V, 1)
        self.ahu_on = np.zeros(self.K, dtype=bool)
        self.dwell = np.zeros(self.K, dtype=int)
        self.recirc_prev = np.full(self.K, RECIRC_MAX)
        self.I_h = np.zeros(Vn)
        self.I_c = np.zeros(Vn)
        self.sb_latch_h = np.zeros(Vn, dtype=bool)
        self.sb_latch_c = np.zeros(Vn, dtype=bool)
        self.heat_timer = 0
        self.step_count = 0
        self.occ_min = math.inf
        self.last_hod = None
        self.seen_occ_today = False
        self.holiday = False
        self.mode = self.SETBACK
        self.zone_mode = np.full(Vn, self.SETBACK, dtype=int)
        self.flush_latch = np.zeros(Vn, dtype=bool)
        self.rate_h = float(p['rate0_kph'])
        self.rate_c = float(p['rate0_kph'])
        self.pre_active = False
        self.pre_t0 = 0
        self.pre_deficit0 = 0.0
        self.pre_kind = 0
        self.pre_reached_step = -1
        self.rate_h_z = np.full(Vn, float(p['rate0_kph']))
        self.rate_c_z = np.full(Vn, float(p['rate0_kph']))
        self.zpre_active = np.zeros(Vn, dtype=bool)
        self.zpre_t0 = np.zeros(Vn, dtype=int)
        self.zpre_def0 = np.zeros(Vn)
        self.zpre_kind = np.zeros(Vn, dtype=int)
        self.zpre_reached = np.full(Vn, -1, dtype=int)
        self.pre_latch = np.zeros(Vn, dtype=bool)
        self._lead_dbg = -1.0

    @staticmethod
    def _norm(x, lo, hi):
        if hi <= lo:
            return 0.0
        return 2.0 * (x - lo) / (hi - lo) - 1.0

    def _cyclic(self, obs, si, ci, period):
        if si < 0 or ci < 0:
            return None
        s, c = (float(obs[si]), float(obs[ci]))
        if not (math.isfinite(s) and math.isfinite(c)):
            return None
        ang = math.atan2(s, c)
        if ang < 0:
            ang += 2.0 * math.pi
        return period * ang / (2.0 * math.pi)

    def _oat(self, obs) -> np.ndarray:
        out = np.full(self.K, np.nan)
        m = self.ahu_oat_idx >= 0
        if m.any():
            out[m] = obs[self.ahu_oat_idx[m]]
        if self.bare_oat_idx >= 0:
            v = float(obs[self.bare_oat_idx]) * self.oat_std + self.oat_mean
            out[~m] = v
        out = np.where(np.isfinite(out) & (out > 150.0) & (out < 350.0), out, np.nan)
        return out

    def get_action(self, obs: np.ndarray) -> dict[str, np.ndarray]:
        p = self.p
        obs = np.asarray(obs, dtype=np.float64)
        cont = np.zeros(self.n_continuous, dtype=np.float32)
        disc = np.zeros(self.n_discrete, dtype=np.int32)
        K, V = (self.K, self.V)
        self.step_count += 1
        per_zone_start = V > 0 and float(p.get('per_zone_start', 1.0)) > 0.5
        hod = self._cyclic(obs, self.hod_sin, self.hod_cos, 24.0)
        dow = self._cyclic(obs, self.dow_sin, self.dow_cos, 7.0)
        if self.now_idx >= 0 and math.isfinite(obs[self.now_idx]):
            now = float(obs[self.now_idx]) > 0.5
        else:
            now = hod is not None and dow is not None and (dow < 5.0) and (self.morning_start <= hod < self.evening_start)
        soon = self.soon_idx >= 0 and math.isfinite(obs[self.soon_idx]) and (float(obs[self.soon_idx]) > 0.5)
        if hod is not None:
            if self.last_hod is not None and hod < self.last_hod - 12.0:
                self.seen_occ_today = False
                self.holiday = False
            self.last_hod = hod
        occupied = False
        if self.occ_idx >= 0 and math.isfinite(obs[self.occ_idx]):
            o = float(obs[self.occ_idx])
            if self.step_count > 1:
                self.occ_min = min(self.occ_min, o)
                occupied = o > self.occ_min + 0.002
        if occupied:
            self.seen_occ_today = True
            self.holiday = False
        if V:
            T = obs[self.z_t] * self.zt_std + self.zt_mean
            T = np.where(np.isfinite(T) & (T > 200.0) & (T < 350.0), T, self.zt_mean)
            sched_lo, sched_hi = (self.comfort_lo, self.comfort_hi) if now else (self.eco_lo, self.eco_hi)
            lo_s = np.where(self.z_lo >= 0, obs[np.maximum(self.z_lo, 0)], sched_lo)
            hi_s = np.where(self.z_hi >= 0, obs[np.maximum(self.z_hi, 0)], sched_hi)
            bad = ~np.isfinite(lo_s) | ~np.isfinite(hi_s) | (hi_s <= lo_s) | (lo_s < 250) | (hi_s > 330)
            lo_s = np.where(bad, sched_lo, lo_s)
            hi_s = np.where(bad, sched_hi, hi_s)
        else:
            T = lo_s = hi_s = np.zeros(0)
        if V:
            design_flow = np.where(self.z_mf >= 0, obs[np.maximum(self.z_mf, 0)], 2.0)
            design_flow = np.where(np.isfinite(design_flow) & (design_flow > 0.01) & (design_flow < 100.0), design_flow, 2.0)
            F_design = AIR_RHO_CP * design_flow
            F_floor = F_design * F_FLOOR100
            F_min = F_design * F_MIN
        else:
            design_flow = F_design = F_floor = F_min = np.zeros(0)
        if V:
            T_ret = (self.member * T[None, :]).sum(axis=1) / self.ahu_zone_count
        else:
            T_ret = np.full(K, self.zt_mean)
        oat = self._oat(obs)
        oat_f = np.where(np.isfinite(oat), oat, T_ret)
        tw_obs = float(obs[self.hws_temp_obs_idx]) if self.hws_temp_obs_idx >= 0 else float('nan')
        if not (math.isfinite(tw_obs) and 273.0 < tw_obs < 400.0):
            tw_obs = 340.0
        kv = max(p['kv_valve'], 0.0001)
        cap1 = WATER_RHO_CP * kv / 3600.0
        lo_pre = self.comfort_lo + p['margin_pre']
        hi_pre = self.comfort_hi - p['margin_pre']
        safety = max(p['lead_safety'], 0.001)
        if V:
            def_h_z = np.maximum(0.0, lo_pre - T)
            def_c_z = np.maximum(0.0, T - hi_pre)
            deficit_h = float(def_h_z.max())
            deficit_c = float(def_c_z.max())
        else:
            def_h_z = def_c_z = np.zeros(0)
            deficit_h = deficit_c = 0.0
        prev_zone_mode = self.zone_mode
        workday_ahead = False
        hours_to_start = 24.0
        if now:
            if hod is not None and hod >= p['holiday_check_h'] and (not self.seen_occ_today) and (self.occ_idx >= 0):
                self.holiday = True
            mode = self.SETBACK if self.holiday and (not occupied) else self.OCCUPIED
            zone_mode = np.full(max(V, 1), mode, dtype=int)
            self.pre_latch[:] = False
        else:
            workday_ahead = False
            hours_to_start = 24.0
            if hod is not None and dow is not None:
                hours_to_start = (self.morning_start - hod) % 24.0
                day_next = dow if hod < self.morning_start else (dow + 1.0) % 7.0
                workday_ahead = day_next < 5.0
            if per_zone_start:
                lead_z = p['lead_base_h'] + np.maximum(def_h_z / np.maximum(self.rate_h_z / safety, 0.001), def_c_z / np.maximum(self.rate_c_z / safety, 0.001))
                lead_z = np.clip(lead_z, p['lead_min_h'], p['lead_max_h'])
                self._lead_dbg = float(lead_z.max())
                lead_rule = workday_ahead & (hours_to_start <= lead_z)
                if float(p.get('pre_latch', 0.0)) > 0.5:
                    self.pre_latch = (self.pre_latch | lead_rule | bool(soon)) & workday_ahead & (hours_to_start <= p['lead_max_h'])
                    pre_z = self.pre_latch | occupied
                else:
                    pre_z = lead_rule | bool(soon) | occupied
                zone_mode = np.where(pre_z, self.PRECOND, self.SETBACK)
                mode = self.PRECOND if bool(pre_z.any()) else self.SETBACK
            else:
                precondition = bool(soon)
                if workday_ahead:
                    lead = p['lead_base_h'] + max(deficit_h / max(self.rate_h / safety, 0.001), deficit_c / max(self.rate_c / safety, 0.001))
                    lead = min(max(lead, p['lead_min_h']), p['lead_max_h'])
                    self._lead_dbg = lead
                    if hours_to_start <= lead:
                        precondition = True
                mode = self.PRECOND if precondition or occupied else self.SETBACK
                zone_mode = np.full(max(V, 1), mode, dtype=int)
        if per_zone_start:
            start = (zone_mode == self.PRECOND) & ~self.zpre_active & (prev_zone_mode != self.OCCUPIED)
            if start.any():
                self.zpre_active[start] = True
                self.zpre_t0[start] = self.step_count
                self.zpre_def0[start] = np.maximum(def_h_z, def_c_z)[start]
                self.zpre_kind[start] = np.where(def_h_z >= def_c_z, 1, -1)[start]
                self.zpre_reached[start] = -1
            act = self.zpre_active
            if act.any():
                cur = np.where(self.zpre_kind > 0, def_h_z, def_c_z)
                newly = act & (self.zpre_reached < 0) & (cur <= 0.1)
                self.zpre_reached[newly] = self.step_count
                ended = act & (zone_mode != self.PRECOND)
                if ended.any():
                    end_step = np.where(self.zpre_reached > 0, self.zpre_reached, self.step_count)
                    hours = np.maximum((end_step - self.zpre_t0) / 12.0, 1.0 / 12.0)
                    recovered = self.zpre_def0 - np.where(self.zpre_reached > 0, 0.0, cur)
                    valid = ended & (self.zpre_def0 >= 0.5)
                    good = valid & (recovered > 0.0)
                    r_obs = np.clip(recovered / hours, p['rate_min_kph'], p['rate_max_kph'])
                    a = p['rate_ema']
                    upd_h = good & (self.zpre_kind > 0)
                    upd_c = good & (self.zpre_kind < 0)
                    self.rate_h_z = np.where(upd_h, (1 - a) * self.rate_h_z + a * r_obs, self.rate_h_z)
                    self.rate_c_z = np.where(upd_c, (1 - a) * self.rate_c_z + a * r_obs, self.rate_c_z)
                    fail = valid & ~good & (zone_mode == self.OCCUPIED)
                    self.rate_h_z = np.where(fail & (self.zpre_kind > 0), np.maximum(self.rate_h_z * 0.5, p['rate_min_kph']), self.rate_h_z)
                    self.rate_c_z = np.where(fail & (self.zpre_kind < 0), np.maximum(self.rate_c_z * 0.5, p['rate_min_kph']), self.rate_c_z)
                    self.zpre_active[ended] = False
        else:
            if mode == self.PRECOND and (not self.pre_active) and (self.mode != self.OCCUPIED):
                self.pre_active = True
                self.pre_t0 = self.step_count
                self.pre_deficit0 = max(deficit_h, deficit_c)
                self.pre_kind = 1 if deficit_h >= deficit_c else -1
                self.pre_reached_step = -1
            if self.pre_active:
                cur = deficit_h if self.pre_kind > 0 else deficit_c
                if self.pre_reached_step < 0 and cur <= 0.1:
                    self.pre_reached_step = self.step_count
                if mode != self.PRECOND:
                    if self.pre_deficit0 >= 0.5:
                        end_step = self.pre_reached_step if self.pre_reached_step > 0 else self.step_count
                        hours = max((end_step - self.pre_t0) / 12.0, 1.0 / 12.0)
                        recovered = self.pre_deficit0 - (0.0 if self.pre_reached_step > 0 else cur)
                        if recovered > 0.0:
                            r_obs = recovered / hours
                            r_obs = min(max(r_obs, p['rate_min_kph']), p['rate_max_kph'])
                            a = p['rate_ema']
                            if self.pre_kind > 0:
                                self.rate_h = (1 - a) * self.rate_h + a * r_obs
                            else:
                                self.rate_c = (1 - a) * self.rate_c + a * r_obs
                        elif mode == self.OCCUPIED:
                            if self.pre_kind > 0:
                                self.rate_h = max(self.rate_h * 0.5, p['rate_min_kph'])
                            else:
                                self.rate_c = max(self.rate_c * 0.5, p['rate_min_kph'])
                    self.pre_active = False
        self.mode = mode
        self.zone_mode = zone_mode
        if V:
            is_occ = zone_mode == self.OCCUPIED
            is_pre = zone_mode == self.PRECOND
            is_sb = zone_mode == self.SETBACK
            floor_z = np.full(V, self.eco_lo - p['night_low_ext'])
            ceil_z = np.full(V, self.eco_hi + p['night_high_ext'])
            if per_zone_start and float(p.get('adaptive_floor', 1.0)) > 0.5:
                recover_h = max(p['lead_max_h'] - p['lead_base_h'], 0.5)
                floor_z = np.maximum(floor_z, lo_pre - self.rate_h_z / safety * recover_h)
                ceil_z = np.minimum(ceil_z, hi_pre + self.rate_c_z / safety * recover_h)
            lo = np.where(is_occ, lo_s + p['margin_occ'], np.where(is_pre, lo_pre, floor_z))
            hi = np.where(is_occ, hi_s - p['margin_occ'], np.where(is_pre, hi_pre, ceil_z))
            mid = 0.5 * (lo + hi)
            lo = np.minimum(lo, mid - 0.1)
            hi = np.maximum(hi, mid + 0.1)
        else:
            is_occ = is_pre = is_sb = np.zeros(0, dtype=bool)
            lo = hi = np.zeros(0)
        flush_z = np.zeros(V, dtype=bool)
        if V and float(p.get('flush_on', 0.0)) > 0.5 and (not now) and workday_ahead and (hours_to_start <= float(p.get('flush_window_h', 8.0))):
            oat_z = oat[self.z_a]
            tgt = max(hi_pre - float(p.get('flush_depth_k', 1.0)), lo_pre + float(p.get('flush_lo_margin_k', 0.5)))
            ok = is_sb & np.isfinite(oat_z) & (oat_z <= T - float(p.get('flush_dt_k', 3.0)))
            if float(p.get('flush_heat_guard', 0.0)) > 0.5 and self.heat_timer > 0:
                ok = np.zeros(V, dtype=bool)
            self.flush_latch = ok & (self.flush_latch | (T > tgt + 0.3)) & (T > tgt)
            flush_z = self.flush_latch.copy()
        elif V:
            self.flush_latch[:] = False
        e_h = lo - T
        e_c = T - hi
        kq_z = max(p['kq_w_per_k'], 0.0) * self.scale[:V]
        ki_z = max(p['ki_w_per_k_step'], 0.0) * self.scale[:V]
        t_disch_max = DISCHARGE_MAX_K - max(p['disch_margin_k'], 0.0)
        sat_lo, sat_hi_native = self.sat_rng
        if V:
            f_occ = float(p.get('f_cap_occ', 1.0))
            if float(p.get('occ_press_dyn', 0.0)) > 0.5:
                e_pos = np.maximum(np.maximum(e_h, e_c), 0.0)
                f_lo = float(p.get('f_cap_occ_lo', F_FLOOR100))
                ramp = np.clip((e_pos - float(p.get('occ_press_e0', 0.3))) / max(float(p.get('occ_press_span', 1.0)), 0.001), 0.0, 1.0)
                f_occ = f_lo + (max(f_occ, f_lo) - f_lo) * ramp
            f_cap = np.where(is_occ, f_occ, float(p.get('f_cap_pre', 0.7)))
            f_cap = np.clip(f_cap, max(float(p.get('f_cap_min', F_FLOOR100)), 0.0), 1.0)
            cap_h = F_design * f_cap * np.maximum(t_disch_max - T, 0.5)
            cap_c = F_design * f_cap * np.maximum(T - sat_lo, 0.5)
            q_cap_h = np.minimum(max(p['q_cap_w'], 100.0) * self.scale[:V], cap_h)
            q_cap_c = np.maximum(np.minimum(max(p['q_cap_w'], 100.0) * self.scale[:V], cap_c), 100.0)
            if float(p.get('water_cap', 1.0)) > 0.5:
                mixed_est = (RECIRC_MAX * T_ret + (1.0 - RECIRC_MAX) * oat_f)[self.z_a]
                t_sa_est = np.minimum(mixed_est, T - 0.5)
                w_avail = cap1 * math.sqrt(max(min(p['dp_hi_bar'], self.dp_rng[1]), p['dp_lo_bar'], 0.001))
                coil_max = w_avail * np.maximum(tw_obs - t_sa_est, 1.0)
                cap_h_water = coil_max * np.maximum(t_disch_max - T, 0.5) / np.maximum(t_disch_max - t_sa_est, 1.0)
                q_cap_h = np.minimum(q_cap_h, float(p.get('water_cap_frac', 0.97)) * cap_h_water)
            q_cap_h = np.maximum(q_cap_h, 100.0)
            hyst = max(p['sb_hyst_k'], 0.1)
            self.sb_latch_h = is_sb & (self.sb_latch_h | (e_h > 0.0)) & (e_h > -hyst)
            self.sb_latch_c = is_sb & (self.sb_latch_c | (e_c > 0.0)) & (e_c > -hyst)
            q_sb_h = np.minimum(max(p['q_sb_w'], 100.0) * self.scale[:V], q_cap_h)
            q_sb_c = np.minimum(max(p['q_sb_w'], 100.0) * self.scale[:V], q_cap_c)
            heat_sb = self.sb_latch_h & ~self.sb_latch_c
            cool_sb = self.sb_latch_c & ~self.sb_latch_h
            dec = max(p['i_decay_mult'], 0.0)
            dI_h = np.where(e_h > 0.0, ki_z * e_h, dec * ki_z * e_h)
            dI_c = np.where(e_c > 0.0, ki_z * e_c, dec * ki_z * e_c)
            self.I_h = np.where(is_sb, 0.0, np.clip(self.I_h + dI_h, 0.0, q_cap_h))
            self.I_c = np.where(is_sb, 0.0, np.clip(self.I_c + dI_c, 0.0, q_cap_c))
            q_h_pi = np.clip(kq_z * np.maximum(e_h, 0.0) + self.I_h, 0.0, q_cap_h)
            q_c_pi = np.clip(kq_z * np.maximum(e_c, 0.0) + self.I_c, 0.0, q_cap_c)
            heat_pi = ~is_sb & (q_h_pi > q_c_pi) & (q_h_pi > p['q_on_w'])
            cool_pi = ~is_sb & (q_c_pi >= q_h_pi) & (q_c_pi > p['q_on_w'])
            heat_zone = heat_sb | heat_pi
            cool_zone = cool_sb | cool_pi
            q_h = np.where(heat_sb, q_sb_h, np.where(heat_pi, q_h_pi, 0.0))
            q_c = np.where(cool_sb, q_sb_c, np.where(cool_pi, q_c_pi, 0.0))
        else:
            q_h = q_c = np.zeros(0)
            heat_zone = cool_zone = np.zeros(0, dtype=bool)
        if V:
            H = np.where(self.ahu_has_zones, (self.member * q_h[None, :]).max(axis=1), 0.0)
            C = np.where(self.ahu_has_zones, (self.member * q_c[None, :]).max(axis=1), 0.0)
        else:
            H = C = np.zeros(K)
        D = np.maximum(H, C)
        fl_ahu = np.zeros(K, dtype=bool)
        if V and flush_z.any():
            np.logical_or.at(fl_ahu, self.z_a, flush_z)
            fl_ahu &= D <= 0.0
        flush_eff = flush_z & fl_ahu[self.z_a] if V else np.zeros(0, dtype=bool)
        want_on = (D > p['q_on_w']) | fl_ahu
        want_off = (D <= 0.0) & ~fl_ahu
        can_switch = self.dwell >= np.where(self.ahu_on, p['min_on_steps'], p['min_off_steps'])
        turn_on = ~self.ahu_on & want_on & can_switch
        turn_off = self.ahu_on & want_off & can_switch
        new_on = (self.ahu_on | turn_on) & ~turn_off
        self.dwell = np.where(new_on == self.ahu_on, self.dwell + 1, 0)
        self.ahu_on = new_on
        on = self.ahu_on
        sat_hi = min(max(p['sat_cool_hi'], sat_lo), sat_hi_native)
        sat = np.full(K, sat_hi_native)
        if V:
            t_need = np.where(cool_zone, T - q_c / np.maximum(F_floor, 1.0), np.inf)
            t_need_ahu = np.full(K, np.inf)
            np.minimum.at(t_need_ahu, self.z_a, t_need)
            has_cool = C > 0.0
            s = np.clip(t_need_ahu, sat_lo, sat_hi)
            mix_floor = min(p['sat_mix_floor'], sat_hi_native)
            if float(p.get('sat_mix_relief', 0.0)) > 0.5:
                relief_min = max(float(p.get('sat_mix_relief_min', sat_lo)), sat_lo)
                floor_k = np.clip(t_need_ahu, relief_min, max(mix_floor, relief_min))
            else:
                floor_k = np.full(K, mix_floor)
            s = np.where(H > 0.0, np.maximum(s, floor_k), s)
            sat = np.where(has_cool, s, sat_hi_native)
        sat = np.clip(sat, sat_lo, sat_hi_native)
        recirc = np.full(K, RECIRC_MAX)
        if p['econ_on'] > 0.5:
            cooling = on & (C > 0.0) & (H <= 0.0) & np.isfinite(oat)
            adv = T_ret - oat_f
            econ = cooling & (adv > P_FLOOR_PA * ECON_K_PER_PA)
            with np.errstate(divide='ignore', invalid='ignore'):
                f_oa = np.where(econ, (T_ret - sat) / np.where(adv > 0, adv, 1.0), 0.0)
            f_oa = np.clip(f_oa, 1.0 - RECIRC_MAX, 1.0)
            recirc = np.where(econ, 1.0 - f_oa, RECIRC_MAX)
        recirc = np.where(on & fl_ahu, 0.0, recirc)
        self.recirc_prev = recirc
        mixed = recirc * T_ret + (1.0 - recirc) * oat_f
        t_sa = np.minimum(mixed, sat)
        any_heat_now = bool(V) and bool((heat_zone & on[self.z_a]).any())
        if any_heat_now or (mode == self.PRECOND and deficit_h > 0.0):
            self.heat_timer = int(p['heat_season_steps'])
        else:
            self.heat_timer = max(self.heat_timer - 1, 0)
        tw = p['tw_hot_k'] if self.heat_timer > 0 else p['tw_idle_k']
        tw = float(np.clip(tw, self.tw_rng[0], self.tw_rng[1]))
        valve = np.zeros(V)
        dp_bar = p['dp_lo_bar']
        pump_on = False
        if V:
            t_sa_z = t_sa[self.z_a]
            zone_on = on[self.z_a]
            dT_c = np.maximum(T - t_sa_z, 0.5)
            F_cool = np.where(cool_zone, q_c / dT_c, 0.0)
            dT_h = np.maximum(t_disch_max - T, 0.5)
            F_heat = np.where(heat_zone, q_h / dT_h, 0.0)
            F_req = np.maximum(np.maximum(F_cool, F_heat), F_min)
            F_req = np.where(flush_eff, np.maximum(F_req, F_floor), F_req)
            F_req = np.where(zone_on, F_req, F_min)
            f_req = np.clip(F_req / F_design, F_MIN, 1.0)
            f_max = np.zeros(K)
            np.maximum.at(f_max, self.z_a, f_req)
            f_max = np.maximum(f_max, F_FLOOR100)
            p_cmd = np.clip(P_MAX_PA * f_max ** 2, P_FLOOR_PA, min(P_MAX_PA, self.p_rng[1]))
            p_cmd = np.where(on, p_cmd, P_FLOOR_PA)
            f_real = np.sqrt(p_cmd / P_MAX_PA)
            damper = np.clip(f_req / f_real[self.z_a], DAMPER_FLOOR, 1.0)
            damper = np.where(zone_on, damper, 0.0)
            F_act = F_design * np.clip(damper, DAMPER_FLOOR, 1.0) * f_real[self.z_a]
            neutral = np.zeros(V, dtype=bool)
            if float(p.get('sb_neutral', 0.0)) > 0.5 and self.heat_timer > 0:
                neutral = zone_on & is_sb & ~heat_zone & ~cool_zone & (T < lo_pre) & (T > t_sa_z + 0.5)
                if float(p.get('sb_neutral_cold', 0.0)) > 0.5:
                    neutral &= np.isfinite(oat[self.z_a]) & (oat[self.z_a] <= floor_z)
            if any_heat_now or neutral.any():
                t_disch = np.clip(T + q_h / np.maximum(F_act, 1.0), t_sa_z, t_disch_max)
                t_disch = np.where(neutral, np.minimum(T, t_disch_max), t_disch)
                gap = np.maximum(tw_obs - t_sa_z, 1.0)
                w_need = np.where((heat_zone | neutral) & zone_on, F_act * np.clip((t_disch - t_sa_z) / gap, 0.0, 1.0), 0.0)
                w_max = float(w_need.max())
                target = max(p['valve_target'], 0.05)
                dp_bar = (w_max / (target * cap1)) ** 2
                dp_bar = float(np.clip(dp_bar, p['dp_lo_bar'], min(p['dp_hi_bar'], self.dp_rng[1])))
                valve = np.clip(w_need / (cap1 * math.sqrt(dp_bar)), 0.0, 1.0)
                pump_on = bool(valve.max() > 0.0)
        else:
            damper = np.zeros(0)
            p_cmd = np.full(K, P_FLOOR_PA)
        for k in range(K):
            cont[self.ahu_temp_idx[k]] = self._norm(float(sat[k]), *self.sat_rng)
            if self.ahu_press_idx[k] >= 0:
                cont[self.ahu_press_idx[k]] = self._norm(float(p_cmd[k]), *self.p_rng) if on[k] else -1.0
            if self.ahu_recirc_idx[k] >= 0:
                cont[self.ahu_recirc_idx[k]] = 2.0 * float(recirc[k]) - 1.0
            disc[k] = 1 if on[k] else 0
        if V:
            md_ = self.z_d >= 0
            cont[self.z_d[md_]] = 2.0 * damper[md_] - 1.0
            mv_ = self.z_v >= 0
            cont[self.z_v[mv_]] = 2.0 * valve[mv_] - 1.0
        for s_ in self.orphan_slots:
            cont[s_] = -1.0
        if self.water_temp_idx >= 0:
            cont[self.water_temp_idx] = self._norm(tw, *self.tw_rng)
        if self.water_press_idx >= 0:
            cont[self.water_press_idx] = self._norm(dp_bar, *self.dp_rng) if pump_on else -1.0
        if 0 <= self.water_disc_idx < self.n_discrete:
            disc[self.water_disc_idx] = 1 if pump_on else 0
        cont = np.nan_to_num(cont, nan=0.0, posinf=1.0, neginf=-1.0)
        np.clip(cont, -1.0, 1.0, out=cont)
        if self._dbg is not None:
            try:
                rh = float(self.rate_h_z.min()) if per_zone_start else self.rate_h
                rc = float(self.rate_c_z.min()) if per_zone_start else self.rate_c
                self._dbg.write(f'{self.step_count},{(-1 if hod is None else hod):.3f},{(-1 if dow is None else dow):.2f},{int(now)},{int(soon)},{int(occupied)},{mode},{int(self.holiday)},{self._lead_dbg:.2f},{rh:.2f},{rc:.2f},{deficit_h:.2f},{deficit_c:.2f},{(T.min() if V else 0):.2f},{(T.max() if V else 0):.2f},{(T.mean() if V else 0):.2f},{int(heat_zone.sum())},{int(cool_zone.sum())},{p_cmd.max():.0f},{int(on.sum())},{tw:.0f},{dp_bar:.1f},{int(pump_on)},{(valve.max() if V else 0):.2f},{(damper.max() if V else 0):.2f},{sat.min():.1f},{recirc.min():.2f},{int((zone_mode == self.PRECOND).sum())}\n')
            except (OSError, ValueError):
                pass
        return {'continuous_action': cont.astype(np.float32), 'discrete_action': disc.astype(np.int32)}
import sys as _sys
_sys.path.append('/kaggle/input/competitions/neurips-2026-smart-buildings/kaggle_evaluation')
from kaggle_evaluation import smart_buildings_inference_server
COMPETITION_DATA_FOLDER = '/kaggle/input/competitions/neurips-2026-smart-buildings/'

class TransferPolicy(smart_buildings_inference_server.Policy):

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        self._impl = _SADRPolicy(building_meta_data, action_spec)
        print(f'SADR v7 controlling {self._impl.K} AHUs', flush=True)

    def get_action(self, obs):
        return self._impl.get_action(obs)
smart_buildings_inference_server.SmartBuildingsInferenceServer(TransferPolicy).run(competition_data_folder=COMPETITION_DATA_FOLDER)
