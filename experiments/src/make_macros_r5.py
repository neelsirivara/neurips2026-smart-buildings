"""Round-5 macros and the round-5 ledger table (called from make_macros.py).

Inputs (missing -> \\textbf{??}):
  results/kaggle_feedback.json                 Kaggle public scores of the submitted policies
  results/round5/set_comparison.json           local sets vs Kaggle (compare_sets_r5.py)
  results/round5/screen_summary.json           round-5 screen vs r5_c00_v7 (screen_round5.py)
  results/round5/decision.json                 choice under the pre-registered rule
  results/round5/confirm_<cand>.json           full-length confirmation vs v7 (confirm_round5.py)
  results/round5/loss_decomposition_r5m_v7.json, analysis/comfort_*.json, analysis/ahu_starts_per_day_v7.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R5 = RES / "round5"
MISSING = r"\textbf{??}"
SETNAME = {"P": "Pub", "M": "Minn", "P+M": "PubMinn", "O": "Old", "FS": "FreshShip", "FD": "FreshDef"}
POLNAME = {"v7": "VSeven", "v6": "VSix", "v5": "VFive", "pid_water": "Pid"}
SHORT = {
    "r5_c00_v7": "v7 (reference)",
    "r5_c01_mon15": "Monday lead $\\times$1.5, no Monday learning",
    "r5_c02_mon125": "Monday lead $\\times$1.25, no Monday learning",
    "r5_c03_wk3": "weekend setback $-3$/$+2$\\,K",
    "r5_c04_wk6": "weekend setback $-6$/$+4$\\,K",
    "r5_c05_lag10": "one-step lag compensation 1.0",
    "r5_c06_lag05": "one-step lag compensation 0.5",
    "r5_c07_fcapc05": "cooling preconditioning cap 0.5",
    "r5_c08_qsb8k": "setback burst 8\\,kW per 100\\,m$^2$",
    "r5_c09_preburst": "preconditioning at the cap from the start",
    "r5_c10_qcap20k": "request cap 20\\,kW per 100\\,m$^2$",
    "r5_c11_qcap30k": "request cap 30\\,kW per 100\\,m$^2$",
    "r5_c12_comp": "composite c04+c10",
}


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def macro(name, val):
    return f"\\newcommand{{\\{name}}}{{{val}}}\n"


def f(x, nd=5, pct=False, signed=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return MISSING
    if pct:
        return f"{100 * x:+.1f}\\%" if signed else f"{100 * x:.1f}\\%"
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def kaggle_macros():
    fb = load(RES / "kaggle_feedback.json") or {}
    sc = fb.get("scores_by_policy", {})
    L = [macro(f"RFiveKag{POLNAME[p]}", f(sc.get(p))) for p in POLNAME]
    L.append(macro("RFiveKagVEight", f(sc.get("v8_r5_c12_comp")) if sc.get("v8_r5_c12_comp") else "pending"))
    v7 = sc.get("v7")
    for p in ("v6", "v5", "pid_water"):
        r = (sc[p] / v7) if (sc.get(p) and v7) else None
        L.append(macro(f"RFiveKagRatio{POLNAME[p]}", f(r, 2 if p == "pid_water" else 3)))
    L.append(macro("RFiveKagPidOverVSevenInv", f((v7 / sc["pid_water"]) if (v7 and sc.get("pid_water")) else None, 3)))
    sub = next((s for s in fb.get("submissions", []) if s.get("ref") == 57580485), {})
    L.append(macro("RFiveKagRankVSeven", sub.get("public_rank", MISSING)))
    L.append(macro("RFiveKagTeamsVSeven", sub.get("teams", MISSING)))
    tp = (fb.get("third_party_calibration") or {}).get("rows", [])
    for i, r in enumerate(tp[:3]):
        nm = ["A", "B", "C"][i]
        L.append(macro(f"RFiveThird{nm}Local", f(r.get("local_public30"))))
        L.append(macro(f"RFiveThird{nm}Kag", f(r.get("kaggle_public"))))
        L.append(macro(f"RFiveThird{nm}Ratio", f(r.get("ratio"), 2)))
    n_probe = sum(1 for s in fb.get("submissions", []) if s.get("submitted_utc", "") >= "2026-10-25"
                  and "probe" in s.get("purpose", ""))
    L.append(macro("RFiveNProbes", n_probe))
    scmp = load(R5 / "set_comparison.json") or {}
    pv7 = (((scmp.get("sets") or {}).get("P") or {}).get("mean") or {}).get("v7")
    L.append(macro("RFiveKagGapPub", f(v7 / pv7, 2) if (v7 and pv7) else MISSING))
    return L


def set_macros():
    sc = load(R5 / "set_comparison.json") or {}
    sets = sc.get("sets", {})
    L = []
    for s, nm in SETNAME.items():
        row = sets.get(s, {})
        mean, n = row.get("mean", {}), row.get("n", {})
        for p, pn in POLNAME.items():
            L.append(macro(f"RFive{nm}{pn}", f(mean.get(p))))
            L.append(macro(f"RFive{nm}{pn}N", n.get(p, MISSING) if n.get(p) else MISSING))
        rat = row.get("ratio_to_v7_paired", {})
        for p in ("v6", "v5", "pid_water"):
            L.append(macro(f"RFive{nm}Ratio{POLNAME[p]}", f(rat.get(p, {}).get("ratio"), 2 if p == "pid_water" else 3)))
        pr = rat.get("pid_water", {}).get("ratio")
        L.append(macro(f"RFive{nm}PidOverVSevenInv", f(1.0 / pr if pr else None, 3)))
        L.append(macro(f"RFive{nm}Level", f(row.get("level_v7_over_kaggle"), 2)))
        L.append(macro(f"RFive{nm}ShapeErr", f(row.get("shape_err"), 3)))
    pr2 = sc.get("pr2_check", {})
    for p, pn in (("v7", "VSeven"), ("pid_water", "Pid")):
        r = pr2.get(p, {})
        L.append(macro(f"RFivePrTwo{pn}Rel", f(r.get("rel_change"), pct=True, signed=True) if r else MISSING))
        L.append(macro(f"RFivePrTwo{pn}N", r.get("n", MISSING) if r else MISSING))
        if r:
            rels = [v["rel"] for v in r["per_scenario"].values()]
            L.append(macro(f"RFivePrTwo{pn}RelMin", f(min(rels), pct=True, signed=True)))
            L.append(macro(f"RFivePrTwo{pn}RelMax", f(max(rels), pct=True, signed=True)))
        else:
            L += [macro(f"RFivePrTwo{pn}RelMin", MISSING), macro(f"RFivePrTwo{pn}RelMax", MISSING)]
    # Minneapolis by station / season
    bys = (sc.get("by_station") or {}).get("M", {}).get("minneapolis", {})
    L.append(macro("RFiveMinnStationVSeven", f(bys.get("v7", {}).get("mean"))))
    return L


def comfort_macros():
    L = []
    for lab, nm in (("pub30_v7", "Pub"), ("old40_v7", "Old"), ("fresh40_v7", "Fresh")):
        c = load(R5 / "analysis" / f"comfort_{lab}.json")
        if not c:
            L += [macro(f"RFiveComfHSix{nm}", MISSING), macro(f"RFiveComfMonRatio{nm}", MISSING)]
            continue
        h6 = c["comfort_by_hour"][6] / c["comfort"] if c["comfort"] else None
        d = c["comfort_h6_by_dow_mon0"]
        other = sum(d[1:5]) / 4.0
        L.append(macro(f"RFiveComfHSix{nm}", f(h6, pct=True)))
        L.append(macro(f"RFiveComfMonRatio{nm}", f(d[0] / other if other else None, 1)))
    a = load(R5 / "analysis" / "ahu_starts_per_day_v7.json") or {}
    vals = list(a.values())
    L.append(macro("RFiveAhuStartsMin", f(min(vals), 1) if vals else MISSING))
    L.append(macro("RFiveAhuStartsMax", f(max(vals), 1) if vals else MISSING))
    return L


def screen_macros():
    ss = load(R5 / "screen_summary.json") or {}
    dec = load(R5 / "decision.json") or {}
    cands = ss.get("candidates", {})
    singles = {k: v for k, v in cands.items() if k in SHORT and k != "r5_c00_v7" and not k.endswith("comp")}
    cnt = {}
    for v in singles.values():
        cnt[v["verdict"]] = cnt.get(v["verdict"], 0) + 1
    L = [macro("RFiveNSingles", len(singles) if singles else MISSING)]
    for verdict, nm in (("helps", "Helps"), ("public only", "PubOnly"), ("n.s.", "Ns"), ("worse", "Worse")):
        L.append(macro(f"RFiveN{nm}", cnt.get(verdict, 0) if singles else MISSING))
    def rel(cand, key):
        r = (cands.get(cand) or {}).get(key)
        return f(r["rel"], pct=True, signed=True) if r else MISSING
    L.append(macro("RFiveWkHeldRel", rel("r5_c04_wk6", "held")))
    L.append(macro("RFiveWkPubRel", rel("r5_c04_wk6", "public")))
    L.append(macro("RFiveMonHeldRel", rel("r5_c01_mon15", "held")))
    L.append(macro("RFivePreburstHeldRel", rel("r5_c09_preburst", "held")))
    L.append(macro("RFiveQcapHeldRel", rel("r5_c10_qcap20k", "held")))
    L.append(macro("RFiveQcapPubRel", rel("r5_c10_qcap20k", "public")))
    q = ((cands.get("r5_c10_qcap20k") or {}).get("held") or {}).get("per_scenario", {})
    b7 = q.get("r5x:building_train_7/fairbanks_1")
    L.append(macro("RFiveQcapBSevenRel", f(b7["cand"] / b7["ref"] - 1, pct=True, signed=True) if b7 else MISSING))
    nz = sum(1 for v in q.values() if abs(v["cand"] - v["ref"]) > 1e-12)
    L.append(macro("RFiveQcapNChanged", nz if q else MISSING))
    L.append(macro("RFiveChosen", (dec.get("chosen") or "none").replace("_", "\\_")))
    L.append(macro("RFiveScreenSteps", f"{ss.get('steps', 2880):,}"))
    ch = dec.get("chosen")
    for key, nm in (("held", "Held"), ("public", "Pub")):
        r = (cands.get(ch) or {}).get(key) if ch else None
        L.append(macro(f"RFiveChosen{nm}D", f(r["diff"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveChosen{nm}Lo", f(r["ci_lo"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveChosen{nm}Hi", f(r["ci_hi"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveChosen{nm}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
    return L


def confirm_macros():
    dec = load(R5 / "decision.json") or {}
    ch = dec.get("chosen")
    cf = load(R5 / f"confirm_{ch}.json") if ch else None
    L = [macro("RFiveShipRuleMet", ("met" if cf.get("ship_rule_met") else "not met") if cf else MISSING),
         macro("RFiveKaggleLikeSet", (cf or {}).get("kaggle_like", MISSING) if cf else MISSING)]
    fs = load(R5 / "fd_seed_sensitivity.json") or {}
    for s, nm in (("FD", "FreshDef"), ("P+M", "PubMinn"), ("pub30", "Pub"), ("r5m", "Minn")):
        L.append(macro(f"RFiveSeeds{nm}Below", (fs.get(s) or {}).get("n_seeds_upper_below_zero", MISSING)))
    # worst single scenario of the candidate on each confirmation set
    for s, nm in (("pub30", "Pub"), ("r5m", "Minn"), ("FD", "FreshDef")):
        per_s = (((cf or {}).get("sets") or {}).get(s) or {}).get("per_scenario", {})
        if per_s:
            k, v = max(per_s.items(), key=lambda kv: kv[1]["cand"] / kv[1]["v7"])
            L.append(macro(f"RFiveConf{nm}WorstRel", f(v["cand"] / v["v7"] - 1, pct=True, signed=True)))
            L.append(macro(f"RFiveConf{nm}WorstScen", "\\texttt{" + k.replace("_", "\\_") + "}"))
            n_ch = sum(1 for v in per_s.values() if abs(v["cand"] - v["v7"]) > 1e-12)
            L.append(macro(f"RFiveConf{nm}NChanged", n_ch))
        else:
            L += [macro(f"RFiveConf{nm}WorstRel", MISSING), macro(f"RFiveConf{nm}WorstScen", MISSING),
                  macro(f"RFiveConf{nm}NChanged", MISSING)]
    # v8 candidate per public station (Table 1 row)
    pub = ((cf or {}).get("sets") or {}).get("pub30") or {}
    per = pub.get("per_scenario", {})
    for st in ("fairbanks", "denver", "atlanta", "phoenix", "singapore"):
        vals = [v["cand"] for k, v in per.items() if k.split("/")[1].startswith(st)]
        L.append(macro(f"RFiveConfPubCand{st.capitalize()}", f(sum(vals) / len(vals), 4) if len(vals) == 6 else MISSING))
    for s, nm in (("pub30", "Pub"), ("r5m", "Minn"), ("P+M", "PubMinn"), ("old40", "Old"), ("FS", "FreshShip"),
                  ("FD", "FreshDef")):
        r = (cf or {}).get("sets", {}).get(s)
        L.append(macro(f"RFiveConf{nm}N", r["n"] if r else MISSING))
        L.append(macro(f"RFiveConf{nm}VSeven", f(r["v7"]) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Cand", f(r["cand"]) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Diff", f(r["diff"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Lo", f(r["ci_lo"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Hi", f(r["ci_hi"] * 1e5, 1, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Rel", f(r["rel"], pct=True, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}RelLo", f(r["rel_ci_lo"], pct=True, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}RelHi", f(r["rel_ci_hi"], pct=True, signed=True) if r else MISSING))
        L.append(macro(f"RFiveConf{nm}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
    return L


def dec_macros():
    d = load(R5 / "loss_decomposition_r5m_v7.json")
    L = []
    if not d:
        return [macro(f"RFiveDecMinn{k}Share", MISSING) for k in ("Gas", "Cooling", "Fan", "Comfort")]
    sh = d["overall"]["shares"]
    for k, nm in (("gas", "Gas"), ("cooling", "Cooling"), ("fan", "Fan"), ("comfort", "Comfort")):
        L.append(macro(f"RFiveDecMinn{nm}Share", f(sh.get(k), pct=True)))
    return L


def capacity_macros():
    c = load(R5 / "analysis" / "capacity_b7m1.json")
    names = ["RFiveCapScenMetric", "RFiveCapScenComfort", "RFiveCapNZones", "RFiveCapDefMin", "RFiveCapDefMax",
             "RFiveCapStepsMin", "RFiveCapStepsMax", "RFiveCapPaMax", "RFiveCapReqKwMin", "RFiveCapReqKwMax",
             "RFiveCapWaterKwMin", "RFiveCapWaterKwMax", "RFiveCapComfortShareOfMinn"]
    if not c or not c.get("zones"):
        return [macro(n, MISSING) for n in names]
    z = c["zones"][:4]
    sc = load(R5 / "analysis" / "comfort_r5m_v7.json") or {}
    tot = sum(r["comfort"] for r in sc.get("per_scenario", []))
    vals = [f(c["metric"], 4), f(c["comfort_per_step"], 4), len(z),
            f(min(r["mean_deficit_k"] for r in z), 1), f(max(r["mean_deficit_k"] for r in z), 1),
            f"{min(r['cold_occupied_steps'] for r in z):,}", f"{max(r['cold_occupied_steps'] for r in z):,}",
            f"{max(r['mean_handler_pa'] for r in z):.0f}",
            f(min(r["request_cap_w"] for r in z) / 1000, 0), f(max(r["request_cap_w"] for r in z) / 1000, 0),
            f(min(r["water_side_net_heat_w"] for r in z) / 1000, 0), f(max(r["water_side_net_heat_w"] for r in z) / 1000, 0),
            f(c["comfort_per_step"] / tot, pct=True) if tot else MISSING]
    return [macro(n, v) for n, v in zip(names, vals)]


def unsigned_variants(lines):
    """For every signed percentage macro X = +a% / -a%, also emit XAbs = a% (prose uses unsigned changes)."""
    import re
    out = []
    for ln in lines:
        m = re.match(r"\\newcommand\{\\(\w+)\}\{([+-])([0-9.]+)\\%\}", ln)
        if m:
            out.append(macro(m.group(1) + "Abs", m.group(3) + "\\%"))
            continue
        m = re.match(r"\\newcommand\{\\(\w*Rel\w*)\}\{(.*)\}", ln)
        if m and "??" in m.group(2):          # keep the unsigned variant defined while the value is missing
            out.append(macro(m.group(1) + "Abs", MISSING))
    return out


def param_macros():
    bp = load(RES / "tune" / "best_params.json") or {}
    v7 = load(RES / "tune" / "best_params_v7.json") or {}
    return [macro("RFiveParWkLo", f(bp.get("wk_ext_lo"), 0) if "wk_ext_lo" in bp else MISSING),
            macro("RFiveParWkHi", f(bp.get("wk_ext_hi"), 0) if "wk_ext_hi" in bp else MISSING),
            macro("RFiveParWkRampEnd", f(bp.get("wk_ramp_end_h"), 0) if "wk_ramp_end_h" in bp else MISSING),
            macro("RFiveParWkRampStart", f(bp["wk_ramp_end_h"] + bp["wk_ramp_h"], 0) if "wk_ramp_h" in bp else MISSING),
            macro("RFiveParQcapKw", f(bp.get("q_cap_w", 0) / 1000, 0) if "q_cap_w" in bp else MISSING),
            macro("RFiveParQcapKwVSeven", f(v7.get("q_cap_w", 0) / 1000, 0) if "q_cap_w" in v7 else MISSING)]


def round5_macros():
    L = (param_macros() + kaggle_macros() + set_macros() + comfort_macros() + screen_macros() + confirm_macros() + dec_macros()
         + capacity_macros())
    return L + unsigned_variants(L)


def write_round5_table():
    """Round-5 ledger: every candidate on both screening sets vs v7 (r5_c00_v7)."""
    ss = load(R5 / "screen_summary.json")
    out = ROOT / "paper" / "tuning_tables_r5.tex"
    if not ss:
        out.write_text("% round-5 ledger: no screen summary yet\n")
        return
    dec = load(R5 / "decision.json") or {}
    chosen = dec.get("chosen")

    def delta(d):
        if not d:
            return "--"
        return f"{d['diff'] * 1e5:+.1f} [{d['ci_lo'] * 1e5:+.1f}, {d['ci_hi'] * 1e5:+.1f}]"

    L = ["\\begin{table}[h]\n\\caption{Round-5 candidates (v8 code, every switch off = v7) on the two screening sets at "
         f"{ss['steps']:,} steps: held-{ss['n_held']} (six scenarios of the shipped buildings under Minneapolis strips "
         "not in the confirmation set, and four round-4 screening scenarios) and public-" + str(ss['n_pub']) + ". "
         "$\\Delta$ = paired mean difference against v7 in $10^{-5}$ per step with its bootstrap 95\\% CI (negative "
         "favours the candidate); verdicts as in Table~\\ref{tab:candidates_r4}. $\\star$: chosen for full-length "
         "confirmation. Pre-registration: \\texttt{experiments/results/round5/PREREG.md}.}\n"
         "\\label{tab:candidates_r5}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{2.2pt}\n"
         "\\begin{tabular}{llrrrrl}\n\\toprule\n"
         " & & \\multicolumn{2}{c}{public screen} & \\multicolumn{2}{c}{held-out screen} & \\\\\n"
         "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\n"
         "id & change vs v7 & metric & $\\Delta$ [CI] & metric & $\\Delta$ [CI] & verdict \\\\\n\\midrule\n"]
    L.append(f"c00 & {SHORT['r5_c00_v7']} & {ss['ref_pub_metric']:.5f} & -- & {ss['ref_held_metric']:.5f} & -- & -- \\\\\n")
    for c in sorted(ss["candidates"]):
        r = ss["candidates"][c]
        cid = c.split("_")[1]
        star = "$\\star$" if c == chosen else ""
        label = SHORT.get(c, c.replace("_", "\\_"))
        pm = f"{r['public']['cand']:.5f}" if r.get("public") else "--"
        hm = f"{r['held']['cand']:.5f}" if r.get("held") else "--"
        L.append(f"{cid}{star} & {label} & {pm} & {delta(r.get('public'))} & {hm} & {delta(r.get('held'))} & "
                 f"{r['verdict']} \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    out.write_text("".join(L))


def write_round5_per_scenario():
    """Appendix table: every Minneapolis scenario (set M) for v7, v6, v5, pid_water and the round-5 composite."""
    sc = load(R5 / "set_comparison.json") or {}
    per = (sc.get("per_scenario") or {}).get("M", {})
    dec = load(R5 / "decision.json") or {}
    ch = dec.get("chosen")
    cf = (load(R5 / f"confirm_{ch}.json") or {}) if ch else {}
    cand = {k: v["cand"] for k, v in ((cf.get("sets") or {}).get("r5m") or {}).get("per_scenario", {}).items()}
    out = ROOT / "paper" / "per_scenario_table_r5.tex"
    keys = sorted(set().union(*[set(v) for v in per.values()])) if per else []
    if not keys:
        out.write_text("% round-5 per-scenario table: no data yet\n")
        return

    def c(p, k):
        v = per.get(p, {}).get(k)
        return "--" if v is None else f"{v:.5f}"

    L = ["\\begin{table}[h]\n\\caption{Set M (round 5): the six shipped buildings under the Minneapolis strips "
         "(start dates: strip 1 January, 2 February, 3 April, 4 May, 5 June, 6 August, 7 September, 8 October), "
         "leaderboard score $|$total$|$/8,640 per scenario (lower is better). v8 cand.\\ = the round-5 composite "
         "(weekend setback and 20\\,kW request cap); -- = not run in the session.}\n"
         "\\label{tab:per_scenario_r5m}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{4pt}\n"
         "\\begin{tabular}{lrrrrr}\n\\toprule\n"
         "scenario & v7 & v8 cand. & v6 & v5 & \\texttt{pid\\_water} \\\\\n\\midrule\n"]
    for k in keys:
        v8 = f"{cand[k]:.5f}" if k in cand else "--"
        L.append(f"\\texttt{{{k.replace('_', chr(92) + '_')}}} & {c('v7', k)} & {v8} & {c('v6', k)} & {c('v5', k)} & "
                 f"{c('pid_water', k)} \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    out.write_text("".join(L))


def write_round5_kaggle_table():
    """Main-text table: Kaggle public scores against every local set (v7 level and the ratios to v7)."""
    sc = load(R5 / "set_comparison.json") or {}
    fb = load(RES / "kaggle_feedback.json") or {}
    kag = {k: v for k, v in (fb.get("scores_by_policy") or {}).items() if v is not None}
    out = ROOT / "paper" / "round5_kaggle_table.tex"
    rows = [("Kaggle public LB (about 10 hidden scenarios)", None),
            ("P: public 30 (shipped six, 5 stations)", "P"),
            ("M: shipped six $\\times$ Minneapolis (12)", "M"),
            ("P+M (42)", "P+M"),
            ("FS: fresh shipped-range buildings (20)", "FS"),
            ("FD: fresh default-range buildings (20)", "FD"),
            ("O: old held-out, default ranges (40)", "O")]

    def cell(x, nd):
        return "--" if x is None else f"{x:.{nd}f}"

    L = ["\\begin{table}[t]\n\\caption{Which local set predicts Kaggle? Leaderboard metric of v7 and the ratio of each "
         "other policy to v7 on the same scenarios (paired), against the Kaggle public scores of the same four policy "
         "files. $E$ = mean over the policies with a Kaggle score of $|\\ln r_{\\text{set}} - \\ln r_{\\text{Kaggle}}|$ "
         "(pre-registered shape error; smaller matches better). Kaggle runs the identical files: its interactive run of "
         "\\texttt{building\\_train\\_1/atlanta\\_2} matches the local total within 0.02\\% for all four.}\n"
         "\\label{tab:kaggle}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{3.5pt}\n"
         "\\begin{tabular}{lrrrrrr}\n\\toprule\n"
         "set & v7 & v7 / Kaggle & v6 / v7 & v5 / v7 & \\texttt{pid\\_water} / v7 & $E$ \\\\\n\\midrule\n"]
    for label, key in rows:
        if key is None:
            v7 = kag.get("v7")
            r = {p: (kag[p] / v7 if (p in kag and v7) else None) for p in ("v6", "v5", "pid_water")}
            L.append(f"{label} & {cell(v7, 5)} & 1 & {cell(r['v6'], 3)} & {cell(r['v5'], 3)} & "
                     f"{cell(r['pid_water'], 2)} & -- \\\\\n\\midrule\n")
            continue
        row = (sc.get("sets") or {}).get(key, {})
        rat = row.get("ratio_to_v7_paired", {})
        L.append(f"{label} & {cell((row.get('mean') or {}).get('v7'), 5)} & {cell(row.get('level_v7_over_kaggle'), 2)} & "
                 f"{cell(rat.get('v6', {}).get('ratio'), 3)} & {cell(rat.get('v5', {}).get('ratio'), 3)} & "
                 f"{cell(rat.get('pid_water', {}).get('ratio'), 2)} & {cell(row.get('shape_err'), 3)} \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    out.write_text("".join(L))

