"""SADR: Schedule-Aware Demand-based Reset controller for the SB26 challenge (v5, final).

Drop-in replacement for ``smart_buildings/baselines/transfer_policy.py`` in the
official starter kit. Pure numpy + stdlib, deterministic, no file or network
access, shape-agnostic (any number of air handlers K and zones V). Every slot
of both action vectors is written explicitly on every step; every value is
clipped to the declared range, and non-finite inputs fall back to safe values.

The controller is organised around three facts about the plant and the score
that hold for every generated building:

  * The comfort term is charged only while a zone is occupied, and occupants
    are only present on weekday comfort hours.  Outside those hours the only
    cost is energy, so the plant is shut down (SETBACK) except to bound the
    fabric drift, and brought back just in time (PRECONDITION) with an
    optimum-start lead that is re-estimated from each morning's recovery.
    A weekday on which nobody has arrived by mid-morning is a holiday in the
    occupancy model, so it is treated as unoccupied.
  * Fan power is flow x pressure, and zone flow goes as damper x sqrt(pressure),
    so the cheapest way to move a given amount of air is wide dampers at the
    200 Pa ventilation floor.  Static pressure is therefore reset
    (trim-and-respond) so that the most demanding damper is fully open, and is
    only raised above the floor when a zone's error is large.
  * Heat comes only from the VAV reheat coils, whose discharge is capped at
    308.15 K, and gas is billed as heat delivered plus a small tank loss.  The
    hot water loop is therefore run hot whenever the building is in heating
    season (hotter water does not cost more gas per joule delivered), valves
    are sized from the heat each zone needs, and the loop differential
    pressure is reset so the most-open valve sits near full travel.

Per step, vectorised over zones:

  1. Mode (OCCUPIED / PRECONDITION / SETBACK) from the comfort-mode flags, the
     cyclic time features, and the building occupancy count.
  2. Zone demands from each zone's temperature against the mode's band
     (sensor setpoints while occupied, comfort window while preconditioning,
     widened eco window while set back), in [0, 1] with a second stage for
     large errors.
  3. Air handler: runs iff some served zone has demand (dwell hysteresis);
     supply-air temperature reset from cooling demand (raised when the same
     handler also has heating zones); static pressure from the maximum flow
     demand; recirculation from an economiser rule with the fan-power
     break-even implied by the simulator's exhaust-fan model.
  4. Zones: dampers from flow demand; reheat valves sized from the water
     capacity rate each heating zone needs, given the discharge-air limit.
  5. Hot water: pump iff some valve is open; differential pressure from the
     largest valve demand; supply water temperature hot in heating season,
     idle otherwise.

All gains and bounds live in ``DEFAULT_PARAMS``.  A JSON file named by the
environment variable ``SADR_PARAMS_JSON`` (used only by the local tuning
harness) overrides them; when the variable is unset the defaults are used.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from typing import Any

import numpy as np

# Native action ranges from the shipped action normalisers (identical in every
# generated config; read from metadata when present, these are the fallbacks).
SAT_MIN_K = 285.0
SAT_MAX_K = 305.0
P_MAX_PA = 2000.0          # design static pressure: 100% damper gives design flow
P_FLOOR_PA = 200.0         # simulator floor while a handler runs
DAMPER_FLOOR = 0.1         # simulator floor while a handler runs
RECIRC_MAX = 0.7           # simulator cap
TW_MIN_K = 310.0
TW_MAX_K = 350.0
DP_MAX_BAR = 20.0
DISCHARGE_MAX_K = 308.15   # VAV discharge-air limit in the simulator
AIR_RHO_CP = 1.2 * 1006.0  # J/m3/K
WATER_RHO_CP = 1000.0 * 4180.0
# Economiser break-even, K of outside-air advantage per Pa of static pressure:
# COP / (fan_eff * rho * cp) = 3.5 / (0.9 * 1.2 * 1006).
ECON_K_PER_PA = 0.00322

F_FLOOR100 = math.sqrt(P_FLOOR_PA / P_MAX_PA)   # flow fraction, 100% damper at floor pressure
F_MIN = DAMPER_FLOOR * F_FLOOR100               # flow fraction, 10% damper at floor pressure

DEFAULT_PARAMS: dict[str, float] = {
    # --- band handling (K) ---
    "margin_occ": 0.3,        # inside the sensor band at which control starts (occupied)
    "margin_pre": 0.8,        # same, while preconditioning (target comfort band)
    "night_low_ext": 8.0,     # drift allowed below the eco heating setpoint while set back
    "night_high_ext": 6.0,    # drift allowed above the eco cooling setpoint while set back
    "sb_hyst_k": 1.0,         # setback burst: heat/cool a zone from the floor until this far inside
    "q_sb_w": 4000.0,         # net heat (W) requested per zone during a setback burst
    "e_full_k": 1.0,          # error at which stage-1 demand saturates
    "e_full2_k": 4.0,         # error at which stage-2 (escalation) demand saturates
    # --- optimum start ---
    "lead_base_h": 0.5,       # fixed part of the preconditioning lead (h)
    "lead_min_h": 0.75,
    "lead_max_h": 8.0,
    "rate0_kph": 2.0,         # initial recovery-rate estimate (K/h), heating and cooling
    "rate_min_kph": 0.4,
    "rate_max_kph": 8.0,
    "rate_ema": 0.5,          # weight of the newest observed recovery rate
    "lead_safety": 1.3,       # lead uses rate / safety
    "holiday_check_h": 7.0,   # weekday hour by which somebody must have arrived
    # --- zone PI loops (net heat into the zone air, W) ---
    "kq_w_per_k": 400.0,      # proportional gain: W of net heat per K of error
    "ki_w_per_k_step": 120.0,  # integral gain: W added per K of error per 5-min step
    "i_decay_mult": 1.0,      # integral unwinding speed when the zone is past its target
    "q_cap_w": 12000.0,       # cap on net heat (either sign) a zone may ask for
    "q_on_w": 50.0,           # a zone with |Q| above this is "in demand"
    # --- air handler ---
    "min_on_steps": 3,        # dwell (5-min steps) after a start
    "min_off_steps": 2,       # dwell after a stop
    "sat_cool_hi": 285.0,     # SAT ceiling (K) while cooling; 285 = always the coldest supply (v5)
    "sat_mix_floor": 292.0,   # SAT floor while the same handler also has heating zones
    "disch_margin_k": 1.0,    # keep discharge air this far below the 308.15 K limit
    "econ_on": 1.0,
    # --- zones ---
    "kv_valve": 0.108,        # reheat valve Kv at full open (m3/h/sqrt(bar)), kit default
    "valve_target": 0.9,      # dP reset aims the most-open valve here
    # --- hot water ---
    "dp_lo_bar": 0.1,
    "dp_hi_bar": 20.0,
    "tw_idle_k": 310.0,
    "tw_hot_k": 350.0,
    "heat_season_steps": 288, # keep the loop hot this long after the last heating demand
}


def _num_suffix(name: str) -> int:
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else 0


def _clip01(x):
    return np.clip(x, 0.0, 1.0)


class TransferPolicy:
    """Schedule-aware demand-based reset (SADR) rule-based controller."""

    name = "transfer"

    OCCUPIED, PRECOND, SETBACK = 0, 1, 2

    def __init__(
        self,
        building_meta_data: Mapping[str, Any],
        action_spec: Any,
        params: Mapping[str, float] | None = None,
    ) -> None:
        md = building_meta_data
        self.metadata = md
        self.action_spec = action_spec
        self.p = dict(DEFAULT_PARAMS)
        if params:
            self.p.update(params)
        env_path = os.environ.get("SADR_PARAMS_JSON")
        if env_path:
            try:
                with open(env_path) as f:
                    self.p.update(json.load(f))
            except (OSError, ValueError):
                pass

        self.n_discrete = int(md["n_discrete_action"])
        self.n_continuous = int(md["n_continuous_action"])
        names = list(md["observation_field_names"])
        self.ix = {n: i for i, n in enumerate(names)}

        temp_indices = list(md["temp_indices"])
        pressure_indices = list(md["pressure_indices"])
        recirc_indices = list(md["recirculation_indices"])
        water_indices = list(md["water_indices"])
        zone_action_indices = md["zone_action_indices"]
        assignments = md.get("ahu_zone_assignments", {}) or {}

        # ---- air handlers, in the positional order of the action lists ----
        ahu_ids = sorted(assignments.keys(), key=_num_suffix)
        self.K = len(temp_indices)
        if len(ahu_ids) > self.K:
            ahu_ids = ahu_ids[: self.K]
        self.ahu_temp_idx = np.array(temp_indices[: self.K], dtype=int)
        self.ahu_press_idx = np.array(
            [pressure_indices[i] if i < len(pressure_indices) else -1 for i in range(self.K)], dtype=int)
        self.ahu_recirc_idx = np.array(
            [recirc_indices[i] if i < len(recirc_indices) else -1 for i in range(self.K)], dtype=int)
        self.ahu_oat_idx = np.array([
            self.ix.get(f"ahs_{aid}_outside_air_temperature_sensor", -1) for aid in ahu_ids
        ] + [-1] * (self.K - len(ahu_ids)), dtype=int)
        bare = [n for n in names if n.endswith("outside_air_temperature_sensor") and not n.startswith("ahs_")]
        self.bare_oat_idx = self.ix[bare[0]] if bare else -1
        onorm = md.get("observation_normalization_metadata", {}) or {}
        oat_n = onorm.get("outside_air_temperature_sensor", {})
        self.oat_mean = float(oat_n.get("sample_mean", 295.0))
        self.oat_std = float(oat_n.get("sample_std", 10.0)) or 10.0

        # ---- zones ----
        zt = onorm.get("zone_air_temperature_sensor", {})
        self.zt_mean = float(zt.get("sample_mean", 295.0))
        self.zt_std = float(zt.get("sample_std", 5.0)) or 5.0

        vav_to_ahu: dict[str, int] = {}
        for a, aid in enumerate(ahu_ids):
            for room in assignments[aid]:
                vav_to_ahu[room.replace("room_", "VAV_")] = a

        z_t, z_lo, z_hi, z_d, z_v, z_a, z_mf = [], [], [], [], [], [], []
        self.orphan_slots: list[int] = []  # action slots of zones we cannot see or place
        for vav_id, acts in zone_action_indices.items():
            d_idx = acts.get("supply_air_damper_percentage_command")
            v_idx = acts.get("reheat_valve_percentage_command")
            t_idx = self.ix.get(f"{vav_id}_zone_air_temperature_sensor")
            a_idx = vav_to_ahu.get(vav_id)
            if t_idx is None or a_idx is None:
                for s in (d_idx, v_idx):
                    if s is not None:
                        self.orphan_slots.append(int(s))
                continue
            z_t.append(t_idx)
            z_lo.append(self.ix.get(f"{vav_id}_zone_air_heating_temperature_setpoint_sensor", -1))
            z_hi.append(self.ix.get(f"{vav_id}_zone_air_cooling_temperature_setpoint_sensor", -1))
            z_d.append(-1 if d_idx is None else int(d_idx))
            z_v.append(-1 if v_idx is None else int(v_idx))
            z_a.append(a_idx)
            z_mf.append(self.ix.get(f"{vav_id}_supply_air_flowrate_setpoint", -1))
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

        # ---- hot water system ----
        self.water_temp_idx = int(water_indices[0]) if water_indices else -1
        self.water_press_idx = int(pressure_indices[-1]) if len(pressure_indices) > self.K else -1
        self.water_disc_idx = self.n_discrete - 1
        self.hws_temp_obs_idx = self.ix.get("hws_supply_water_temperature_sensor", -1)

        # ---- schedule & time ----
        cw = md.get("comfort_temp_window", (294.0, 297.0))
        ew = md.get("eco_temp_window", (289.0, 298.0))
        self.comfort_lo, self.comfort_hi = float(cw[0]), float(cw[1])
        self.eco_lo, self.eco_hi = float(ew[0]), float(ew[1])
        self.morning_start = float(md.get("morning_start_hour", 6))
        self.evening_start = float(md.get("evening_start_hour", 19))
        self.hod_sin = self.ix.get("hod_sin_000", -1)
        self.hod_cos = self.ix.get("hod_cos_000", -1)
        self.dow_sin = self.ix.get("dow_sin_000", -1)
        self.dow_cos = self.ix.get("dow_cos_000", -1)
        self.now_idx = self.ix.get("comfort_mode_now", -1)
        self.soon_idx = self.ix.get("comfort_mode_soon", -1)
        self.occ_idx = self.ix.get("num_occupants", -1)

        # ---- action normalisation (fallbacks match every shipped config) ----
        anorm = md.get("action_normalization_metadata", {}) or {}

        def rng(key_sub, lo, hi):
            for k, v in anorm.items():
                if key_sub in k:
                    try:
                        return float(v["min_native_value"]), float(v["max_native_value"])
                    except (KeyError, TypeError, ValueError):
                        return lo, hi
            return lo, hi

        self.sat_rng = rng("supply_air_temperature_setpoint", SAT_MIN_K, SAT_MAX_K)
        self.p_rng = rng("static_pressure_setpoint", 0.0, P_MAX_PA)
        self.tw_rng = rng("supply_water_temperature_setpoint", TW_MIN_K, TW_MAX_K)
        self.dp_rng = rng("differential_pressure_setpoint", 0.0, DP_MAX_BAR)

        # Optional per-step trace for local development only (never set on Kaggle).
        self._dbg = None
        dbg_path = os.environ.get("SADR_DEBUG_LOG")
        if dbg_path:
            try:
                self._dbg = open(dbg_path, "w")
                self._dbg.write("step,hod,dow,now,soon,occupied,mode,holiday,lead_h,rate_h,rate_c,"
                                "deficit_h,deficit_c,Tmin,Tmax,Tmean,n_heat,n_cool,maxP,n_on,tw,dp,pump,"
                                "max_valve,max_damper,sat_min,recirc_min\n")
            except OSError:
                self._dbg = None

        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        p = self.p
        self.ahu_on = np.zeros(self.K, dtype=bool)
        self.dwell = np.zeros(self.K, dtype=int)
        self.recirc_prev = np.full(self.K, RECIRC_MAX)
        self.I_h = np.zeros(max(self.V, 1))   # integral of heating demand, W
        self.I_c = np.zeros(max(self.V, 1))   # integral of cooling demand, W
        self.sb_latch_h = np.zeros(max(self.V, 1), dtype=bool)  # setback burst latches
        self.sb_latch_c = np.zeros(max(self.V, 1), dtype=bool)
        self.heat_timer = 0
        self.step_count = 0
        self.occ_min = math.inf
        self.last_hod = None
        self.seen_occ_today = False
        self.holiday = False
        self.mode = self.SETBACK
        # optimum start
        self.rate_h = float(p["rate0_kph"])
        self.rate_c = float(p["rate0_kph"])
        self.pre_active = False
        self.pre_t0 = 0            # step index at which preconditioning started
        self.pre_deficit0 = 0.0
        self.pre_kind = 0          # +1 heating deficit, -1 cooling deficit
        self.pre_reached_step = -1

    @staticmethod
    def _norm(x, lo, hi):
        if hi <= lo:
            return 0.0
        return 2.0 * (x - lo) / (hi - lo) - 1.0

    def _cyclic(self, obs, si, ci, period):
        if si < 0 or ci < 0:
            return None
        s, c = float(obs[si]), float(obs[ci])
        if not (math.isfinite(s) and math.isfinite(c)):
            return None
        ang = math.atan2(s, c)
        if ang < 0:
            ang += 2.0 * math.pi
        return period * ang / (2.0 * math.pi)

    def _oat(self, obs) -> np.ndarray:
        """Outside air temperature (K) per AHU (NaN when unavailable)."""
        out = np.full(self.K, np.nan)
        m = self.ahu_oat_idx >= 0
        if m.any():
            out[m] = obs[self.ahu_oat_idx[m]]
        if self.bare_oat_idx >= 0:
            v = float(obs[self.bare_oat_idx]) * self.oat_std + self.oat_mean
            out[~m] = v
        out = np.where(np.isfinite(out) & (out > 150.0) & (out < 350.0), out, np.nan)
        return out

    # -------------------------------------------------------------- the step
    def get_action(self, obs: np.ndarray) -> dict[str, np.ndarray]:
        p = self.p
        obs = np.asarray(obs, dtype=np.float64)
        cont = np.zeros(self.n_continuous, dtype=np.float32)
        disc = np.zeros(self.n_discrete, dtype=np.int32)
        K, V = self.K, self.V
        self.step_count += 1

        # ---------------- time & flags ----------------
        hod = self._cyclic(obs, self.hod_sin, self.hod_cos, 24.0)
        dow = self._cyclic(obs, self.dow_sin, self.dow_cos, 7.0)
        if self.now_idx >= 0 and math.isfinite(obs[self.now_idx]):
            now = float(obs[self.now_idx]) > 0.5
        else:  # reconstruct from the schedule
            now = (hod is not None and dow is not None and dow < 5.0
                   and self.morning_start <= hod < self.evening_start)
        soon = self.soon_idx >= 0 and math.isfinite(obs[self.soon_idx]) and float(obs[self.soon_idx]) > 0.5

        # day boundary bookkeeping
        if hod is not None:
            if self.last_hod is not None and hod < self.last_hod - 12.0:
                self.seen_occ_today = False
                self.holiday = False
            self.last_hod = hod

        # occupancy: the count is affinely normalised with an unknown constant,
        # so detect "somebody is here" relative to the running minimum.
        occupied = False
        if self.occ_idx >= 0 and math.isfinite(obs[self.occ_idx]):
            o = float(obs[self.occ_idx])
            if self.step_count > 1:
                self.occ_min = min(self.occ_min, o)
                occupied = o > self.occ_min + 2e-3
        if occupied:
            self.seen_occ_today = True
            self.holiday = False

        # ---------------- zone temperatures & sensor band ----------------
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

        # ---------------- mode ----------------
        deficit_h = deficit_c = 0.0
        if V:
            deficit_h = float(np.max(np.maximum(0.0, (self.comfort_lo + p["margin_pre"]) - T)))
            deficit_c = float(np.max(np.maximum(0.0, T - (self.comfort_hi - p["margin_pre"]))))
        if now:
            if (hod is not None and hod >= p["holiday_check_h"] and not self.seen_occ_today
                    and self.occ_idx >= 0):
                self.holiday = True
            mode = self.SETBACK if (self.holiday and not occupied) else self.OCCUPIED
        else:
            precondition = bool(soon)
            if hod is not None and dow is not None:
                hours_to_start = (self.morning_start - hod) % 24.0
                day_next = dow if hod < self.morning_start else (dow + 1.0) % 7.0
                if day_next < 5.0:
                    safety = max(p["lead_safety"], 1e-3)
                    lead = p["lead_base_h"] + max(
                        deficit_h / max(self.rate_h / safety, 1e-3),
                        deficit_c / max(self.rate_c / safety, 1e-3))
                    lead = min(max(lead, p["lead_min_h"]), p["lead_max_h"])
                    self._lead_dbg = lead
                    if hours_to_start <= lead:
                        precondition = True
            mode = self.PRECOND if (precondition or occupied) else self.SETBACK

        # optimum-start learning: track one preconditioning episode per morning
        if mode == self.PRECOND and not self.pre_active and self.mode != self.OCCUPIED:
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
                # preconditioning ended (comfort hours began, or a setback resumed)
                if self.pre_deficit0 >= 0.5:
                    end_step = self.pre_reached_step if self.pre_reached_step > 0 else self.step_count
                    hours = max((end_step - self.pre_t0) / 12.0, 1.0 / 12.0)
                    recovered = self.pre_deficit0 - (0.0 if self.pre_reached_step > 0 else cur)
                    if recovered > 0.0:
                        r_obs = recovered / hours
                        r_obs = min(max(r_obs, p["rate_min_kph"]), p["rate_max_kph"])
                        a = p["rate_ema"]
                        if self.pre_kind > 0:
                            self.rate_h = (1 - a) * self.rate_h + a * r_obs
                        else:
                            self.rate_c = (1 - a) * self.rate_c + a * r_obs
                    elif mode == self.OCCUPIED:
                        # did not recover at all: assume a much slower plant
                        if self.pre_kind > 0:
                            self.rate_h = max(self.rate_h * 0.5, p["rate_min_kph"])
                        else:
                            self.rate_c = max(self.rate_c * 0.5, p["rate_min_kph"])
                self.pre_active = False
        self.mode = mode

        # ---------------- band for this mode ----------------
        if mode == self.OCCUPIED:
            lo = lo_s + p["margin_occ"]
            hi = hi_s - p["margin_occ"]
        elif mode == self.PRECOND:
            lo = np.full(V, self.comfort_lo + p["margin_pre"])
            hi = np.full(V, self.comfort_hi - p["margin_pre"])
        else:
            lo = np.full(V, self.eco_lo - p["night_low_ext"])
            hi = np.full(V, self.eco_hi + p["night_high_ext"])
        if V:
            mid = 0.5 * (lo + hi)
            lo = np.minimum(lo, mid - 0.1)
            hi = np.maximum(hi, mid + 0.1)

        # ---------------- zone PI loops on net heat (W into the zone air) ----------------
        # Positive e_h: zone below its heating target; positive e_c: above its cooling
        # target.  Each loop regulates to its own target, so inside the deadband both
        # integrals unwind and the zone free-floats.
        e_h = lo - T
        e_c = T - hi
        kq = max(p["kq_w_per_k"], 0.0)
        ki = max(p["ki_w_per_k_step"], 0.0)
        q_cap = max(p["q_cap_w"], 100.0)
        if V and mode == self.SETBACK:
            # Burst heating/cooling against a wide floor: a running handler always pays
            # the ventilation load of every served zone, so the cheap way to bound the
            # drift is to stay off and, when a zone crosses the floor, heat it hard until
            # it is sb_hyst_k inside, then switch off again.  No steady load is held.
            self.I_h[:] = 0.0
            self.I_c[:] = 0.0
            hyst = max(p["sb_hyst_k"], 0.1)
            self.sb_latch_h = (self.sb_latch_h | (e_h > 0.0)) & (e_h > -hyst)
            self.sb_latch_c = (self.sb_latch_c | (e_c > 0.0)) & (e_c > -hyst)
            q_sb = min(max(p["q_sb_w"], 100.0), q_cap)
            heat_zone = self.sb_latch_h & ~self.sb_latch_c
            cool_zone = self.sb_latch_c & ~self.sb_latch_h
            q_h = np.where(heat_zone, q_sb, 0.0)
            q_c = np.where(cool_zone, q_sb, 0.0)
        elif V:
            self.sb_latch_h[:] = False
            self.sb_latch_c[:] = False
            dec = max(p["i_decay_mult"], 0.0)
            dI_h = np.where(e_h > 0.0, ki * e_h, dec * ki * e_h)
            dI_c = np.where(e_c > 0.0, ki * e_c, dec * ki * e_c)
            self.I_h = np.clip(self.I_h + dI_h, 0.0, q_cap)
            self.I_c = np.clip(self.I_c + dI_c, 0.0, q_cap)
            q_h = np.clip(kq * np.maximum(e_h, 0.0) + self.I_h, 0.0, q_cap)
            q_c = np.clip(kq * np.maximum(e_c, 0.0) + self.I_c, 0.0, q_cap)
            # a zone cannot be heated and cooled at once: the larger request wins
            heat_zone = (q_h > q_c) & (q_h > p["q_on_w"])
            cool_zone = (q_c >= q_h) & (q_c > p["q_on_w"])
            q_h = np.where(heat_zone, q_h, 0.0)
            q_c = np.where(cool_zone, q_c, 0.0)
        else:
            q_h = q_c = np.zeros(0)
            heat_zone = cool_zone = np.zeros(0, dtype=bool)

        # ---------------- per-AHU aggregates ----------------
        if V:
            H = np.where(self.ahu_has_zones, (self.member * q_h[None, :]).max(axis=1), 0.0)
            C = np.where(self.ahu_has_zones, (self.member * q_c[None, :]).max(axis=1), 0.0)
            T_ret = (self.member * T[None, :]).sum(axis=1) / self.ahu_zone_count
        else:
            H = C = np.zeros(K)
            T_ret = np.full(K, self.zt_mean)
        D = np.maximum(H, C)

        # run / stop with dwell hysteresis
        want_on = D > p["q_on_w"]
        want_off = D <= 0.0
        can_switch = self.dwell >= np.where(self.ahu_on, p["min_on_steps"], p["min_off_steps"])
        turn_on = ~self.ahu_on & want_on & can_switch
        turn_off = self.ahu_on & want_off & can_switch
        new_on = (self.ahu_on | turn_on) & ~turn_off
        self.dwell = np.where(new_on == self.ahu_on, self.dwell + 1, 0)
        self.ahu_on = new_on
        on = self.ahu_on

        # ---------------- design flow per zone & floor-pressure capacity ----------------
        oat = self._oat(obs)
        oat_f = np.where(np.isfinite(oat), oat, T_ret)
        if V:
            design_flow = np.where(self.z_mf >= 0, obs[np.maximum(self.z_mf, 0)], 2.0)
            design_flow = np.where(np.isfinite(design_flow) & (design_flow > 0.01) & (design_flow < 100.0),
                                   design_flow, 2.0)
            F_floor = AIR_RHO_CP * design_flow * F_FLOOR100     # W/K at 100% damper, floor pressure
            F_min = AIR_RHO_CP * design_flow * F_MIN            # W/K at the damper floor
        else:
            design_flow = F_floor = F_min = np.zeros(0)

        # ---------------- supply air temperature reset (per AHU) ----------------
        # Cooling: the coldest supply any cooling zone needs to be served at 100%
        # damper and floor pressure, bounded to [285, sat_cool_hi]; floored when the
        # handler also has heating zones.  Heating only: coil off (SAT at maximum).
        sat_lo, sat_hi_native = self.sat_rng
        sat_hi = min(max(p["sat_cool_hi"], sat_lo), sat_hi_native)
        sat = np.full(K, sat_hi_native)
        if V:
            t_need = np.where(cool_zone, T - q_c / np.maximum(F_floor, 1.0), np.inf)
            t_need_ahu = np.full(K, np.inf)
            np.minimum.at(t_need_ahu, self.z_a, t_need)
            has_cool = C > 0.0
            s = np.clip(t_need_ahu, sat_lo, sat_hi)
            # the mixed-handler floor is independent of the cooling ceiling, so a cold SAT for
            # cooling-only handlers (v5) does not remove the reheat protection on mixed handlers
            s = np.where(H > 0.0, np.maximum(s, min(p["sat_mix_floor"], sat_hi_native)), s)
            sat = np.where(has_cool, s, sat_hi_native)
        sat = np.clip(sat, sat_lo, sat_hi_native)

        # ---------------- economiser ----------------
        recirc = np.full(K, RECIRC_MAX)
        # provisional pressure (floor) for the break-even; refined below
        if p["econ_on"] > 0.5:
            cooling = on & (C > 0.0) & (H <= 0.0) & np.isfinite(oat)
            adv = T_ret - oat_f
            econ = cooling & (adv > P_FLOOR_PA * ECON_K_PER_PA)
            with np.errstate(divide="ignore", invalid="ignore"):
                f_oa = np.where(econ, (T_ret - sat) / np.where(adv > 0, adv, 1.0), 0.0)
            f_oa = np.clip(f_oa, 1.0 - RECIRC_MAX, 1.0)
            recirc = np.where(econ, 1.0 - f_oa, RECIRC_MAX)
        self.recirc_prev = recirc

        # estimated coil-entering (supply) air temperature per AHU
        mixed = recirc * T_ret + (1.0 - recirc) * oat_f
        t_sa = np.minimum(mixed, sat)

        # ---------------- hot water temperature ----------------
        tw_obs = float(obs[self.hws_temp_obs_idx]) if self.hws_temp_obs_idx >= 0 else float("nan")
        if not (math.isfinite(tw_obs) and 273.0 < tw_obs < 400.0):
            tw_obs = 340.0
        any_heat_now = bool(V) and bool((heat_zone & on[self.z_a]).any())
        if any_heat_now or (mode == self.PRECOND and deficit_h > 0.0):
            self.heat_timer = int(p["heat_season_steps"])
        else:
            self.heat_timer = max(self.heat_timer - 1, 0)
        tw = p["tw_hot_k"] if self.heat_timer > 0 else p["tw_idle_k"]
        tw = float(np.clip(tw, self.tw_rng[0], self.tw_rng[1]))

        # ---------------- zone flows, dampers, pressure, valves ----------------
        valve = np.zeros(V)
        dp_bar = p["dp_lo_bar"]
        pump_on = False
        if V:
            t_sa_z = t_sa[self.z_a]
            zone_on = on[self.z_a]
            # cooling: flow so that F * (T - t_sa) = q_c
            dT_c = np.maximum(T - t_sa_z, 0.5)
            F_cool = np.where(cool_zone, q_c / dT_c, 0.0)
            # heating: the discharge limit bounds the heat per unit flow
            t_disch_max = DISCHARGE_MAX_K - max(p["disch_margin_k"], 0.0)
            dT_h = np.maximum(t_disch_max - T, 0.5)
            F_heat = np.where(heat_zone, q_h / dT_h, 0.0)
            F_req = np.maximum(np.maximum(F_cool, F_heat), F_min)
            F_req = np.where(zone_on, F_req, F_min)
            f_req = np.clip(F_req / (AIR_RHO_CP * design_flow), F_MIN, 1.0)   # fraction of design flow
            f_max = np.zeros(K)
            np.maximum.at(f_max, self.z_a, f_req)
            f_max = np.maximum(f_max, F_FLOOR100)
            p_cmd = np.clip(P_MAX_PA * f_max ** 2, P_FLOOR_PA, min(P_MAX_PA, self.p_rng[1]))
            p_cmd = np.where(on, p_cmd, P_FLOOR_PA)
            f_real = np.sqrt(p_cmd / P_MAX_PA)
            damper = np.clip(f_req / f_real[self.z_a], DAMPER_FLOOR, 1.0)
            damper = np.where(zone_on, damper, 0.0)
            # actual flow delivered at the commanded damper and pressure
            F_act = AIR_RHO_CP * design_flow * np.clip(damper, DAMPER_FLOOR, 1.0) * f_real[self.z_a]
            # reheat: discharge temperature that delivers q_h net, then the water
            # capacity rate that produces it, then the valve at the chosen dP
            if any_heat_now:
                t_disch = np.clip(T + q_h / np.maximum(F_act, 1.0), t_sa_z, t_disch_max)
                gap = np.maximum(tw_obs - t_sa_z, 1.0)
                w_need = np.where(heat_zone & zone_on,
                                  F_act * np.clip((t_disch - t_sa_z) / gap, 0.0, 1.0), 0.0)
                kv = max(p["kv_valve"], 1e-4)
                cap1 = WATER_RHO_CP * kv / 3600.0            # W/K per unit valve per sqrt(bar)
                w_max = float(w_need.max())
                target = max(p["valve_target"], 0.05)
                dp_bar = (w_max / (target * cap1)) ** 2
                dp_bar = float(np.clip(dp_bar, p["dp_lo_bar"], min(p["dp_hi_bar"], self.dp_rng[1])))
                valve = np.clip(w_need / (cap1 * math.sqrt(dp_bar)), 0.0, 1.0)
                pump_on = bool(valve.max() > 0.0)
        else:
            damper = np.zeros(0)
            p_cmd = np.full(K, P_FLOOR_PA)

        # ---------------- scatter into the action vectors ----------------
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
        for s in self.orphan_slots:
            cont[s] = -1.0
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
                self._dbg.write(
                    f"{self.step_count},{-1 if hod is None else hod:.3f},{-1 if dow is None else dow:.2f},"
                    f"{int(now)},{int(soon)},{int(occupied)},{mode},{int(self.holiday)},"
                    f"{getattr(self, '_lead_dbg', -1):.2f},{self.rate_h:.2f},{self.rate_c:.2f},"
                    f"{deficit_h:.2f},{deficit_c:.2f},"
                    f"{T.min() if V else 0:.2f},{T.max() if V else 0:.2f},{T.mean() if V else 0:.2f},"
                    f"{int(heat_zone.sum())},{int(cool_zone.sum())},{p_cmd.max():.0f},{int(on.sum())},"
                    f"{tw:.0f},{dp_bar:.1f},{int(pump_on)},{valve.max() if V else 0:.2f},"
                    f"{damper.max() if V else 0:.2f},{sat.min():.1f},{recirc.min():.2f}\n")
            except (OSError, ValueError):
                pass
        return {"continuous_action": cont.astype(np.float32), "discrete_action": disc.astype(np.int32)}
