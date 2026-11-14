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
POLICY_MACRO = {"transfer": "Ours", "transfer_v5": "OursVFive", "transfer_v4": "OursVFour", "pid_water": "PidWater", "pid": "Pid",
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
        for f in results_dir.glob(f"building_*/{station}_*/transfer*/ahu_log.csv"):
            m = float(pd.read_csv(f, usecols=["outside_air"])["outside_air"].max())
            best = m if best is None else max(best, m)
        for f in results_dir.glob(f"building_*/{station}_*/transfer/diag.csv"):   # round-3 runs log the OAT here
            m = float(pd.read_csv(f, usecols=["oat_k"])["oat_k"].max())
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


PLAIN = {'ki_w_per_k_step': 'integral gain $k_i$ (W/K per step)', 'margin_pre': 'precondition margin (K)', 'sat_mix_floor': 'mixed-handler SAT floor (K)', 'sb_hyst_k': 'setback hysteresis (K)'}


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
            L.append(f"{PLAIN.get(r['param'], _tex(r['param']))} & {kind} ({r['value']:g}) & {r['score']:.5f} & "
                     f"{100 * r['rel_vs_best']:+.1f}\\% & {100 * r['rel_vs_default']:+.1f}\\% \\\\\n")
        L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")
    cands = (get(cs, "full", "candidates") or [])
    if cands:
        v4 = get(cs, "full", "v4_mac") or {}
        short = {"sat_cool_hi": "SAT", "night_low_ext": "nlo", "night_high_ext": "nhi", "margin_occ": "occ",
                 "lead_max_h": "lead"}
        L.append("\\begin{table}[h]\n\\caption{v5 candidates at full length (8,640 steps) on the 30 public scenarios, "
                 "run on the same machine as v4 (metric " + fmt(v4.get("metric"), 5) + "). Overrides are applied to the v4 "
                 "values (SAT = cooling supply-air temperature in K; nlo/nhi = low/high setback widening in K; occ = "
                 "occupied margin in K; lead = longest preconditioning lead in h); CI = paired bootstrap 95\\% CI of the "
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
    L += write_round3_table()
    from make_macros_r4 import write_round4_table
    L += write_round4_table()
    out.write_text("".join(L))


def write_round3_table() -> list[str]:
    """The round-3 (v6) candidates on both screening sets, from results/round3/candidates.json:
    metric, ratio against the shipped v5, and the paired difference against the v6 defaults (c00)
    with its bootstrap CI and the screen verdict under the shipping rule."""
    lg = load(RES / "round3" / "candidates.json")
    if not lg:
        return []
    cands = lg.get("candidates") or {}
    if not cands:
        return []
    steps = lg.get("screen_steps")
    short = {"f_cap_pre": "$f_{\\text{cap}}^{\\text{pre}}$", "f_cap_occ": "$f_{\\text{cap}}^{\\text{occ}}$",
             "gain_area_scaling": "area scaling", "per_zone_start": "per-zone start", "adaptive_floor": "adaptive floor",
             "area_scale_min": "scale min", "q_cap_w": "$q$ cap (W)", "margin_pre": "pre margin", "rate0_kph": "rate$_0$",
             "pre_latch": "latch", "lead_safety": "lead safety"}
    L = ["\\begin{table}[h]\n\\caption{Round-3 candidates (v6 code) on the two screening sets at "
         + (f"{steps:,}" if steps else "??") + " steps: six public scenarios and six held-out scenarios "
         "(building 0502 twice, buildings 0500, 0505, 0507 and 0509 once). Metric = leaderboard metric on the set; "
         "ratio = against the shipped v5 on the same scenarios; $\\Delta$ = paired mean difference against the v6 "
         "defaults (c00) in units of $10^{-5}$ with its bootstrap 95\\% CI (negative favours the candidate). "
         "Verdict under the shipping rule against c00: \\emph{rule met} = held-out CI below zero and public CI not "
         "above it; \\emph{public only} = only the public CI below zero; \\emph{worse} = a CI above zero; n.s. = "
         "neither. c01--c13 change one or two values of the v6 defaults (c03--c05 are ablations); c14--c16 combine "
         "the changes that helped; $\\star$ marks the shipped variant. Parameter files: "
         "\\texttt{experiments/src/policy\\_candidates/}.}\n"
         "\\label{tab:candidates_r3}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{2.2pt}\n"
         "\\begin{tabular}{llrrrrrrl}\n\\toprule\n"
         " & & \\multicolumn{3}{c}{public screen} & \\multicolumn{3}{c}{held-out screen} & \\\\\n"
         "\\cmidrule(lr){3-5}\\cmidrule(lr){6-8}\n"
         "id & change vs v6 defaults & metric & ratio & $\\Delta$ vs c00 [CI] & metric & ratio & "
         "$\\Delta$ vs c00 [CI] & verdict \\\\\n\\midrule\n"]

    def delta(d):
        if not d or d.get("diff") is None:
            return "--"
        s = 1e5
        return f"{d['diff'] * s:+.1f} [{d['ci_lo'] * s:+.1f}, {d['ci_hi'] * s:+.1f}]"

    def cell(d, d0):
        if not d or d.get("metric") is None:
            return "-- & -- & --"
        r = "--" if d.get("ratio") is None else f"{d['ratio']:.3f}"
        return f"{d['metric']:.5f} & {r} & {delta(d0)}"
    shipped = (lg.get("shipped") or {}).get("candidate")
    order = sorted(cands, key=lambda n: (n != "ref_v5", n))
    for name in order:
        e = cands[name]
        if name == "ref_v5":
            ident, change = "v5", "shipped v5 (reference)"
        else:
            ident = name.split("_")[1]
            pr = e.get("params") or {}
            change = ", ".join(f"{short.get(k, _tex(k))} {v:g}" for k, v in pr.items()) or "v6 defaults"
        if name == shipped:
            ident = "$\\star$" + ident
        verdict = {"r3_c00_v6_default": "base", "ref_v5": "--"}.get(name, e.get("screen_outcome_vs_c00", "--"))
        L.append(f"{ident} & {change} & {cell(e.get('screen_public'), e.get('screen_public_vs_c00'))} & "
                 f"{cell(e.get('screen_held'), e.get('screen_held_vs_c00'))} & {verdict} \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")
    return L


def write_per_scenario_table(fs, hs, r3=None) -> None:
    """paper/per_scenario_table.tex: every scenario's return and score for ours (the shipped
    policy), v5, v4, local pid_water and the organizer-provided pid_water (public set), then the
    two held-out sets of generated buildings."""
    out = ROOT / "paper" / "per_scenario_table.tex"
    L = ["% AUTO-GENERATED by experiments/src/make_macros.py -- do not edit by hand\n"]

    def block(scores, title, label, with_official):
        ours = get(scores, "policies", "transfer", "per_scenario") or {}
        v5 = get(scores, "policies", "transfer_v5", "per_scenario") or {}
        v4 = get(scores, "policies", "transfer_v4", "per_scenario") or {}
        loc = get(scores, "policies", "pid_water", "per_scenario") or {}
        off = get(scores, "policies", "pid_water_official", "per_scenario") or {}
        if not ours:
            L.append(f"% {label}: no data yet\n")
            return
        cols = "llrrrrrr" + ("r" if with_official else "")
        L.append("\\begin{table}[t]\n\\caption{" + title + "}\n\\label{" + label + "}\n\\centering\\scriptsize\n"
                 "\\setlength{\\tabcolsep}{2.5pt}\n\\begin{tabular}{" + cols + "}\n\\toprule\n")
        hdr = ("scenario & zones/AHUs & SADR v6 return & v6 score & v5 score & v4 score & "
               "pid\\_water return & pid\\_water score")
        if with_official:
            hdr += " & organizer"
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
            w5 = v5.get(k, {})
            row = (f"{_tex(k)} & {size} & {o['total']:.1f} & {sc} & "
                   + (f"{w5['score']:.4f}" if w5 else "--") + " & "
                   + (f"{v['score']:.4f}" if v else "--") + " & "
                   + (f"{b['total']:.1f} & {b['score']:.4f}" if b else "-- & --"))
            if with_official:
                row += " & " + (f"{f['score']:.4f}" if f else "--")
            L.append(row + " \\\\\n")
        L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")

    block(fs, "Per-scenario results on the 30 public scenarios (8,640 steps). Score is $|$total$/8640|$, lower is "
              "better; bold marks scenarios where SADR beats the locally re-run \\texttt{pid\\_water}; organizer = "
              "the \\texttt{pid\\_water} score from the kit's \\texttt{baseline\\_returns.json}.",
          "tab:per_scenario", True)
    block(hs, "Per-scenario results on the generated held-out buildings 0501 and 0502 (8,640 steps), SADR vs locally run "
              "\\texttt{pid\\_water}.", "tab:per_scenario_held", False)
    if r3:
        block(r3, "Per-scenario results on the six generated held-out buildings of round 3 (8,640 steps), SADR vs locally run "
                  "\\texttt{pid\\_water}.", "tab:per_scenario_held_r3", False)
    out.write_text("".join(L))


R3_BUILDINGS = {"building_0500": "Bfivehundred", "building_0505": "Bfivefive", "building_0507": "Bfiveseven",
                "building_0508": "Bfiveeight", "building_0509": "Bfivenine", "building_0511": "Bfiveeleven"}


def _comp_macros(prefix: str, c: dict | None) -> list[str]:
    out = [macro(f"{prefix}Diff", fmt(get(c, "diff"), 5, signed=True)),
           macro(f"{prefix}DiffLo", fmt(get(c, "ci_lo"), 5, signed=True)),
           macro(f"{prefix}DiffHi", fmt(get(c, "ci_hi"), 5, signed=True)),
           macro(f"{prefix}Ratio", fmt(get(c, "ratio"), 3)),
           macro(f"{prefix}RatioLo", fmt(get(c, "ratio_ci_lo"), 3)),
           macro(f"{prefix}RatioHi", fmt(get(c, "ratio_ci_hi"), 3)),
           macro(f"{prefix}Wins", fmt(get(c, "wins"), int_=True)),
           macro(f"{prefix}Losses", fmt(get(c, "losses"), int_=True)),
           macro(f"{prefix}PWilcoxon", pfmt(get(c, "wilcoxon", "p_value")))]
    r = get(c, "ratio")
    out.append(macro(f"{prefix}RelRed", fmt(None if r is None else 1.0 - r, pct=True)))
    rlo, rhi = get(c, "ratio_ci_lo"), get(c, "ratio_ci_hi")
    out.append(macro(f"{prefix}RelRedLo", fmt(None if rhi is None else 1.0 - rhi, pct=True)))
    out.append(macro(f"{prefix}RelRedHi", fmt(None if rlo is None else 1.0 - rlo, pct=True)))
    return out


def pooled_heldout_macros(hs, r3) -> list[str]:
    """Both held-out sets pooled (buildings 0501/0502 + the six round-3 buildings), and the same pool
    without the six scenarios whose first 10 days were used by the round-3 screen (the 'unscreened'
    subset). Paired bootstrap over scenarios exactly as score_all.py (5,000 resamples, seed 0)."""
    import numpy as _np
    from score_all import paired_bootstrap, wilcoxon
    ss = load(RES / "round3" / "screen_summary.json")
    screened = set(get(ss, "sets", "held") or [])
    L = []

    def per(pol):
        out = {}
        for sc in (hs, r3):
            for k, v in (get(sc, "policies", pol, "per_scenario") or {}).items():
                out[k] = v["score"]
        return out
    ours, v5, pw = per("transfer"), per("transfer_v5"), per("pid_water")
    for tag, excl in (("HeldAll", set()), ("HeldUnscr", screened)):
        keys = sorted(k for k in ours if k in v5 and k in pw and k not in excl)
        complete = bool(hs) and bool(r3) and len(keys) > 0
        L.append(macro(f"N{tag}", fmt(len(keys) if complete else None, int_=True)))
        L.append(macro(f"N{tag}Build", fmt(len({k.split('/')[0] for k in keys}) if complete else None, int_=True)))
        for pol, mname, d in (("transfer", "Ours", ours), ("transfer_v5", "OursVFive", v5), ("pid_water", "PidWater", pw)):
            L.append(macro(f"{tag}Metric{mname}", fmt(float(_np.mean([d[k] for k in keys])) if complete else None, 4)))
            L.append(macro(f"{tag}Metric{mname}Five", fmt(float(_np.mean([d[k] for k in keys])) if complete else None, 5)))
        for other, oname, d in (("transfer_v5", "VFive", v5), ("pid_water", "PidWater", pw)):
            c = None
            if complete:
                A = _np.array([ours[k] for k in keys]); B = _np.array([d[k] for k in keys])
                c = paired_bootstrap(A, B)
                c["wilcoxon"] = wilcoxon(A, B)
            L += _comp_macros(f"{tag}{oname}", c)
        if complete:
            A5 = _np.mean([v5[k] for k in keys]); B5 = _np.mean([pw[k] for k in keys])
            L.append(macro(f"{tag}RatioVFivePidWater", fmt(A5 / B5, 3)))
        else:
            L.append(macro(f"{tag}RatioVFivePidWater", MISSING))
    L.append(macro("NHeldScreened", fmt(len(screened) if ss else None, int_=True)))
    return L


def round3_macros(fs, hs) -> list[str]:
    """Macros for the round-3 revision: the shipped v6 against v5 on the public set, the previous
    held-out set and the new held-out set (heldout_r3_scores.json); the per-component loss
    decomposition (decompose_loss.py); the new buildings' sizes; the screening summary."""
    L = []
    r3 = load(RES / "heldout_r3_scores.json")
    for tag, sc in (("Pub", fs), ("Held", hs), ("HeldR", r3)):
        if tag == "Pub":   # Held/HeldR MetricOursVFive are written with the other held-out policy macros
            L.append(macro(f"{tag}MetricOursVFive", fmt(get(sc, "policies", "transfer_v5", "metric"), 4)))
        L += _comp_macros(f"{tag}VFive", get(sc, "comparisons", "transfer_vs_transfer_v5"))
        for st, sn in STATION_NAMES.items():
            L.append(macro(f"{tag}VFiveDiff{sn}", fmt(get(sc, "comparisons", "transfer_vs_transfer_v5", "by_station_diff", st), 5, signed=True)))
    for tag, sc in (("Held", hs), ("HeldR", r3)):
        _v5, _pw = get(sc, "policies", "transfer_v5", "metric"), get(sc, "policies", "pid_water", "metric")
        L.append(macro(f"{tag}RatioVFivePidWater", fmt(None if (not _v5 or not _pw) else _v5 / _pw, 3)))
    L.append(macro("NHeldR", fmt(get(r3, "n_scenarios"), int_=True)))
    r3_b = sorted({k.split("/")[0] for k in (get(r3, "scenarios") or [])})
    L.append(macro("NHeldRBuild", fmt(len(r3_b) if r3 else None, int_=True)))
    for pol, mname in (("transfer", "Ours"), ("transfer_v5", "OursVFive"), ("pid_water", "PidWater")):
        L.append(macro(f"HeldRMetric{mname}", fmt(get(r3, "policies", pol, "metric"), 4)))
        for st, sn in STATION_NAMES.items():
            L.append(macro(f"HeldRMetric{mname}{sn}", fmt(get(r3, "policies", pol, "by_station", st), 4)))
        for b, bn in R3_BUILDINGS.items():
            L.append(macro(f"HeldRMetric{mname}{bn}", fmt(get(r3, "policies", pol, "by_building", b), 4)))
        for comp in ("comfort", "energy", "carbon"):
            L.append(macro(f"HeldRDecomp{mname}{comp.capitalize()}", fmt(get(r3, "policies", pol, "decomp", comp), 4)))
    L += _comp_macros("HeldRPidWater", get(r3, "comparisons", "transfer_vs_pid_water"))
    L += pooled_heldout_macros(hs, r3)
    sizes = {}
    for pol in ("transfer", "pid_water", "transfer_v5"):
        sizes.update(get(r3, "policies", pol, "building_size") or {})
    for b, bn in R3_BUILDINGS.items():
        L.append(macro(f"Zones{bn}", fmt(get(sizes, b, "num_zones"), int_=True)))
        L.append(macro(f"Ahus{bn}", fmt(get(sizes, b, "num_ahus"), int_=True)))
    zs = [get(sizes, b, "num_zones") for b in R3_BUILDINGS if get(sizes, b, "num_zones") is not None]
    ah = [get(sizes, b, "num_ahus") for b in R3_BUILDINGS if get(sizes, b, "num_ahus") is not None]
    full = len(zs) == len(R3_BUILDINGS)
    L.append(macro("HeldRZonesMin", fmt(min(zs) if full else None, int_=True)))
    L.append(macro("HeldRZonesMax", fmt(max(zs) if full else None, int_=True)))
    L.append(macro("HeldRAhusMin", fmt(min(ah) if full else None, int_=True)))
    L.append(macro("HeldRAhusMax", fmt(max(ah) if full else None, int_=True)))
    import numpy as _np
    all_b = {}
    for tree, tag in ((RES / "final", "Pub"), (RES / "final_heldout", "Held"), (RES / "final_heldout_r3", "HeldR")):
        areas = []
        per_b = {}
        for f in sorted(tree.glob("building_*/*/transfer*/zones.npz")):
            b = f.parts[-4]
            if b in per_b:
                continue
            try:
                a_ = _np.load(f)["zone_area_m2"]
            except Exception:  # noqa: BLE001
                continue
            if _np.all(_np.isfinite(a_)):
                per_b[b] = a_
                areas += a_.tolist()
        all_b.update(per_b)
        L.append(macro(f"{tag}ZoneAreaMedian", fmt(float(_np.median(areas)) if areas else None, 0)))
        L.append(macro(f"{tag}ZoneAreaMax", fmt(float(max(areas)) if areas else None, 0)))
        L.append(macro(f"{tag}ZoneAreaMin", fmt(float(min(areas)) if areas else None, 0)))
    # the old held-out buildings' areas may only exist in the round-3 diag copies before assembly
    for f in sorted((RES / "mac" / "round3").glob("diag_v5_*/building_*/*/transfer/zones.npz")):
        b = f.parts[-4]
        if b not in all_b:
            try:
                a_ = _np.load(f)["zone_area_m2"]
                if _np.all(_np.isfinite(a_)):
                    all_b[b] = a_
            except Exception:  # noqa: BLE001
                pass
    for b, bn in {**BUILDING_MACRO, **R3_BUILDINGS}.items():
        a_ = all_b.get(b)
        L.append(macro(f"ZoneAreaMedian{bn}", fmt(None if a_ is None else float(_np.median(a_)), 0)))
        L.append(macro(f"ZoneAreaMax{bn}", fmt(None if a_ is None else float(a_.max()), 0)))
    for tag, fn in (("DecPubVFive", "loss_decomposition_public_v5.json"), ("DecPubOurs", "loss_decomposition_public_v6.json"),
                    ("DecHeldVFive", "loss_decomposition_heldout_v5.json"), ("DecHeldOurs", "loss_decomposition_heldout_v6.json"),
                    ("DecHeldRVFive", "loss_decomposition_heldout_r3_v5.json"), ("DecHeldROurs", "loss_decomposition_heldout_r3_v6.json")):
        d = load(RES / "round3" / fn)
        o = get(d, "overall")
        L.append(macro(f"{tag}N", fmt(get(d, "n_scenarios"), int_=True)))
        L.append(macro(f"{tag}Metric", fmt(get(o, "metric"), 5)))
        for comp in ("comfort", "fan", "cooling", "pump", "gas"):
            L.append(macro(f"{tag}{comp.capitalize()}", fmt(get(o, "components", comp), 5)))
            L.append(macro(f"{tag}{comp.capitalize()}Share", fmt(get(o, "shares", comp), pct=True)))
        for m, mn in (("0", "Occ"), ("1", "Pre"), ("2", "Sb")):
            bm = get(o, "by_mode", m)
            L.append(macro(f"{tag}Mode{mn}Share", fmt(None if (bm is None or not get(o, "metric")) else sum(bm.values()) / o["metric"], pct=True)))
        L.append(macro(f"{tag}UnoccShare", fmt(None if (o is None or not o.get("metric")) else sum(o["by_occupancy"]["unoccupied"].values()) / o["metric"], pct=True)))
        L.append(macro(f"{tag}IdleMinflow", fmt(get(o, "minflow_idle_share_of_supply_air_while_heating"), pct=True)))
        L.append(macro(f"{tag}OccOut", fmt(get(o, "occupied_zone_steps_out_of_band"), pct=True)))
        L.append(macro(f"{tag}RecoveryBig", fmt(get(o, "recovery_hours_mean_largest_quartile"), 2)))
        L.append(macro(f"{tag}RecoveryRest", fmt(get(o, "recovery_hours_mean_rest"), 2)))
        for st, sn in STATION_NAMES.items():
            g = get(d, "by_station", st)
            for comp in ("comfort", "fan", "cooling", "gas"):
                L.append(macro(f"{tag}{comp.capitalize()}Share{sn}", fmt(get(g, "shares", comp), pct=True)))
        for b, bn in {**BUILDING_MACRO, **R3_BUILDINGS}.items():
            g = get(d, "by_building", b)
            if g is not None:
                L.append(macro(f"{tag}Metric{bn}", fmt(get(g, "metric"), 5)))
                L.append(macro(f"{tag}ComfortShare{bn}", fmt(get(g, "shares", "comfort"), pct=True)))
                L.append(macro(f"{tag}RecoveryBig{bn}", fmt(get(g, "recovery_hours_mean_largest_quartile"), 2)))
    ss = load(RES / "round3" / "screen_summary.json")
    lg3 = load(RES / "round3" / "candidates.json")
    rows = {r["name"]: r for r in (get(ss, "rows") or [])}
    L.append(macro("ScreenSteps", f"{get(ss, 'steps'):,}" if get(ss, "steps") else MISSING))
    L.append(macro("NScreenCands", fmt(len([n for n in rows if n != "ref_v5"]) if ss else None, int_=True)))
    for name, mn in (("ref_v5", "RefVFive"), ("r3_c00_v6_default", "CZero"), ("r3_c01_fcap_pre1", "COne"),
                     ("r3_c02_fcap_pre05", "CTwo"), ("r3_c03_no_gain_scaling", "CThree"), ("r3_c04_no_zone_start", "CFour"),
                     ("r3_c05_no_adaptive_floor", "CFive"), ("r3_c06_scale_min1", "CSix"), ("r3_c07_qcap20k", "CSeven"),
                     ("r3_c08_margin_pre05", "CEight"), ("r3_c09_rate0_1", "CNine"), ("r3_c10_fcap_occ07", "CTen"),
                     ("r3_c11_latch", "CEleven"), ("r3_c12_safety16", "CTwelve"), ("r3_c13_pre05_safety16", "CThirteen"),
                     ("r3_c14_pre05_min1", "CFourteen"), ("r3_c15_pre05_min1_mpre05", "CFifteen"),
                     ("r3_c16_pre035_min1", "CSixteen")):
        r = rows.get(name) or {}
        e0 = get(lg3, "candidates", name) or {}
        for s_, sn in (("public", "Pub"), ("held", "Held")):
            d = r.get(s_) or {}
            L.append(macro(f"Screen{mn}{sn}", fmt(d.get("metric"), 5)))
            L.append(macro(f"Screen{mn}{sn}Ratio", fmt(d.get("ratio"), 3)))
            L.append(macro(f"Screen{mn}{sn}Wins", fmt(d.get("wins"), int_=True)))
            # paired against the v6 defaults (c00), per-step difference in units of 1e-5
            d0 = e0.get(f"screen_{s_}_vs_c00") or {}
            for k_, kn in (("diff", ""), ("ci_lo", "Lo"), ("ci_hi", "Hi")):
                v_ = d0.get(k_)
                L.append(macro(f"Screen{mn}{sn}DZero{kn}", fmt(None if v_ is None else v_ * 1e5, 1, signed=True)))
            L.append(macro(f"Screen{mn}{sn}DZeroWins", fmt(d0.get("wins"), int_=True)))
        L.append(macro(f"Screen{mn}Verdict", e0.get("screen_outcome_vs_c00", "--")))
    # round-3 ledger counts and the shipped variant
    cl = get(lg3, "candidates") or {}
    verdicts = [e.get("screen_outcome_vs_c00") for n, e in cl.items() if n not in ("ref_v5", "r3_c00_v6_default")]
    L.append(macro("NRThreeVariants", fmt(len(verdicts) if lg3 else None, int_=True)))
    for v_, vn in (("worse", "Worse"), ("n.s.", "Ns"), ("rule met", "RuleMet"), ("public only", "PubOnly")):
        L.append(macro(f"NRThree{vn}", fmt(sum(1 for x in verdicts if x == v_) if lg3 else None, int_=True)))
    sh = get(lg3, "shipped") or {}
    L.append(macro("ShippedCand", _tex(sh["candidate"]) if sh.get("candidate") else MISSING))
    L.append(macro("ShippedCandId", sh["candidate"].split("_")[1] if sh.get("candidate") else MISSING))
    c0 = get(lg3, "full_length_c00_public") or {}
    L.append(macro("FullCZeroPub", fmt(c0.get("metric"), 5)))
    for k_, kn in (("diff", "Diff"), ("ci_lo", "DiffLo"), ("ci_hi", "DiffHi")):
        L.append(macro(f"FullCZeroPubVFive{kn}", fmt(get(c0, "vs_v5", k_), 5, signed=True)))
    L.append(macro("FullCZeroPubVFiveWins", fmt(get(c0, "vs_v5", "wins"), int_=True)))
    sc0 = get(lg3, "full_length_shipped_vs_c00_public") or {}
    for k_, kn in (("diff", "Diff"), ("ci_lo", "DiffLo"), ("ci_hi", "DiffHi")):
        L.append(macro(f"FullShipVsCZeroPub{kn}", fmt(sc0.get(k_), 5, signed=True)))
    L.append(macro("FullShipVsCZeroPubWins", fmt(sc0.get("wins"), int_=True)))
    L.append(macro("FullShipPub", fmt(sc0.get("metric_shipped"), 5)))
    ch = get(lg3, "full_length_c00_heldout") or {}
    ok = bool(ch.get("complete"))
    L.append(macro("FullCZeroHeldN", fmt(ch.get("n") if ok else None, int_=True)))
    L.append(macro("FullCZeroHeld", fmt(ch.get("metric") if ok else None, 5)))
    L.append(macro("FullCZeroHeldShip", fmt(ch.get("metric_shipped") if ok else None, 5)))
    for k_, kn in (("diff", "Diff"), ("ci_lo", "DiffLo"), ("ci_hi", "DiffHi")):
        L.append(macro(f"FullShipVsCZeroHeld{kn}", fmt(get(ch, "shipped_vs_c00", k_) if ok else None, 5, signed=True)))
    L.append(macro("FullShipVsCZeroHeldWins", fmt(get(ch, "shipped_vs_c00", "wins") if ok else None, int_=True)))
    # five-decimal versions for sentences that set our numbers against the leaderboard's
    L.append(macro("MetricOursFive", fmt(get(fs, "policies", "transfer", "metric"), 5)))
    L.append(macro("FullShipVsCZeroPubLosses", fmt(sc0.get("losses"), int_=True)))
    for tag, mn in (("b0502_v5", "TenDayVFive"), ("b0502_v6", "TenDayVSixA"), ("b0502_v6b", "TenDayVSixB"), ("b0502_v6c", "TenDayVSixC")):
        f = RES / "round3" / tag / "building_0502" / "denver_1" / "transfer" / "summary.json"
        sm = load(f)
        L.append(macro(f"{mn}Score", fmt(None if not sm else abs(sm["total_reward"]) / sm["total_steps"], 5)))
        L.append(macro(f"{mn}Regret", fmt(get(sm, "total_normalized_productivity_regret"), 2)))
    return L


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
    for pol, mname in (("transfer", "Ours"), ("pid_water", "PidWater"), ("transfer_v4", "OursVFour"), ("transfer_v5", "OursVFive")):
        for b, bn in BUILDING_MACRO.items():
            if b.startswith("building_0"):
                lines.append(macro(f"HeldMetric{mname}{bn}", fmt(get(hs, "policies", pol, "by_building", b), 4)))
        for st, sn in STATION_NAMES.items():
            lines.append(macro(f"HeldMetric{mname}{sn}", fmt(get(hs, "policies", pol, "by_station", st), 4)))
    for pol, mname in (("transfer", "Ours"), ("pid_water", "PidWater"), ("transfer_v4", "OursVFour"), ("transfer_v5", "OursVFive")):
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
                 "sb_hyst_k": "ParSbHystK", "q_sb_w": "ParQSbW", "f_cap_pre": "ParFCapPre", "f_cap_occ": "ParFCapOcc",
                 "area_scale_min": "ParAreaScaleMin", "area_scale_max": "ParAreaScaleMax", "area_ref_m2": "ParAreaRef"}
    for k, name in par_names.items():
        v = bp.get(k)
        lines.append(macro(name, MISSING if v is None else (f"{v:.3g}" if k == "f_cap_pre" else f"{v:g}")))

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
    _r = get(win, "ratio_vs_v4")
    lines.append(macro("CandWinnerRelRed", fmt(None if _r is None else 1.0 - _r, pct=True)))
    # v5 minus v4 per station (the candidate's station means against v4's on the same machine)
    for st, sn in STATION_NAMES.items():
        _a = get(win, "by_station", st)
        _b = get(fs, "policies", "transfer_v4", "by_station", st)
        lines.append(macro(f"CandWinnerDiff{sn}", fmt(None if (_a is None or _b is None) else _a - _b, 4, signed=True)))

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

    # ---- round 3: v6 vs v5 on the three sets, the new held-out set, the loss decomposition ----
    lines += round3_macros(fs, hs)

    # ---- round 4: diagnosis, screen, confirmation (make_macros_r4.py) ----
    from make_macros_r4 import round4_macros
    lines += round4_macros()

    # ---- round 5: Kaggle probes, local sets vs Kaggle, screen, confirmation (make_macros_r5.py) ----
    from make_macros_r5 import round5_macros, write_round5_kaggle_table, write_round5_per_scenario, write_round5_table
    lines += round5_macros()
    write_round5_kaggle_table()
    write_round5_table()
    write_round5_per_scenario()

    # ---- round 6: Kaggle compute, harsh sets vs Kaggle, decomposition, screen, confirmation (make_macros_r6.py) ----
    from make_macros_r6 import round6_macros, write_round6_kaggle_table, write_round6_table
    lines += round6_macros()
    write_round6_kaggle_table()
    write_round6_table()

    # ---- round 7: heating-lever analysis, screen, confirmation (make_macros_r7.py) ----
    from make_macros_r7 import round7_macros, write_round7_table
    lines += round7_macros()
    write_round7_table()

    # ---- round 8: confirmation of the round-7 ledger variant on HC2 (make_macros_r8.py) ----
    from make_macros_r8 import round8_macros
    lines += round8_macros()

    # ---- environment ----
    lines.append(macro("SimSecPerStep", fmt(get(ei, "sec_per_step_median"), 3)))
    lines.append(macro("SimMinPerScenario", fmt(get(ei, "min_per_scenario_median"), 1)))
    lines.append(macro("TotalCoreHours", fmt(get(ei, "total_core_hours"), 1)))

    OUT.write_text("".join(lines))
    write_per_scenario_table(fs, hs, load(RES / "heldout_r3_scores.json"))
    from make_macros_r4 import write_round4_per_scenario
    write_round4_per_scenario()
    n_missing = sum(1 for ln in lines if MISSING in ln)
    print(f"wrote {OUT} ({len(lines)} macros, {n_missing} missing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
