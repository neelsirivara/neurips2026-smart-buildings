"""Emit paper/results_macros.tex from the result JSON files.

Every number that appears in the paper comes from here. Missing inputs emit
\\textbf{??} so the PDF never lies silently.

Inputs (all optional; missing -> ??):
  results/final_scores.json          score_all.py on the 30 training scenarios
  results/heldout_scores.json        score_all.py on generated held-out buildings (if any)
  results/tune/tune_log.json         tuning log (number of configs, screening score)
  results/tune/best_params.json      tuned parameters
  results/env_info.json              speed, versions
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
OUT = ROOT / "paper" / "results_macros.tex"

MISSING = r"\textbf{??}"


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def fmt(x, nd=4, pct=False, signed=False, int_=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return MISSING
    if int_:
        return f"{int(round(x))}"
    if pct:
        s = f"{100 * x:+.1f}" if signed else f"{100 * x:.1f}"
        return s + r"\%"
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def pfmt(pv):
    """p-value for use inside $p=...$ (no $ of its own)."""
    if pv is None:
        return MISSING
    if pv < 1e-4:
        return "<10^{-4}"
    if pv < 0.01:
        return "<0.01"
    return f"={pv:.2f}"


def macro(name: str, value: str) -> str:
    # LaTeX macro names cannot contain digits; callers avoid them.
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def get(d, *keys, default=None):
    for k in keys:
        if d is None:
            return default
        d = d.get(k) if isinstance(d, dict) else None
    return default if d is None else d


STATION_NAMES = {"fairbanks": "Fairbanks", "denver": "Denver", "atlanta": "Atlanta",
                 "phoenix": "Phoenix", "singapore": "Singapore"}
POLICY_MACRO = {"transfer": "Ours", "transfer_v4": "OursVFour", "pid_water": "PidWater", "pid": "Pid",
                "fixed_setpoint": "FixedSp", "bang_bang": "BangBang", "pid_water_official": "PidWaterOff",
                "pid_official": "PidOff", "fixed_setpoint_official": "FixedSpOff", "bang_bang_official": "BangBangOff"}
BUILDING_MACRO = {"building_train_1": "Bone", "building_train_2": "Btwo", "building_train_4": "Bfour",
                  "building_train_5": "Bfive", "building_train_7": "Bseven", "building_train_8": "Beight",
                  "building_0501": "Bgena", "building_0502": "Bgenb"}


def _parse_list_col(series):
    """ahu_log.csv stores per-AHU lists as strings like "[0, 1, 0]" or "[np.float64(1.0), ...]"."""
    import re
    import numpy as np
    num = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")
    return np.array([[float(x) for x in num.findall(str(v))] for v in series], dtype=float)


def ahu_on_frac_unoccupied(run_dir: Path):
    """Fraction of unoccupied steps on which at least one AHU was commanded on."""
    try:
        import numpy as np
        import pandas as pd
        ts = pd.read_csv(run_dir / "timeseries.csv", usecols=["occupancy"])
        ahu = pd.read_csv(run_dir / "ahu_log.csv", usecols=["ahu_run_cmds"])
        R = _parse_list_col(ahu["ahu_run_cmds"])
        n = min(len(ts), len(R))
        occ = ts["occupancy"].values[:n] > 0
        on = R[:n].max(axis=1) > 0
        return float(on[~occ].mean()) if (~occ).any() else None
    except Exception:  # noqa: BLE001
        return None


def peak_oat_c(results_dir: Path, station: str):
    """Maximum outside-air temperature (deg C) over the saved AHU logs of our runs for one station."""
    try:
        import pandas as pd
        best = None
        for f in results_dir.glob(f"building_*/{station}_*/transfer/ahu_log.csv"):
            m = float(pd.read_csv(f, usecols=["outside_air"])["outside_air"].max())
            best = m if best is None else max(best, m)
        return None if best is None else best - 273.15
    except Exception:  # noqa: BLE001
        return None


def tank_loss_extra_kw():
    """Boiler tank dissipation at 350 K minus at 310 K, tank standing in 294 K air (kit's Boiler)."""
    try:
        import sys
        sys.path.insert(0, str(ROOT / "kit"))
        from smart_buildings.smart_control.simulator import boiler as _b
        b = _b.Boiler(supply_water_temperature_setpoint=350.0, device_id="audit_boiler")
        return (b.compute_thermal_dissipation_rate(350.0, 294.0) - b.compute_thermal_dissipation_rate(310.0, 294.0)) / 1000.0
    except Exception:  # noqa: BLE001
        return None


def random_search_evals(tl, ab) -> dict:
    """Entries of tune_log.json that belong to the v4 random search: no candidate tag and not an
    ablation-only configuration (ablation rows are matched by their parameter hash)."""
    import hashlib
    if not tl:
        return {}

    def phash(params):
        return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:10]

    abl = set()
    if ab:
        base, best = ab["default"]["params"], ab["best"]["params"]
        for row in ab["rows"]:
            src = best if row["macro"].startswith("Rev") else base
            pp = dict(src)
            pp[row["param"]] = row["value"]
            abl.add(phash(pp))
    ev = tl.get("evals", {})
    if any(v.get("stage") == "random" for v in ev.values()):
        return {h: v for h, v in ev.items() if v.get("stage") == "random"}
    return {h: v for h, v in ev.items() if "_policy" not in v.get("params", {}) and h not in abl}


def _tex(s: str) -> str:
    return s.replace("_", r"\_")


def write_tuning_tables(ab, cs) -> None:
    """paper/tuning_tables.tex: the v4 ablation on the screening set and the v5 candidates at full length."""
    out = ROOT / "paper" / "tuning_tables.tex"
    L = ["% AUTO-GENERATED by experiments/src/make_macros.py -- do not edit by hand\n"]
    if ab:
        L.append("\\begin{table}[h]\n\\caption{Ablation of the four tuned v4 values on the screening set (six scenarios, "
                 "1,440 steps; leaderboard metric, lower is better). Rev: the best configuration with one value reverted "
                 "to its default; Add: the defaults with one tuned value added. Best " + f"{ab['best']['score']:.5f}" +
                 ", defaults " + f"{ab['default']['score']:.5f}" + ".}\n\\label{tab:ablation}\n\\centering\\small\n"
                 "\\begin{tabular}{llrrr}\n\\toprule\nparameter & change & score & vs best & vs defaults \\\\\n\\midrule\n")
        for r in ab["rows"]:
            kind = "Rev" if r["macro"].startswith("Rev") else "Add"
            L.append(f"\\texttt{{{_tex(r['param'])}}} & {kind} ({r['value']:g}) & {r['score']:.5f} & "
                     f"{100 * r['rel_vs_best']:+.1f}\\% & {100 * r['rel_vs_default']:+.1f}\\% \\\\\n")
        L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")
    cands = (get(cs, "full", "candidates") or [])
    if cands:
        v4 = get(cs, "full", "v4_mac") or {}
        short = {"sat_cool_hi": "SAT", "night_low_ext": "nlo", "night_high_ext": "nhi", "margin_occ": "occ",
                 "lead_max_h": "lead"}
        L.append("\\begin{table}[h]\n\\caption{v5 candidates at full length (8,640 steps) on the 30 public scenarios, "
                 "run on the same machine as v4 (metric " + fmt(v4.get("metric"), 5) + "). Overrides are applied to the v4 "
                 "values (SAT = \\texttt{sat\\_cool\\_hi} in K; nlo/nhi = \\texttt{night\\_low/high\\_ext} in K; occ = "
                 "\\texttt{margin\\_occ}; lead = \\texttt{lead\\_max\\_h}); CI = paired bootstrap 95\\% CI of the "
                 "per-scenario difference vs v4 (negative favours the candidate); the last five columns are station "
                 "means.}\n\\label{tab:candidates}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{3pt}\n"
                 "\\begin{tabular}{lrrcrrrrrr}\n\\toprule\noverrides & metric & ratio & CI & wins & Fai. & Den. & "
                 "Atl. & Pho. & Sin. \\\\\n\\midrule\n")
        for c in cands:
            ov = ", ".join(f"{short.get(k, _tex(k))} {v:g}" for k, v in c["params"].items()) or "none (v5 code, v4 values)"
            bs = c.get("by_station", {})
            L.append(f"{ov} & {c['metric']:.5f} & {c['ratio_vs_v4']:.3f} & [{c['ci_lo']:+.5f}, {c['ci_hi']:+.5f}] & "
                     f"{c['wins']}/{c['n']} & {bs.get('fairbanks', float('nan')):.4f} & {bs.get('denver', float('nan')):.4f} & "
                     f"{bs.get('atlanta', float('nan')):.4f} & {bs.get('phoenix', float('nan')):.4f} & "
                     f"{bs.get('singapore', float('nan')):.4f} \\\\\n")
        L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")
    out.write_text("".join(L))


def write_per_scenario_table(fs, hs) -> None:
    """paper/per_scenario_table.tex: every scenario's return and score for ours, local pid_water
    and the organizer-provided pid_water (public set), then the held-out generated buildings."""
    out = ROOT / "paper" / "per_scenario_table.tex"
    L = ["% AUTO-GENERATED by experiments/src/make_macros.py -- do not edit by hand\n"]

    def block(scores, title, label, with_official):
        ours = get(scores, "policies", "transfer", "per_scenario") or {}
        v4 = get(scores, "policies", "transfer_v4", "per_scenario") or {}
        loc = get(scores, "policies", "pid_water", "per_scenario") or {}
        off = get(scores, "policies", "pid_water_official", "per_scenario") or {}
        if not ours:
            L.append(f"% {label}: no data yet\n")
            return
        cols = "llrrrrr" + ("r" if with_official else "")
        L.append("\\begin{table}[t]\n\\caption{" + title + "}\n\\label{" + label + "}\n\\centering\\scriptsize\n"
                 "\\setlength{\\tabcolsep}{2.5pt}\n\\begin{tabular}{" + cols + "}\n\\toprule\n")
        hdr = "scenario & zones/AHUs & v5 return & v5 score & v4 score & pid\\_water return & pid\\_water score"
        if with_official:
            hdr += " & pid\\_water official score"
        L.append(hdr + " \\\\\n\\midrule\n")
        keys = sorted(ours, key=lambda k: (k.split("/")[1].rsplit("_", 1)[0], k))
        for k in keys:
            o = ours[k]
            b = loc.get(k, {})
            f = off.get(k, {})
            size = f"{o.get('num_zones', '?')}/{o.get('num_ahus', '?')}"
            better = o["score"] < b.get("score", float("inf"))
            sc = f"\\textbf{{{o['score']:.4f}}}" if better else f"{o['score']:.4f}"
            v = v4.get(k, {})
            row = (f"{_tex(k)} & {size} & {o['total']:.1f} & {sc} & "
                   + (f"{v['score']:.4f}" if v else "--") + " & "
                   + (f"{b['total']:.1f} & {b['score']:.4f}" if b else "-- & --"))
            if with_official:
                row += " & " + (f"{f['score']:.4f}" if f else "--")
            L.append(row + " \\\\\n")
        L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")

    block(fs, "Per-scenario results on the 30 public scenarios (8,640 steps). Score is $|$total$/8640|$, lower is "
              "better; bold marks scenarios where SADR beats the locally re-run \\texttt{pid\\_water}.",
          "tab:per_scenario", True)
    block(hs, "Per-scenario results on the generated held-out buildings (8,640 steps), SADR vs locally run "
              "\\texttt{pid\\_water}.", "tab:per_scenario_held", False)
    out.write_text("".join(L))


def main() -> int:
    lines = ["% AUTO-GENERATED by experiments/src/make_macros.py -- do not edit by hand\n"]
    fs = load(RES / "final_scores.json")
    hs = load(RES / "heldout_scores.json")
    fl = load(RES / "final_scores_local.json")      # laptop run of v4 + pid_water (cross-machine check)
    cs = load(RES / "candidates_summary.json")
    tl = load(RES / "tune" / "tune_log.json")
    bp = load(RES / "tune" / "best_params.json")
    ei = load(RES / "env_info.json")

    # ---- main table: metric per policy, by station, decomposition ----
    lines.append(macro("NScen", fmt(get(fs, "n_scenarios"), int_=True)))
    for pol, mname in POLICY_MACRO.items():
        d = get(fs, "policies", pol)
        lines.append(macro(f"Metric{mname}", fmt(get(d, "metric"), 4)))
        lines.append(macro(f"MetricSd{mname}", fmt(get(d, "metric_sd"), 4)))
        for st, sn in STATION_NAMES.items():
            lines.append(macro(f"Metric{mname}{sn}", fmt(get(d, "by_station", st), 4)))
        for b, bn in BUILDING_MACRO.items():
            lines.append(macro(f"Metric{mname}{bn}", fmt(get(d, "by_building", b), 4)))
        for comp in ("comfort", "energy", "carbon"):
            lines.append(macro(f"Decomp{mname}{comp.capitalize()}", fmt(get(d, "decomp", comp), 4)))
            for st, sn in STATION_NAMES.items():
                lines.append(macro(f"Decomp{mname}{comp.capitalize()}{sn}",
                                   fmt(get(d, "decomp_by_station", st, comp), 4)))
        lines.append(macro(f"SecPerStep{mname}", fmt(get(d, "seconds_per_step_mean"), 3)))
        lines.append(macro(f"PolicyMs{mname}", fmt(get(d, "policy_ms_per_step_mean"), 2)))
    # ---- comparisons ----
    for pol, mname in POLICY_MACRO.items():
        c = get(fs, "comparisons", f"transfer_vs_{pol}")
        lines.append(macro(f"Diff{mname}", fmt(get(c, "diff"), 4, signed=True)))
        lines.append(macro(f"DiffLo{mname}", fmt(get(c, "ci_lo"), 4, signed=True)))
        lines.append(macro(f"DiffHi{mname}", fmt(get(c, "ci_hi"), 4, signed=True)))
        lines.append(macro(f"Ratio{mname}", fmt(get(c, "ratio"), 3)))
        lines.append(macro(f"RatioLo{mname}", fmt(get(c, "ratio_ci_lo"), 3)))
        lines.append(macro(f"RatioHi{mname}", fmt(get(c, "ratio_ci_hi"), 3)))
        r = get(c, "ratio")
        lines.append(macro(f"RelRed{mname}", fmt(None if r is None else 1.0 - r, pct=True)))
        rlo, rhi = get(c, "ratio_ci_lo"), get(c, "ratio_ci_hi")
        lines.append(macro(f"RelRedLo{mname}", fmt(None if rhi is None else 1.0 - rhi, pct=True)))
        lines.append(macro(f"RelRedHi{mname}", fmt(None if rlo is None else 1.0 - rlo, pct=True)))
        lines.append(macro(f"Wins{mname}", fmt(get(c, "wins"), int_=True)))
        lines.append(macro(f"Losses{mname}", fmt(get(c, "losses"), int_=True)))
        pv = get(c, "wilcoxon", "p_value")
        lines.append(macro(f"PWilcoxon{mname}", pfmt(pv)))
        for st, sn in STATION_NAMES.items():
            lines.append(macro(f"Diff{mname}{sn}", fmt(get(c, "by_station_diff", st), 4, signed=True)))
    lines.append(macro("NBoot", fmt(get(fs, "comparisons", "transfer_vs_pid_water", "n_boot"), int_=True)))
    # ---- local vs official gap ----
    for pol, mname in POLICY_MACRO.items():
        g = get(fs, "local_vs_official_gap", pol)
        lines.append(macro(f"GapMean{mname}", fmt(get(g, "mean_rel_diff"), pct=True, signed=True)))
        lines.append(macro(f"GapMin{mname}", fmt(get(g, "min_rel_diff"), pct=True, signed=True)))
        lines.append(macro(f"GapMax{mname}", fmt(get(g, "max_rel_diff"), pct=True, signed=True)))
    # ---- per-scenario worst / best ----
    ours = get(fs, "policies", "transfer", "per_scenario") or {}
    base = get(fs, "policies", "pid_water", "per_scenario") or get(fs, "policies", "pid_water_official", "per_scenario") or {}
    if ours and base:
        diffs = {k: ours[k]["score"] - base[k]["score"] for k in ours if k in base}
        worst = max(diffs, key=diffs.get)
        best = min(diffs, key=diffs.get)
        lines.append(macro("WorstScen", worst.replace("_", r"\_")))
        lines.append(macro("WorstScenDiff", fmt(diffs[worst], 4, signed=True)))
        lines.append(macro("BestScen", best.replace("_", r"\_")))
        lines.append(macro("BestScenDiff", fmt(diffs[best], 4, signed=True)))
        lines.append(macro("NScenWorse", fmt(sum(1 for v in diffs.values() if v > 0), int_=True)))
        lines.append(macro("MaxOursScore", fmt(max(v["score"] for v in ours.values()), 4)))
        lines.append(macro("MaxOursScen", max(ours, key=lambda k: ours[k]["score"]).replace("_", r"\_")))
        lines.append(macro("MaxBaseScore", fmt(max(v["score"] for v in base.values()), 4)))
    else:
        for m in ("WorstScen", "WorstScenDiff", "BestScen", "BestScenDiff", "NScenWorse", "MaxOursScore", "MaxBaseScore", "MaxOursScen"):
            lines.append(macro(m, MISSING))

    # ---- building sizes (zones / AHUs), from whichever score file has them ----
    sizes = {}
    for src in (fs, hs):
        for pol in ("transfer", "pid_water"):
            sizes.update(get(src, "policies", pol, "building_size") or {})
    for b, bn in BUILDING_MACRO.items():
        lines.append(macro(f"Zones{bn}", fmt(get(sizes, b, "num_zones"), int_=True)))
        lines.append(macro(f"Ahus{bn}", fmt(get(sizes, b, "num_ahus"), int_=True)))
    # ---- held-out generated buildings ----
    lines.append(macro("NHeld", fmt(get(hs, "n_scenarios"), int_=True)))
    held_b = sorted({k.split("/")[0] for k in (get(hs, "scenarios") or [])})
    lines.append(macro("NHeldBuild", fmt(len(held_b) if hs else None, int_=True)))
    for pol, mname in (("transfer", "Ours"), ("pid_water", "PidWater"), ("transfer_v4", "OursVFour")):
        for b, bn in BUILDING_MACRO.items():
            if b.startswith("building_0"):
                lines.append(macro(f"HeldMetric{mname}{bn}", fmt(get(hs, "policies", pol, "by_building", b), 4)))
        for st, sn in STATION_NAMES.items():
            lines.append(macro(f"HeldMetric{mname}{sn}", fmt(get(hs, "policies", pol, "by_station", st), 4)))
    for pol, mname in (("transfer", "Ours"), ("pid_water", "PidWater"), ("transfer_v4", "OursVFour")):
        lines.append(macro(f"HeldMetric{mname}", fmt(get(hs, "policies", pol, "metric"), 4)))
    c = get(hs, "comparisons", "transfer_vs_pid_water")
    lines.append(macro("HeldDiff", fmt(get(c, "diff"), 4, signed=True)))
    lines.append(macro("HeldDiffLo", fmt(get(c, "ci_lo"), 4, signed=True)))
    lines.append(macro("HeldDiffHi", fmt(get(c, "ci_hi"), 4, signed=True)))
    lines.append(macro("HeldRatio", fmt(get(c, "ratio"), 3)))
    lines.append(macro("HeldRatioLo", fmt(get(c, "ratio_ci_lo"), 3)))
    lines.append(macro("HeldRatioHi", fmt(get(c, "ratio_ci_hi"), 3)))
    r = get(c, "ratio")
    lines.append(macro("HeldRelRed", fmt(None if r is None else 1.0 - r, pct=True)))
    lines.append(macro("HeldWins", fmt(get(c, "wins"), int_=True)))
    pv = get(c, "wilcoxon", "p_value")
    lines.append(macro("HeldPWilcoxon", pfmt(pv)))
    c4 = get(hs, "comparisons", "transfer_vs_transfer_v4")
    lines.append(macro("HeldVFourDiff", fmt(get(c4, "diff"), 5, signed=True)))
    lines.append(macro("HeldVFourDiffLo", fmt(get(c4, "ci_lo"), 5, signed=True)))
    lines.append(macro("HeldVFourDiffHi", fmt(get(c4, "ci_hi"), 5, signed=True)))
    lines.append(macro("HeldVFourRatio", fmt(get(c4, "ratio"), 3)))
    lines.append(macro("HeldVFourWins", fmt(get(c4, "wins"), int_=True)))
    for comp in ("comfort", "energy", "carbon"):
        lines.append(macro(f"HeldDecompOurs{comp.capitalize()}", fmt(get(hs, "policies", "transfer", "decomp", comp), 4)))
        lines.append(macro(f"HeldDecompPidWater{comp.capitalize()}", fmt(get(hs, "policies", "pid_water", "decomp", comp), 4)))

    # ---- tuning ----
    # The log also holds the ablation rows and the v5 candidates (params["_policy"] == "v5");
    # the random-search set is everything else.
    ab = load(RES / "tune" / "ablation.json")
    rs = random_search_evals(tl, ab)
    n_cfg = len(rs) if tl else None
    lines.append(macro("NTuneConfigs", fmt(n_cfg, int_=True)))
    lines.append(macro("NTuneRandom", fmt(None if n_cfg is None else n_cfg - 1, int_=True)))
    lines.append(macro("NAblation", fmt(len(ab["rows"]) if ab else None, int_=True)))
    if ab:
        for row in ab["rows"]:
            lines.append(macro(f"Abl{row['macro']}", fmt(row.get("score"), 5)))
            lines.append(macro(f"AblRel{row['macro']}", fmt(row.get("rel_vs_best"), pct=True, signed=True)))
            lines.append(macro(f"AblRelDef{row['macro']}", fmt(row.get("rel_vs_default"), pct=True, signed=True)))
    # v5 candidates on the screening set (compare_candidates.py)
    v5 = [r for r in (get(cs, "screening") or []) if r.get("tag") == "v5"]
    lines.append(macro("NCandV", fmt(len(v5) if cs else None, int_=True)))
    lines.append(macro("CandBestScreen", fmt(v5[0]["score"] if v5 else None, 5)))
    lines.append(macro("CandSatColdScreen", fmt(next((r["score"] for r in v5 if r["diff_vs_best"] == {"sat_cool_hi": 285.0}), None), 5)))
    lines.append(macro("CandNightEightScreen", fmt(next((r["score"] for r in v5 if r["diff_vs_best"] == {"night_low_ext": 8.0}), None), 5)))
    if tl and tl.get("evals"):
        scored = [(v["score"], h) for h, v in rs.items() if "score" in v]
        if scored:
            scored.sort()
            lines.append(macro("TuneBestScreen", fmt(scored[0][0], 4)))
            lines.append(macro("TuneWorstScreen", fmt(scored[-1][0], 4)))
        else:
            lines += [macro("TuneBestScreen", MISSING), macro("TuneWorstScreen", MISSING)]
        dflt = next((v for v in tl["evals"].values() if v.get("is_default")), None)
        lines.append(macro("TuneDefaultScreen", fmt(get(dflt, "score"), 4)))
    else:
        lines += [macro("TuneBestScreen", MISSING), macro("TuneWorstScreen", MISSING), macro("TuneDefaultScreen", MISSING)]
    tb = load(RES / "tune_baseline" / "pid_water__agg.json")
    lines.append(macro("TunePidWaterScreen", fmt(get(tb, "leaderboard_metric") if (tb and tb.get("n_scenarios") == 6) else None, 4)))
    # parameter macros: tuned values if present, else the policy's defaults (flagged)
    if not bp:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sadr_pol_m", ROOT / "submission" / "transfer_policy.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bp = dict(mod.DEFAULT_PARAMS)
            lines.append(macro("ParSource", "default (untuned)"))
        except Exception:  # noqa: BLE001
            bp = {}
            lines.append(macro("ParSource", MISSING))
    else:
        lines.append(macro("ParSource", "tuned"))
    par_names = {"margin_occ": "ParMarginOcc", "margin_pre": "ParMarginPre", "night_low_ext": "ParNightLowExt",
                 "night_high_ext": "ParNightHighExt", "kq_w_per_k": "ParKqWPerK", "ki_w_per_k_step": "ParKiWPerKStep",
                 "sat_cool_hi": "ParSatCoolHi", "sat_mix_floor": "ParSatMixFloor", "lead_safety": "ParLeadSafety",
                 "rate0_kph": "ParRateZeroKph", "holiday_check_h": "ParHolidayCheckH",
                 "heat_season_steps": "ParHeatSeasonSteps", "min_on_steps": "ParMinOnSteps",
                 "disch_margin_k": "ParDischMarginK", "rate_ema": "ParRateEma", "lead_min_h": "ParLeadMinH",
                 "lead_max_h": "ParLeadMaxH", "valve_target": "ParValveTarget", "q_cap_w": "ParQCapW",
                 "sb_hyst_k": "ParSbHystK", "q_sb_w": "ParQSbW"}
    for k, name in par_names.items():
        v = bp.get(k)
        lines.append(macro(name, MISSING if v is None else f"{v:g}"))

    # ---- derived diagnostics that the text quotes (each from a file on disk) ----
    # (a) v3 snapshot: fraction of unoccupied steps with any AHU running (b8/fairbanks_8, 8,640 steps)
    lines.append(macro("VthreeAhuOnUnocc", fmt(ahu_on_frac_unoccupied(
        RES / "dev_full" / "building_train_8" / "fairbanks_8" / "transfer"), pct=True)))
    # (b) peak outside-air temperature in the Phoenix strips (from the saved AHU logs of our runs)
    lines.append(macro("PhoenixPeakOatC", fmt(peak_oat_c(RES / "full", "phoenix"), 0)))
    # (c) organizer pid_water: loss in the extreme climates relative to the mean of the mild ones
    off = get(fs, "policies", "pid_water_official", "by_station") or {}
    mild = [off.get(st) for st in ("denver", "atlanta", "singapore") if off.get(st)]
    mild_mean = sum(mild) / len(mild) if len(mild) == 3 else None
    for st, sn in (("fairbanks", "Fairbanks"), ("phoenix", "Phoenix")):
        v = None if (mild_mean is None or not off.get(st)) else off[st] / mild_mean
        lines.append(macro(f"ExtremeRatio{sn}", fmt(v, 1)))
    # (d) extra boiler tank dissipation at 350 K vs 310 K (kit formula, tank in 294 K air), kW
    lines.append(macro("TankLossExtraKw", fmt(tank_loss_extra_kw(), 2)))

    # ---- analysis.json (analyze_final.py): where the loss goes ----
    an = load(RES / "analysis.json")
    lines.append(macro("NAnalysis", fmt(get(an, "n_scenarios"), int_=True)))
    for pol, mname in (("transfer", "Ours"), ("pid_water", "PidWater")):
        m = get(an, "means", pol) or {}
        lines.append(macro(f"UnoccShare{mname}", fmt(m.get("unocc_share"), pct=True)))
        lines.append(macro(f"RegretShare{mname}", fmt(m.get("regret_share"), pct=True)))
        lines.append(macro(f"EnergyShare{mname}", fmt(m.get("energy_share"), pct=True)))
        lines.append(macro(f"CarbonShare{mname}", fmt(m.get("carbon_share"), pct=True)))
        lines.append(macro(f"OccOut{mname}", fmt(m.get("occ_frac_zone_steps_out"), pct=True)))
        lines.append(macro(f"OccOutGtOne{mname}", fmt(m.get("occ_frac_zone_steps_out_gt1"), pct=True)))
        lines.append(macro(f"OccWorstDev{mname}", fmt(m.get("occ_mean_worst_dev_k"), 2)))
        lines.append(macro(f"FirstWorkdayRatio{mname}", fmt(m.get("first_workday_regret_ratio"), 2)))
        lines.append(macro(f"FirstWorkdayRatioMedian{mname}", fmt(m.get("first_workday_regret_ratio_median"), 2)))
        for st, sn in STATION_NAMES.items():
            lines.append(macro(f"UnoccShare{mname}{sn}", fmt(get(m, "unocc_share_by_station", st), pct=True)))
        lbh = m.get("loss_by_hour") or []
        if lbh:
            import numpy as _np
            arr = _np.array(lbh)
            lines.append(macro(f"PeakLossHour{mname}", fmt(int(arr.argmax()), int_=True)))
            lines.append(macro(f"PeakLossShare{mname}", fmt(float(arr.max() / arr.sum()) if arr.sum() > 0 else None, pct=True)))
        else:
            lines += [macro(f"PeakLossHour{mname}", MISSING), macro(f"PeakLossShare{mname}", MISSING)]
    m0 = get(an, "means", "transfer") or {}
    lines.append(macro("NFirstWorkdayWorse", fmt(m0.get("n_first_workday_worse"), int_=True)))
    lines.append(macro("NFirstWorkdayTotal", fmt(m0.get("n_first_workday_total"), int_=True)))

    # ---- Kaggle public leaderboard snapshot (read by the coordinator, saved as JSON) ----
    lb = None
    for f in sorted(RES.glob("kaggle_leaderboard_*.json")):
        lb = load(f)
        lb_date = f.stem.replace("kaggle_leaderboard_", "")
    lines.append(macro("LbDate", lb_date if lb else MISSING))
    lines.append(macro("LbNTeams", fmt(get(lb, "n_teams"), int_=True)))
    ranks = {r["rank"]: r["score"] for r in (get(lb, "top") or [])}
    for rk, name in ((1, "One"), (8, "Eight"), (10, "Ten"), (30, "Thirty"), (49, "FortyNine")):
        lines.append(macro(f"LbRank{name}", fmt(ranks.get(rk), 5)))
    ours_m = get(fs, "policies", "transfer", "metric")
    lines.append(macro("OursVsLbOne", fmt(None if (ours_m is None or not ranks.get(1)) else ours_m / ranks[1], 1)))

    # ---- v5 candidates at full length (Mac), winner, v4 values of the revised parameters ----
    full_c = [c for c in (get(cs, "full", "candidates") or []) if c.get("complete")]
    lines.append(macro("NCandFull", fmt(len(full_c) if cs else None, int_=True)))
    win = full_c[0] if full_c else None
    lines.append(macro("CandWinner", _tex(win["name"]) if win else MISSING))
    lines.append(macro("CandWinnerMetric", fmt(get(win, "metric"), 5)))
    lines.append(macro("CandWinnerVFourMetric", fmt(get(win, "metric_v4_same_scenarios"), 5)))
    lines.append(macro("CandWinnerRatio", fmt(get(win, "ratio_vs_v4"), 3)))
    lines.append(macro("CandWinnerDiff", fmt(get(win, "diff"), 5, signed=True)))
    lines.append(macro("CandWinnerCiLo", fmt(get(win, "ci_lo"), 5, signed=True)))
    lines.append(macro("CandWinnerCiHi", fmt(get(win, "ci_hi"), 5, signed=True)))
    lines.append(macro("CandWinnerWins", fmt(get(win, "wins"), int_=True)))

    def cand_metric(params):
        return next((c["metric"] for c in full_c if c["params"] == params), None)
    lines.append(macro("CandSatColdFull", fmt(cand_metric({"sat_cool_hi": 285.0}), 5)))
    lines.append(macro("CandNightEightFull", fmt(cand_metric({"night_low_ext": 8.0}), 5)))
    v4p = get(ab, "best", "params") or {}
    for k, name in (("sat_cool_hi", "VFourSatCoolHi"), ("night_low_ext", "VFourNightLowExt"),
                    ("night_high_ext", "VFourNightHighExt"), ("margin_occ", "VFourMarginOcc")):
        lines.append(macro(name, MISSING if k not in v4p else f"{v4p[k]:g}"))
    # cross-machine check: laptop v4 (final_scores_local: ours=transfer) vs Mac v4 (final_scores: transfer_v4)
    lines.append(macro("LocalVFourMetric", fmt(get(fl, "policies", "transfer", "metric"), 4)))
    lines.append(macro("LocalPidWaterMetric", fmt(get(fl, "policies", "pid_water", "metric"), 4)))
    mac_v4 = get(fs, "policies", "transfer_v4", "per_scenario") or {}
    lap_v4 = get(fl, "policies", "transfer", "per_scenario") or {}
    common = [k for k in mac_v4 if k in lap_v4]
    if common:
        rel = [abs(lap_v4[k]["total"] - mac_v4[k]["total"]) / abs(mac_v4[k]["total"]) for k in common]
        lines.append(macro("MachineGapMean", f"{100 * sum(rel) / len(rel):.3f}\\%"))
        lines.append(macro("MachineGapMax", f"{100 * max(rel):.3f}\\%"))
        lines.append(macro("MachineGapN", fmt(len(common), int_=True)))
    else:
        lines += [macro("MachineGapMean", MISSING), macro("MachineGapMax", MISSING), macro("MachineGapN", MISSING)]
    mac_pw = get(fs, "policies", "pid_water", "per_scenario") or {}
    lap_pw = get(fl, "policies", "pid_water", "per_scenario") or {}
    common = [k for k in mac_pw if k in lap_pw]
    lines.append(macro("MachineGapPidWater", (
        f"{100 * sum(abs(lap_pw[k]['total'] - mac_pw[k]['total']) / abs(mac_pw[k]['total']) for k in common) / len(common):.3f}\\%")
        if common else MISSING))
    write_tuning_tables(ab, cs)

    # ---- environment ----
    lines.append(macro("SimSecPerStep", fmt(get(ei, "sec_per_step_median"), 3)))
    lines.append(macro("SimMinPerScenario", fmt(get(ei, "min_per_scenario_median"), 1)))
    lines.append(macro("TotalCoreHours", fmt(get(ei, "total_core_hours"), 1)))

    OUT.write_text("".join(lines))
    write_per_scenario_table(fs, hs)
    n_missing = sum(1 for ln in lines if MISSING in ln)
    print(f"wrote {OUT} ({len(lines)} macros, {n_missing} missing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
