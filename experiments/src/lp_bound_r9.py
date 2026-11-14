"""Round 9 (analysis only): perfect-foresight LP bound on the heat v10 could save by shaping each zone's trajectory.

The kit's building model is linear and time invariant: one backward-Euler step of the temperature field (plus the
interior-mass nodes) with a single sparse LU factorisation (finite_difference_solver.py).  Given the net heat each
zone's air receives, zone temperatures follow by superposition.  This script

1. runs the policy (v10) for --steps steps on one scenario and logs, per step and VAV, the net HVAC heat
   Q = reheat + rho cp F (T_sa - T) (read inside the simulator step, as run_diag_r9.py), the discharge/coil
   conditions, occupancy and zone temperatures;
2. checks the linear model: replays the logged Q + internal gains + occupants through the bare solver from the same
   initial state (no stochastic convection) and reports the zone-temperature error;
3. computes each zone's impulse response to 1 kW for one step (zero state, zero ambient), the zone's own temperature
   and every other zone's, for the whole window;
4. per zone, solves the LP  min sum_b price_b dQ_b  s.t.  T_v10(t) + sum_b M(t,b) dQ_b >= min(294, T_v10(t)) on every
   occupied step (and <= 297), Q_v10 + dQ within [Q_lo, Q_hi] per 15-min block, holding the other zones at their
   v10 trajectories.  Q_hi = the zone's box at floor-pressure flow and the discharge cap (v10's preconditioning cap;
   --qmax-full: full design flow), Q_lo = no reheat (forced air only while occupied, nothing otherwise).  Price
   = gas per J of net heat: g_cap = (T_cap - T_sa)/(T_cap - T) where the box would run at the cap, 1 where v10 already
   reheats forced air below the cap.  The other zones held fixed makes the sum over zones an optimistic (upper)
   estimate of the saving: in reality a colder neighbour also needs more heat.

Output: <results-dir>/<building>/<weather>/lp_bound.json.  Analysis only; nothing here is a controller.

    python lp_bound_r9.py --policy-file policies/v10.py --building building_train_8 --weather fairbanks_8 \
        --scenarios-dir <kit>/smart_buildings/training_scenarios --results-dir out/lp_bound --steps 2016
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

KIT = Path(os.environ["SB_KIT_DIR"])
sys.path.insert(0, str(KIT))
ORIG = Path(os.getcwd())
os.chdir(KIT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import linprog  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402

from smart_buildings.evaluate import create_building_meta_data, load_hybrid_environment, validate_action  # noqa: E402
from smart_buildings.smart_control.simulator import constants as C  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402

T_CAP = 308.15
RHO_CP = C.AIR_DENSITY * C.AIR_HEAT_CAPACITY
F_FLOOR = 2.0 * np.sqrt(200.0 / 2000.0)          # m3/s, damper 1 at floor pressure
F_MIN = 0.1 * F_FLOOR
BLK = 6                                            # steps per LP block (30 min); --blk overrides


class _LPRes:
    def __init__(self, status, x, fun, message):
        self.status, self.x, self.fun, self.message = status, x, fun, message


def solve_lp(c, A, b, bounds, nq):
    """linprog with the heat variables in kW (the first nq columns) and the objective scaled to O(1), retried with
    the interior-point and dual-simplex solvers on numerical trouble; returns x, fun in the original units."""
    c = np.asarray(c, dtype=float)
    colscale = np.ones(len(c))
    colscale[:nq] = 1000.0
    objscale = 1.0 / max(np.abs(c * colscale).max(), 1e-12)
    cs = c * colscale * objscale
    bs = [((lo / colscale[i]) if lo is not None else None, (hi / colscale[i]) if hi is not None else None)
          for i, (lo, hi) in enumerate(bounds)]
    As = None if A is None else A * colscale[None, :]
    last = None
    for method in ("highs", "highs-ipm", "highs-ds"):
        r = linprog(cs, A_ub=As, b_ub=b, bounds=bs, method=method)
        last = r
        if r.status == 0:
            return _LPRes(0, r.x * colscale, r.fun / objscale, r.message)
    return _LPRes(int(last.status), None, None, str(last.message))


def _abs(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (ORIG / q)


def run_policy(env, md, pol, steps):
    sim = env.building.simulator
    cap = {"on": False}
    o_fd = sim.finite_differences_timestep

    def fd(*a, **k):
        r = o_fd(*a, **k)
        c = np.asarray(k.get("air_side_conductance"), dtype=float)
        s = np.asarray(k.get("supply_temperature"), dtype=float)
        te = sim._air_side_sensed.T @ sim.building.temp.reshape(-1)
        cap["cond"], cap["tsa"], cap["tend"] = c.copy(), s.copy(), np.asarray(te, dtype=float).copy()
        return r
    sim.finite_differences_timestep = fd
    rh = {}
    for vid, vav in sim._hvac.vavs.items():
        def mk(vid, o):
            def f(sa, wt):
                r = o(sa, wt)
                if cap["on"]:
                    rh[vid] = float(r)
                return r
            return f
        vav.compute_reheat_energy_rate = mk(vid, vav.compute_reheat_energy_rate)
    o_ex = sim.execute_step_sim

    def ex(*a, **k):
        cap["on"] = True
        rh.clear()
        try:
            return o_ex(*a, **k)
        finally:
            cap["on"] = False
    sim.execute_step_sim = ex
    tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
    vav_ids = list(tr.vavs.keys())
    col = {v: i for i, v in enumerate(sim._coupled_vavs)}
    V = len(vav_ids)
    out = {k: np.zeros((steps, V)) for k in ("T", "Q", "RH", "F", "TSA", "OCC")}
    out["tout"] = np.zeros(steps)
    out["gas"] = np.zeros(steps)
    out["loss"] = np.zeros(steps)
    out["ts"] = []
    tr.reset()
    obs = tr.last_obs
    t0 = sim._current_timestamp
    for n in range(steps):
        ts = sim._current_timestamp
        out["ts"].append(ts)
        out["tout"][n] = sim._weather_controller.get_current_temp(ts)
        obs, _, term, trunc, _ = tr.step(validate_action(pol.get_action(obs), env.action_spec()))
        info, resp = env.get_reward_info_and_response()
        out["gas"][n] = sum(x.natural_gas_heating_energy_rate for x in info.boiler_reward_infos.values())
        out["loss"][n] = -tr.rewards[-1]
        zocc = {zid: z.average_occupancy for zid, z in info.zone_reward_infos.items()}
        c, s, te = cap["cond"], cap["tsa"], cap["tend"]
        for i, vid in enumerate(vav_ids):
            j = col[vid]
            r = rh.get(vid, 0.0)
            out["RH"][n, i] = r
            out["Q"][n, i] = r + c[j] * (s[j] - te[j])
            out["F"][n, i] = c[j] / RHO_CP
            out["TSA"][n, i] = s[j]
            out["OCC"][n, i] = zocc.get(vid.replace("VAV_", "room_"), 0.0)
        out["T"][n] = tr.zone_temps[-1]
        if term or trunc:
            break
    return vav_ids, out, t0


def _validate_and_impulses(a, bld, solver, idx, ncv, L, G, conv, n, V, zone_means):
    """Replay v10's logged heat through the bare solver (model check), then the 1 kW one-step impulse responses."""
    tv = time.time()
    bld.reset()
    solver.reset(bld.temp)
    temp = bld.temp.copy()
    Trep = np.zeros((n, V))
    for k in range(n):
        q = np.zeros_like(temp)
        for z in range(V):
            q[idx[z]] = (L["Q"][k, z] + G[k, z]) / ncv[z]
        temp = solver.solve(temp, q, L["tout"][k], conv)
        Trep[k] = zone_means(temp)
    err = Trep - L["T"]
    t_val = time.time() - tv

    # ---- 3. impulse responses (zero state, zero ambient), 1 kW for one step ----
    ti = time.time()
    W = min(a.win, n)
    R = np.zeros((V, W, V), dtype=np.float32)   # R[z_in, lag, z_out]
    zero = np.zeros_like(bld.temp)
    for z in range(V):
        solver.reset(zero)
        solver._mass_temp[:] = 0.0
        temp = zero.copy()
        q = np.zeros_like(temp)
        q[idx[z]] = 1000.0 / ncv[z]
        temp = solver.solve(temp, q, 0.0, conv)
        R[z, 0] = zone_means(temp)
        q0 = np.zeros_like(temp)
        for k in range(1, W):
            temp = solver.solve(temp, q0, 0.0, conv)
            R[z, k] = zone_means(temp)
    t_imp = time.time() - ti
    return err, R, W, t_val, t_imp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy-file", required=True)
    ap.add_argument("--building", required=True)
    ap.add_argument("--weather", required=True)
    ap.add_argument("--scenarios-dir", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--steps", type=int, default=2016)
    ap.add_argument("--win", type=int, default=2016, help="LP window (steps); consecutive windows over the run")
    ap.add_argument("--qmax-full", action="store_true")
    ap.add_argument("--blk", type=int, default=6, help="steps per LP block and between comfort checks")
    ap.add_argument("--both", action="store_true", help="run the hard-comfort and the --score LP on one impulse set")
    ap.add_argument("--reuse", action="store_true", help="load the v10 log and impulse responses from lp_cache.npz")
    ap.add_argument("--gs-damp", type=float, default=0.5, help="Gauss-Seidel step: move this fraction to each zone's new optimum")
    ap.add_argument("--gs", type=int, default=0,
                    help="score mode: Gauss-Seidel sweeps over zones, each zone solved against the others' current "
                         "changes through the cross responses; the final joint solution is then scored exactly "
                         "(an achievable point of the linear model, i.e. a lower estimate of the joint optimum)")
    ap.add_argument("--score", action="store_true",
                    help="objective in leaderboard-loss units: gas at the step's normalised cost+carbon price, "
                         "comfort as a priced slack below 294 K at the score's own weight (0.6 x 0.2 per K x the "
                         "zone's occupancy share), instead of hard comfort >= min(294, v10)")
    ap.add_argument("--policy", default="transfer")       # accepted for runner compatibility
    ap.add_argument("--params-json", default=None)
    a = ap.parse_args()
    global BLK
    BLK = max(1, a.blk)
    out_dir = _abs(a.results_dir) / a.building / a.weather
    out_dir.mkdir(parents=True, exist_ok=True)
    tags = [("lp_bound_full" if a.qmax_full else "lp_bound") + ("_score" if sc else "")
            + (f"_gs{g}" if (sc and g > 0) else "") + ".json"
            for sc, g in ([(False, 0), (True, 0), (True, max(a.gs, 16))] if a.both else [(a.score, a.gs)])]
    if all((out_dir / t).exists() for t in tags):
        print("skip (done)")
        return 0
    scen = _abs(a.scenarios_dir) / a.building / a.weather
    env = load_hybrid_environment(scen / "config.gin")
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    md = create_building_meta_data(env, scen)
    spec = importlib.util.spec_from_file_location("pol_lp", _abs(a.policy_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pol = mod.TransferPolicy(md, env.action_spec())
    tw = time.time()
    cache = out_dir / "lp_cache.npz"
    reuse = a.reuse and cache.exists()
    if reuse:
        cz = np.load(cache, allow_pickle=False)
        vav_ids = [str(v) for v in cz["vav_ids"]]
        L = {k: cz[k] for k in ("T", "Q", "RH", "F", "TSA", "OCC", "tout", "gas", "loss")}
        L["ts"] = [pd.Timestamp(str(t)) for t in cz["ts"]]
        t0 = L["ts"][0]
    else:
        vav_ids, L, t0 = run_policy(env, md, pol, a.steps)
    n = len(L["ts"])
    V = len(vav_ids)
    t_run = time.time() - tw
    sim = env.building.simulator
    bld = sim.building
    solver = sim._solver
    rooms = [v.replace("VAV_", "room_") for v in vav_ids]
    idx = [bld._zone_indices(r) for r in rooms]
    ncv = np.array([len(i[0]) for i in idx], dtype=float)
    area = ncv * (bld.cv_size_cm / 100.0) ** 2
    ts = pd.DatetimeIndex(L["ts"])
    comfort = np.array([sim._hvac.is_comfort_mode(t) for t in L["ts"]], dtype=bool)
    G = (sim._internal_gain_w_per_m2 * np.where(comfort, 1.0, sim._internal_gain_standby_fraction))[:, None] \
        * area[None, :] + sim._occupant_sensible_heat_w * L["OCC"]
    conv = sim._weather_controller.get_air_convection_coefficient(t0)
    rf = env.reward_function
    dt5 = pd.Timedelta(seconds=300)
    lw = np.zeros(n)                                   # leaderboard loss per W of gas for one step
    for k, t in enumerate(L["ts"]):
        dcost = rf._electricity_energy_cost.cost(t, t + dt5, rf._max_electricity_rate) +             rf._natural_gas_energy_cost.cost(t, t + dt5, rf._max_natural_gas_rate)
        dcarb = rf._electricity_energy_cost.carbon(t, t + dt5, rf._max_electricity_rate) +             rf._natural_gas_energy_cost.carbon(t, t + dt5, rf._max_natural_gas_rate)
        wsum = rf.energy_cost_weight + rf.carbon_emission_weight + rf.productivity_weight
        lw[k] = (rf.energy_cost_weight * rf._natural_gas_energy_cost.cost(t, t + dt5, 1.0) / dcost
                 + rf.carbon_emission_weight * rf._natural_gas_energy_cost.carbon(t, t + dt5, 1.0) / dcarb) / wsum
    comfort_w = rf.productivity_weight / (rf.energy_cost_weight + rf.carbon_emission_weight + rf.productivity_weight)
    # comfort weight of a zone: its expected occupancy share, 1/V while anyone is in (arrivals are independent of the
    # zone, so E[n_z / N] = 1/V); the realised share is not observable to any policy and is not used
    hod0 = ts.hour.values + ts.minute.values / 60.0
    early0 = ((ts.dayofweek.values < 5) & (hod0 >= 6.0) & (hod0 < 6.25))[:, None]
    occ_share = np.where((L["OCC"].sum(axis=1, keepdims=True) > 0) | early0, 1.0 / max(len(vav_ids), 1), 0.0)         * np.ones((1, len(vav_ids)))

    def zone_means(temp):
        return np.array([temp[i].mean() for i in idx])

    # ---- 2. validation replay ----
    tv = time.time()
    if reuse:
        err = cz["err"]
        R = cz["R"]
        W = R.shape[1]
        t_val = t_imp = 0.0
    else:
        err, R, W, t_val, t_imp = _validate_and_impulses(a, bld, solver, idx, ncv, L, G, conv, n, V, zone_means)
        np.savez_compressed(cache, vav_ids=np.array(vav_ids), ts=np.array([str(t) for t in L["ts"]]),
                            err=err.astype(np.float32), R=R,
                            **{k: np.asarray(L[k]) for k in ("T", "Q", "RH", "F", "TSA", "OCC", "tout", "gas", "loss")})

    gs_req = a.gs
    modes = [(False, 0), (True, 0), (True, max(gs_req, 16))] if a.both else [(a.score, a.gs)]
    for mode_score, mode_gs in modes:
        a.score, a.gs = mode_score, mode_gs
        tag = (("lp_bound_full" if a.qmax_full else "lp_bound") + ("_score" if a.score else "")
               + (f"_gs{a.gs}" if (a.score and a.gs > 0) else "") + ".json")
        # ---- 4. per-zone LP, per window ----
        tl = time.time()
        # comfort is checked whenever anyone is in, and also 06:00-06:15 on every weekday: a policy cannot know a
        # holiday before the first quarter hour passes without arrivals (no date is observed), so the recovery into
        # a holiday morning is not counted as avoidable; after 06:15 the LP may stop heating on a holiday
        hodf = ts.hour.values + ts.minute.values / 60.0
        early = (ts.dayofweek.values < 5) & (hodf >= 6.0) & (hodf < 6.25)
        occ_bld = (L["OCC"].sum(axis=1) > 0) | early
        res_z = []
        f_hi = 2.0 if a.qmax_full else F_FLOOR
        tot = {"save_heat": 0.0, "save_gas": 0.0, "gas_in_windows": 0.0}
        nbw = W // BLK
        prof_qv = np.full((V, (n // W) * nbw), np.nan, dtype=np.float32)
        prof_dq = np.full((V, (n // W) * nbw), np.nan, dtype=np.float32)
        for w0 in range(0, n - W + 1, W):
            sl = slice(w0, w0 + nbw * BLK)
            tot["gas_in_windows"] += float(L["gas"][sl].sum() * 300.0)
            occ_w = occ_bld[sl]
            cons_t = np.where(occ_w)[0][::BLK]            # comfort checked every BLK steps
            n_w = nbw * BLK
            gs_on = a.score and a.gs > 0
            eff = np.zeros((n_w, V))                       # sum over zones of conv(R[z',:,z], dq_z') (gs mode)
            dq_cur = np.zeros((V, nbw))
            self_eff = np.zeros((n_w, V))
            gs_rec = {}
            best_gs = {}
            from scipy.signal import fftconvolve
            sweeps = a.gs if gs_on else 1
            for sweep in range(sweeps):
              for z in range(V):
                  h = R[z, :, z].astype(float) / 1000.0     # K per W for one step
                  hb = np.convolve(h, np.ones(BLK))[:nbw * BLK]
                  if len(cons_t):
                      bmax = cons_t // BLK
                      Mx = np.zeros((len(cons_t), nbw))
                      for r_i, t in enumerate(cons_t):
                          bs = np.arange(0, bmax[r_i] + 1)
                          Mx[r_i, bs] = hb[t - bs * BLK]
                  Tw = L["T"][sl, z] + ((eff[:, z] - self_eff[:, z]) if gs_on else 0.0)
                  Tv = Tw[cons_t]
                  lo_req = np.minimum(294.0, Tv)
                  hi_req = np.maximum(297.0, Tv)
                  rs = lambda x: x[sl].reshape(nbw, BLK)
                  Qv = rs(L["Q"][:, z]).mean(axis=1)
                  RHv = rs(L["RH"][:, z]).mean(axis=1)
                  Tb = rs(L["T"][:, z]).mean(axis=1)
                  Fb = rs(L["F"][:, z]).mean(axis=1)
                  tsa_obs = rs(L["TSA"][:, z])
                  tout_b = L["tout"][sl].reshape(nbw, BLK).mean(axis=1)
                  with np.errstate(invalid="ignore"):
                      tsa = np.where(Fb > 1e-3, np.nanmean(np.where(tsa_obs > 0, tsa_obs, np.nan), axis=1), np.nan)
                  tsa = np.where(np.isfinite(tsa), tsa, 0.7 * Tb + 0.3 * tout_b)
                  occ_b = occ_w.reshape(nbw, BLK).any(axis=1)
                  q_hi = np.maximum(f_hi * RHO_CP * np.maximum(T_CAP - Tb, 0.5), Qv)
                  q_lo = np.where(occ_b & (Fb > 1e-3), -F_MIN * RHO_CP * np.maximum(Tb - tsa, 0.0), np.minimum(Qv, 0.0))
                  q_lo = np.minimum(q_lo, Qv)
                  g_cap = np.maximum((T_CAP - tsa) / np.maximum(T_CAP - Tb, 0.5), 1.0)
                  below_cap = occ_b & (RHv > 1.0) & (Qv < F_MIN * RHO_CP * np.maximum(T_CAP - Tb, 0.5))
                  p_add = np.where(below_cap, 1.0, g_cap)
                  # removing heat saves what v10 paid for it (coil duty per J of net heat), never more than adding costs
                  with np.errstate(divide="ignore", invalid="ignore"):
                      c_v10 = np.where(Qv > 1.0, RHv / Qv, p_add)
                  p_rem = np.minimum(np.clip(c_v10, 0.0, None), p_add)
                  # variables: x = [dQ+ (nbw), dQ- (nbw)], dQ = dQ+ - dQ-
                  c = np.concatenate([p_add, -p_rem]) * BLK * 300.0
                  bounds = [(0.0, float(u)) for u in (q_hi - Qv)] + [(0.0, float(u)) for u in (Qv - q_lo)]
                  nc = len(cons_t)
                  if a.score and nc:
                      # loss units: gas J -> loss via the step's price (per W per step = lw), comfort slack s >= 0 with
                      # T + s >= 294 priced at comfort_w * (1/5 K) * occupancy share per check step (BLK steps)
                      lwb = lw[sl].reshape(nbw, BLK).mean(axis=1)
                      c = np.concatenate([p_add * lwb, -p_rem * lwb]) * BLK
                      cs = comfort_w * 0.2 * occ_share[sl][cons_t, z] * BLK
                      c = np.concatenate([c, cs])
                      bounds = bounds + [(0.0, None)] * nc
                      I = np.eye(nc)
                      A = np.vstack([np.hstack([-Mx, Mx, -I]), np.hstack([Mx, -Mx, np.zeros((nc, nc))])])
                      b = np.concatenate([Tv - 294.0, hi_req - Tv])
                      r = solve_lp(c, A, b, bounds, 2 * nbw)
                      base_comfort = float((cs * np.maximum(294.0 - Tv, 0.0)).sum())
                  elif nc:
                      A = np.vstack([np.hstack([-Mx, Mx]), np.hstack([Mx, -Mx])])
                      b = np.concatenate([Tv - lo_req, hi_req - Tv])
                      r = solve_lp(c, A, b, bounds, 2 * nbw)
                      base_comfort = 0.0
                  else:
                      r = solve_lp(c, None, None, bounds, 2 * nbw)
                      base_comfort = 0.0
                  if r.status != 0:
                      res_z.append({"zone": vav_ids[z], "w0": w0, "status": int(r.status), "msg": str(r.message)})
                      continue
                  dqp, dqm = r.x[:nbw], r.x[nbw:2 * nbw]
                  dq = dqp - dqm
                  if gs_on:
                      dq_upd = dq_cur[z] + float(a.gs_damp) * (dq - dq_cur[z])
                      delta = np.repeat(dq_upd - dq_cur[z], BLK)
                      if np.abs(delta).max() > 0.0:
                          for z2 in range(V):
                              eff[:, z2] += fftconvolve(R[z, :n_w, z2].astype(float) / 1000.0, delta)[:n_w]
                      dq_cur[z] = dq_upd
                      self_eff[:, z] = fftconvolve(R[z, :n_w, z].astype(float) / 1000.0, np.repeat(dq_upd, BLK))[:n_w]
                      gs_rec[z] = {"ca": p_add * lwb * BLK, "cr": p_rem * lwb * BLK, "cs": cs,
                                   "base_T": L["T"][sl, z][cons_t]}
                      dq = dq_upd
                      if sweep < sweeps - 1:
                          continue
                  wi = w0 // W
                  prof_qv[z, wi * nbw:(wi + 1) * nbw] = Qv
                  prof_dq[z, wi * nbw:(wi + 1) * nbw] = dq
                  sh = float(-(dq * BLK * 300.0).sum())
                  if a.score:
                      # loss saved (sum over steps) = baseline comfort cost - LP objective (gas change + new comfort)
                      sg = float(base_comfort - r.fun)
                  else:
                      sg = float(-r.fun)
                  if not gs_on:
                      tot["save_heat"] += sh
                      tot["save_gas"] += sg
                  res_z.append({"zone": vav_ids[z], "w0": w0, "status": 0, "save_heat_kwh": sh / 3.6e6,
                                "save_gas_kwh": (sg / 3.6e6) if not a.score else None,
                                "save_loss_sum": sg if a.score else None, "base_comfort_loss_sum": base_comfort,
                                "dq_unocc_kwh": float((dq * ~occ_b).sum() * BLK * 300.0 / 3.6e6),
                                "dq_occ_kwh": float((dq * occ_b).sum() * BLK * 300.0 / 3.6e6)})
              if gs_on and gs_rec:
                  # exact joint score of the current Gauss-Seidel solution (cross effects included), every sweep
                  gas_term = comf_new = comf_base = heat = 0.0
                  for z, v in gs_rec.items():
                      d = dq_cur[z]
                      gas_term += float((v["ca"] * np.maximum(d, 0.0) - v["cr"] * np.maximum(-d, 0.0)).sum())
                      t_fin = v["base_T"] + eff[cons_t, z]
                      comf_new += float((v["cs"] * np.maximum(294.0 - t_fin, 0.0)).sum())
                      comf_base += float((v["cs"] * np.maximum(294.0 - v["base_T"], 0.0)).sum())
                      heat += float(-(d * BLK * 300.0).sum())
                  sv = comf_base - (gas_term + comf_new)
                  tot.setdefault("gs", []).append({"w0": w0, "sweep": sweep, "gas_term": gas_term,
                                                   "comfort_base": comf_base, "comfort_final": comf_new, "save": sv})
                  if sv > best_gs.get("save", -np.inf):
                      best_gs.update({"save": sv, "heat": heat, "sweep": sweep})
            if gs_on and best_gs:
                tot["save_gas"] += best_gs["save"]
                tot["save_heat"] += best_gs["heat"]
                tot["gs_best_sweep"] = best_gs["sweep"]
        t_lp = time.time() - tl
        gas_kwh = float(L["gas"][:n].sum() * 300.0 / 3.6e6)
        summ = {"building": a.building, "weather": a.weather, "steps": n, "qmax": "full" if a.qmax_full else "floor",
                "v10_total_loss_per_step": float(L["loss"][:n].mean()), "v10_gas_kwh": gas_kwh,
                "v10_coil_kwh": float(L["RH"][:n].sum() * 300.0 / 3.6e6),
                "validation_rmse_k": float(np.sqrt(np.mean(err ** 2))), "validation_max_abs_k": float(np.abs(err).max()),
                "validation_rmse_by_zone_k": np.sqrt((err ** 2).mean(axis=0)).round(3).tolist(),
                "lp_window_steps": W, "lp_gas_in_windows_kwh": tot["gas_in_windows"] / 3.6e6,
                "lp_save_heat_kwh": tot["save_heat"] / 3.6e6, "lp_save_gas_kwh": tot["save_gas"] / 3.6e6,
                "lp_save_gas_share": (tot["save_gas"] / max(tot["gas_in_windows"], 1e-9)) if not a.score else None,
                "lp_save_loss_per_step": (tot["save_gas"] / n) if a.score else None,
                "lp_save_loss_share": (tot["save_gas"] / n / max(float(L["loss"][:n].mean()), 1e-12)) if a.score else None,
                "gs": tot.get("gs"), "zones": res_z, "seconds": {"run": t_run, "validate": t_val, "impulse": t_imp, "lp": t_lp}}
        (out_dir / tag).write_text(json.dumps(summ, indent=1))
        np.savez_compressed(out_dir / tag.replace(".json", "_profiles.npz"), qv=prof_qv, dq=prof_dq,
                            vav_ids=np.array(vav_ids), blk=BLK, t_zone=L["T"][:n].astype(np.float32),
                            tout=L["tout"][:n].astype(np.float32), occ_bld=occ_bld[:n],
                            ts=np.array([str(t) for t in L["ts"][:n]]))
        print(json.dumps({k: v for k, v in summ.items() if k not in ("zones", "validation_rmse_by_zone_k")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
