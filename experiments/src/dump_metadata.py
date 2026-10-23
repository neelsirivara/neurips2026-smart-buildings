"""Dump building metadata + observation field names + one raw observation for inspection."""
import sys, json
from pathlib import Path
KIT = Path(__file__).resolve().parents[2] / "kit"
sys.path.insert(0, str(KIT))
import os
os.chdir(KIT)
import numpy as np
from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker

scen = sys.argv[1] if len(sys.argv) > 1 else "building_train_1/atlanta_2"
d = KIT / "smart_buildings/training_scenarios" / scen
env = load_hybrid_environment(d / "config.gin")
env.metrics_path = None
env._occupancy_normalization_constant = 125.0
md = create_building_meta_data(env, d)
tracker = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
tracker.reset()
obs = tracker.last_obs
names = md["observation_field_names"]
print("n_obs", len(names), "n_cont", md["n_continuous_action"], "n_disc", md["n_discrete_action"])
for k in ["temp_indices","pressure_indices","recirculation_indices","water_indices","morning_start_hour","evening_start_hour","comfort_temp_window","eco_temp_window","time_zone","holidays","num_floors"]:
    print(k, "=", md[k])
print("zone_action_indices sample:", list(md["zone_action_indices"].items())[:3])
print("ahu_zone_assignments:", {k: len(v) for k, v in md["ahu_zone_assignments"].items()})
print("action_norm:", json.dumps(md["action_normalization_metadata"], indent=0)[:1500])
print("obs_norm keys:", list(md["observation_normalization_metadata"].keys()))
for i, n in enumerate(names):
    if not n.startswith("VAV_") or n.startswith("VAV_1_"):
        print(f"{i:4d} {n:60s} {obs[i]: .4f}")
print("device_action_tuples:", env._device_action_tuples[:8], "...", env._device_action_tuples[-4:])
print("action_names:", env.action_names[:6], "...", env.action_names[-4:])
