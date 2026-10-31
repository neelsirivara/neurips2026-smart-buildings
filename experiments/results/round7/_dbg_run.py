import sys, os, json, importlib.util
from pathlib import Path
sys.path.insert(0, r"C:\Users\neels\Downloads\gen_papers_2\neurips_challenges\smart_buildings\kit")
os.chdir(r"C:\Users\neels\Downloads\gen_papers_2\neurips_challenges\smart_buildings\kit")
import numpy as np
from smart_buildings import evaluate as ev
from smart_buildings.smart_control.utils.scenario_generator import SimulationTracker
cand = sys.argv[1]; b = sys.argv[2]; w = sys.argv[3]; steps = int(sys.argv[4])
P = json.load(open(rf"C:\Users\neels\Downloads\gen_papers_2\neurips_challenges\smart_buildings\experiments\src\policy_candidates\{cand}.json"))
scen = Path("smart_buildings/heldout_scenarios_r6hs") / b / w
env = ev.load_hybrid_environment(scen / "config.gin"); env.metrics_path = None; env._occupancy_normalization_constant = 125.0
tr = SimulationTracker(env, vmin=280, vmax=310, capture_snapshots=False)
md = ev.create_building_meta_data(env, scen)
spec = importlib.util.spec_from_file_location("p", r"C:\Users\neels\Downloads\gen_papers_2\neurips_challenges\smart_buildings\experiments\results\round7\debug_v10.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pol = m.TransferPolicy(md, env.action_spec(), params=P)
tr.reset(); obs = tr.last_obs
rows = []
for t in range(steps):
    obs, r, *_ = tr.step(ev.validate_action(pol.get_action(obs), env.action_spec()))
    ts = env.building.current_timestamp
    if ts.hour == 1 and ts.minute == 0 and ts.dayofweek < 5:
        la = getattr(pol, "_dbg_lead_all", None)
        dl = getattr(pol, "_dbg_lead", None)
        th = pol.mbr_th
        rows.append({"day": str(ts.date()), "lead_mean": float(np.mean(la)) if la is not None else None,
                     "lead_model_mean": float(np.mean(dl[1][dl[2]])) if dl is not None and dl[2].any() else None,
                     "n_use": int(dl[2].sum()) if dl is not None else 0,
                     "trec_med": float(np.median(dl[3][np.isfinite(dl[3])])) if dl is not None and np.isfinite(dl[3]).any() else None,
                     "a_med": float(np.median(th[:, 0])), "k_med": float(np.median(th[:, 1])), "c_med": float(np.median(th[:, 2])),
                     "rate_ema_med": float(np.median(pol.rate_h_z)), "n_med": float(np.median(pol.mbr_n))})
for r in rows: print(r)
