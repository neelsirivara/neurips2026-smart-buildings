import sys, os
from pathlib import Path
KIT = Path(__file__).resolve().parents[2] / "kit"
sys.path.insert(0, str(KIT)); os.chdir(KIT)
import numpy as np, time
from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data, POLICY_MAP, validate_action
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker
scen = sys.argv[1] if len(sys.argv) > 1 else "building_train_1/atlanta_2"
d = KIT / "smart_buildings/training_scenarios" / scen
env = load_hybrid_environment(d / "config.gin"); env.metrics_path = None; env._occupancy_normalization_constant = 125.0
md = create_building_meta_data(env, d)
names = md["observation_field_names"]
for i, n in enumerate(names):
    if i >= 300: print(i, n)
ix = {n: i for i, n in enumerate(names)}
tracker = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False); tracker.reset(); obs = tracker.last_obs
pol = POLICY_MAP["pid_water"](md, env.action_spec())
t0 = time.time()
for s in range(int(sys.argv[2]) if len(sys.argv) > 2 else 60):
    a = validate_action(pol.get_action(obs), env.action_spec())
    obs, r, term, trunc, _ = tracker.step(a)
    hod = np.arctan2(obs[ix["hod_sin_000"]], obs[ix["hod_cos_000"]]) % (2*np.pi) / (2*np.pi) * 24
    dow = np.arctan2(obs[ix["dow_sin_000"]], obs[ix["dow_cos_000"]]) % (2*np.pi) / (2*np.pi) * 7
    if s % 6 == 0:
        print(f"step {s:4d} ts={tracker.timestamps[-1]} hod={hod:5.2f} dow={dow:4.2f} now={obs[ix['comfort_mode_now']]:.0f} soon={obs[ix['comfort_mode_soon']]:.0f} occ={obs[ix['num_occupants']]:.4f} oat={obs[ix['ahs_ahu_1_outside_air_temperature_sensor']]:.2f} r={r:.4f}")
print("sec/step", (time.time()-t0)/(s+1))
