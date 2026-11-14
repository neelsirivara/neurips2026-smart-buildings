"""Round 9 debug: v10 preconditions every Saturday morning. Print the policy's decoded day/hour and workday logic."""
import importlib.util
import math
import os
import sys
from pathlib import Path

KIT = Path(os.environ.get("SB_KIT_DIR", r"C:/Users/neels/Downloads/gen_papers_2/neurips_challenges/smart_buildings/kit"))
sys.path.insert(0, str(KIT))
os.chdir(KIT)
import numpy as np  # noqa: E402
from smart_buildings.evaluate import create_building_meta_data, load_hybrid_environment, validate_action  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402

b, w, steps = (sys.argv[1:4] + ["building_train_8", "fairbanks_8", "700"][len(sys.argv[1:4]):])
scen = KIT / "smart_buildings/training_scenarios" / b / w
env = load_hybrid_environment(scen / "config.gin")
env.metrics_path = None
env._occupancy_normalization_constant = 125.0
tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
md = create_building_meta_data(env, scen)
spec = importlib.util.spec_from_file_location("v10", str(Path(__file__).resolve().parents[2] / "submission" / "transfer_policy.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pol = mod.TransferPolicy(md, env.action_spec())
names = md["observation_field_names"]
print("time fields:", [n for n in names if "day" in n or "hour" in n or "time" in n][:10])
tr.reset()
obs = tr.last_obs
sim = env.building.simulator
for n in range(int(steps)):
    ts = sim._current_timestamp
    hod = pol._cyclic(np.asarray(obs, dtype=float), pol.hod_sin, pol.hod_cos, 24.0)
    dow = pol._cyclic(np.asarray(obs, dtype=float), pol.dow_sin, pol.dow_cos, 7.0)
    act = pol.get_action(obs)
    if ts.minute == 0 and ((ts.dayofweek == 4 and ts.hour >= 17) or (ts.dayofweek == 5 and ts.hour <= 7)):
        o = np.asarray(obs, dtype=float)
        now = float(o[pol.now_idx]) if pol.now_idx >= 0 else None
        soon = float(o[pol.soon_idx]) if pol.soon_idx >= 0 else None
        occ = float(o[pol.occ_idx]) if pol.occ_idx >= 0 else None
        print(ts, ts.day_name()[:3], "dow %.2f hod %.2f" % (dow, hod), "mode", pol.mode, "now", now, "soon", soon,
              "occ %.4f occ_min %.4f" % (occ, pol.occ_min), "lead_max %.2f" % pol._lead_dbg,
              "n_pre", int((pol.zone_mode == 1).sum()))
    obs, *_ = tr.step(validate_action(act, env.action_spec()))
