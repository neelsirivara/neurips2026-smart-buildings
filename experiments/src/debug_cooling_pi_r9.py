"""Debug: why does VAV_35 on building_train_7/phoenix_3 sit above 297 K with its damper part-open (v10)?"""
import importlib.util
import os
import sys
from pathlib import Path

KIT = Path(r"C:/Users/neels/Downloads/gen_papers_2/neurips_challenges/smart_buildings/kit")
sys.path.insert(0, str(KIT))
os.chdir(KIT)
import numpy as np  # noqa: E402
from smart_buildings.evaluate import create_building_meta_data, load_hybrid_environment, validate_action  # noqa: E402
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker  # noqa: E402

scen = KIT / "smart_buildings/training_scenarios/building_train_7/phoenix_3"
env = load_hybrid_environment(scen / "config.gin")
env.metrics_path = None
env._occupancy_normalization_constant = 125.0
tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
md = create_building_meta_data(env, scen)
spec = importlib.util.spec_from_file_location("v10", r"C:/Users/neels/Downloads/gen_papers_2/neurips_challenges/smart_buildings/submission/transfer_policy.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pol = mod.TransferPolicy(md, env.action_spec())
vids = list(tr.vavs.keys())
j = vids.index("VAV_35")
tr.reset()
obs = tr.last_obs
for n in range(330):
    act = pol.get_action(obs)
    if n >= 300:
        zt = obs[pol.z_t[j]] * pol.zt_std + pol.zt_mean
        lo_s = obs[pol.z_lo[j]] if pol.z_lo[j] >= 0 else None
        hi_s = obs[pol.z_hi[j]] if pol.z_hi[j] >= 0 else None
        print(n, "T %.3f lo_s %s hi_s %s mode %d I_c %.0f I_h %.0f damper %.3f valve %.3f" % (
            zt, None if lo_s is None else round(float(lo_s), 2), None if hi_s is None else round(float(hi_s), 2),
            int(pol.zone_mode[j]), pol.I_c[j], pol.I_h[j],
            (act["continuous_action"][pol.z_d[j]] + 1) / 2, (act["continuous_action"][pol.z_v[j]] + 1) / 2))
    obs, *_ = tr.step(validate_action(act, env.action_spec()))
