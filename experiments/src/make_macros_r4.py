"""Round-4 macros and the round-4 ledger table (called from make_macros.py).

Inputs (missing -> \\textbf{??}):
  results/round4/diag_round4.json, diag_cooling_v6.json   diagnosis of the shipped v6 (diag_round4.py)
  results/round4/generator_ranges.json                     shipped six vs the kit's default ranges
  results/round4/screen_summary_screen_vs_r4_c00_v6.json   screen (screen_round4.py summarize)
  results/round4/decision.json                             choice under the pre-registered rule
  results/round4/confirm_<cand>.json                        full-length comparison vs v6 (confirm_round4.py)
  kit/smart_buildings/heldout_scenarios_r4{s,c}             zone maps of the new buildings (sizes)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R4 = RES / "round4"
KS = ROOT / "kit" / "smart_buildings"
MISSING = r"\textbf{??}"
NUM = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
       11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen", 16: "Sixteen", 0: "Zero"}
SHORT = {  # compact labels for the ledger table
    "r4_c00_v6": "shipped v6 (reference)",
    "r4_c01_fcap_floor": "$f_{\\text{cap}}^{\\text{pre}}$ 0.316 (floor-pressure flow)",
    "r4_c02_fcap025": "$f_{\\text{cap}}^{\\text{pre}}$ 0.25, no clip",
    "r4_c03_fcap015": "$f_{\\text{cap}}^{\\text{pre}}$ 0.15, no clip",
    "r4_c04_fcap005": "$f_{\\text{cap}}^{\\text{pre}}$ 0.05, no clip",
    "r4_c05_disch025": "discharge margin 0.25\\,K",
    "r4_c06_mix_relief": "mixed-handler SAT relief",
    "r4_c07_occ_dyn": "occupied pressure cap ($e_0$ 0.3, span 1\\,K)",
    "r4_c08_occ_dyn_mild": "occupied pressure cap ($e_0$ 0.1, span 0.5\\,K)",
    "r4_c09_flush": "night flush (outside air)",
    "r4_c10_sb_neutral": "reheat set-back zones' forced air",
    "r4_c11_flush_guard": "night flush, not in heating season",
    "r4_c12_disch0": r"discharge margin 0\,K",
    "r4_c13_neutral_cold": "c10, only below the setback floor",
    "r4_c14_comp_a": "composite c12+c08+c11+c01+c10",
    "r4_c15_comp_b": "composite c12+c08+c11+c01+c13",
}
SHIPPED_FRESH = ("building_0601", "building_0602", "building_0603", "building_0606")


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def fmt(x, nd=4, pct=False, signed=False, int_=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return MISSING
    if int_:
        return f"{int(round(x))}"
    if pct:
        return (f"{100 * x:+.1f}" if signed else f"{100 * x:.1f}") + r"\%"
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def macro(name, value):
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def _tex(s):
    return s.replace("_", r"\_")


def cid(name):
    """r4_c07_occ_dyn -> 'Seven' (macro-safe id)."""
    try:
        return NUM[int(name.split("_")[1][1:])]
    except (IndexError, ValueError, KeyError):
        return None


def _areas(zone_map_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("v7_for_areas", HERE / "policy_candidates" / "transfer_policy_v7.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._room_areas(np.load(zone_map_path))


def building_sizes(tag):
    out = {}
    base = KS / f"heldout_scenarios_{tag}"
    if not base.exists():
        return out
    for b in sorted(base.iterdir()):
        ws = sorted(w for w in b.iterdir() if (w / "zone_map.npy").exists())
        if not ws:
            continue
        a = _areas(ws[0] / "zone_map.npy")
        gin = (ws[0] / "config.gin").read_text()
        out[b.name] = {"zones": len(a), "area": float(a.sum()), "median": float(np.median(a)), "max": float(a.max()),
                       "ahus": gin.count("max_air_flow_rate = 20.0")}
    return out


def diag_macros():
    L = []
    d = load(R4 / "diag_round4.json")
    ps = (d or {}).get("per_scenario", {})

    def mean(keys, f):
        v = [f(ps[k]) for k in keys]
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else None
    for s, tag in (("public", "Pub"), ("r3", "RThree")):
        hot = [k for k, o in ps.items() if o["set"] == s and k.split("/")[1].split("_")[0] in ("phoenix", "singapore")]
        allk = [k for k, o in ps.items() if o["set"] == s]
        L.append(macro(f"RFCoolWm{tag}", fmt(mean(hot, lambda o: o["cool_elec_w_per_m2"]), 2)))
        L.append(macro(f"RFCoolNorm{tag}", fmt(mean(hot, lambda o: o["cool_elec_w_per_ahu_norm"]), 3)))
        L.append(macro(f"RFAreaPerAhu{tag}", fmt(mean(allk, lambda o: o["area_per_ahu_m2"]), 0)))
        fa = mean(allk, lambda o: o.get("fan_above_floor_loss", 0.0))
        met = mean(allk, lambda o: o["metric"])
        fan = mean(allk, lambda o: o["loss_components"]["fan"])
        L.append(macro(f"RFFanAbove{tag}", fmt(fa, 5)))
        L.append(macro(f"RFFanAbove{tag}Share", fmt(None if not (fa and met) else fa / met, pct=True)))
        L.append(macro(f"RFFanAbove{tag}FanShare", fmt(None if not (fa and fan) else fa / fan, pct=True)))
        mix = mean(allk, lambda o: o.get("fan_above_floor_loss_mixed_292", 0.0))
        cold = mean(allk, lambda o: o.get("fan_above_floor_loss_cold_285", 0.0))
        L.append(macro(f"RFFanAboveMix{tag}Share", fmt(None if not (fa and mix is not None) else mix / fa, pct=True)))
        L.append(macro(f"RFFanAboveCold{tag}Share", fmt(None if not (fa and cold is not None) else cold / fa, pct=True)))
        cf = [k for k, o in ps.items() if o["set"] == s and k.split("/")[1].startswith("fairbanks") and o.get("oat_mean_c", 99) < 0]
        L.append(macro(f"RFVentGas{tag}", fmt(mean(cf, lambda o: o.get("vent_heat_over_gas")), pct=True)))
        L.append(macro(f"RFIdleUnoccGas{tag}", fmt(mean(cf, lambda o: o["idle_zone_cooling_over_gas_by_mode"]["1"]
                                                       + o["idle_zone_cooling_over_gas_by_mode"]["2"]), pct=True)))
        L.append(macro(f"RFNColdFairbanks{tag}", fmt(len(cf), int_=True)))
        mild = [k for k, o in ps.items() if o["set"] == s and k.split("/")[1].split("_")[0] in ("denver", "atlanta")
                and o.get("cool_elec_w_per_m2", 0) > 0.5]
        L.append(macro(f"RFFlushMild{tag}", fmt(mean(mild, lambda o: o.get("unocc_steps_oat_le_Tzone_minus3_share")), pct=True)))
        L.append(macro(f"RFFlushHot{tag}", fmt(mean(hot, lambda o: o.get("unocc_steps_oat_le_Tzone_minus3_share")), pct=True)))
        L.append(macro(f"RFEconHot{tag}", fmt(mean(hot, lambda o: o.get("share_econ_active")), pct=True)))
        L.append(macro(f"RFPreCoolHot{tag}", fmt(mean(hot, lambda o: o["share_by_mode"]["1"]), pct=True)))
    fo = (ps.get("building_train_2/fairbanks_2") or {}).get("oat_mean_c")
    L.append(macro("RFFlushFailOatC", MISSING if fo is None else f"{fo:.0f}"))
    g = load(R4 / "generator_ranges.json")
    sh, rg = (g or {}).get("shipped", {}), (g or {}).get("regenerated_default", {})
    b1, r1 = sh.get("building_train_1"), rg.get("building_train_1")
    L.append(macro("RFTrainOneSize", MISSING if not b1 else f"{b1['width']}\\,$\\times$\\,{b1['height']}"))
    L.append(macro("RFSeedZeroDefaultSize", MISSING if not r1 else f"{r1['width']}\\,$\\times$\\,{r1['height']}"))
    if sh:
        L.append(macro("RFShippedWidth", f"{min(v['width'] for v in sh.values())}--{max(v['width'] for v in sh.values())}"))
        L.append(macro("RFShippedHeight", f"{min(v['height'] for v in sh.values())}--{max(v['height'] for v in sh.values())}"))
        L.append(macro("RFShippedRoom", f"{min(v['min_room'] for v in sh.values())}--{max(v['max_room'] for v in sh.values())}"))
    else:
        L += [macro("RFShippedWidth", MISSING), macro("RFShippedHeight", MISSING), macro("RFShippedRoom", MISSING)]
    dr = (g or {}).get("default_ranges", {})
    L.append(macro("RFDefaultWidth", MISSING if "width" not in dr else f"{dr['width'][0]}--{dr['width'][1]}"))
    L.append(macro("RFDefaultHeight", MISSING if "height" not in dr else f"{dr['height'][0]}--{dr['height'][1]}"))
    return L


def set_macros():
    L = []
    for tag, mt in (("r4s", "Scr"), ("r4c", "Fresh")):
        bs = building_sizes(tag)
        L.append(macro(f"RF{mt}NBuild", fmt(len(bs) if bs else None, int_=True)))
        if bs:
            z = [v["zones"] for v in bs.values()]
            L.append(macro(f"RF{mt}ZonesMin", fmt(min(z), int_=True)))
            L.append(macro(f"RF{mt}ZonesMax", fmt(max(z), int_=True)))
            L.append(macro(f"RF{mt}ZoneAreaMax", fmt(max(v["max"] for v in bs.values()), 0)))
            sh = [v["median"] for b, v in bs.items() if b in SHIPPED_FRESH or b in ("building_0520", "building_0524")]
            de = [v["median"] for b, v in bs.items() if not (b in SHIPPED_FRESH or b in ("building_0520", "building_0524"))]
            L.append(macro(f"RF{mt}ShippedZoneMedian", fmt(float(np.median(sh)) if sh else None, 0)))
            L.append(macro(f"RF{mt}DefaultZoneMedian", fmt(float(np.median(de)) if de else None, 0)))
        else:
            for k in ("ZonesMin", "ZonesMax", "ZoneAreaMax", "ShippedZoneMedian", "DefaultZoneMedian"):
                L.append(macro(f"RF{mt}{k}", MISSING))
    return L


def screen_macros():
    L = []
    ss = load(R4 / "screen_summary_screen_vs_r4_c00_v6.json")
    rows = {r["name"]: r for r in (ss or {}).get("rows", [])}
    L.append(macro("RFScreenSteps", MISSING if not ss else f"{ss['steps']:,}"))
    L.append(macro("RFNScreenPub", fmt(len((ss or {}).get("sets", {}).get("public", [])) or None, int_=True)))
    L.append(macro("RFNScreenHeld", fmt(len((ss or {}).get("sets", {}).get("held", [])) or None, int_=True)))
    singles = [n for n in rows if n.startswith("r4_c") and n != "r4_c00_v6" and n in SHORT and "comp" not in n]
    comps = [n for n in rows if "comp" in n]
    L.append(macro("RFNComposites", fmt(len(comps) or None, int_=True)))
    L.append(macro("RFNSingles", fmt(len(singles) or None, int_=True)))
    for cls, mn in (("helps", "Helps"), ("worse", "Worse"), ("n.s.", "Ns"), ("public only", "PubOnly")):
        L.append(macro(f"RFN{mn}", fmt(sum(1 for n in singles if rows[n].get("class") == cls) if singles else None, int_=True)))
    for n, r in rows.items():
        i = cid(n)
        if i is None or n == "r4_c00_v6":
            continue
        for s, st in (("public", "Pub"), ("held", "Held"), ("held_new20", "New"), ("held_old6", "Old")):
            d = r.get(s) or {}
            L.append(macro(f"RFC{i}{st}D", fmt(None if d.get("diff") is None else d["diff"] * 1e5, 1, signed=True)))
            L.append(macro(f"RFC{i}{st}Lo", fmt(None if d.get("ci_lo") is None else d["ci_lo"] * 1e5, 1, signed=True)))
            L.append(macro(f"RFC{i}{st}Hi", fmt(None if d.get("ci_hi") is None else d["ci_hi"] * 1e5, 1, signed=True)))
            L.append(macro(f"RFC{i}{st}Rel", fmt(None if not d.get("ratio") else d["ratio"] - 1.0, pct=True, signed=True)))
            L.append(macro(f"RFC{i}{st}Wins", MISSING if d.get("wins") is None else f"{d['wins']}/{d['n_paired']}"))
        L.append(macro(f"RFC{i}Class", r.get("class", MISSING)))
    return L


def confirm_macros():
    L = []
    dec = load(R4 / "decision.json") or {}
    cand = dec.get("chosen")
    L.append(macro("RFChosen", MISSING if not cand else _tex(cand)))
    L.append(macro("RFChosenShort", MISSING if not cand else SHORT.get(cand, _tex(cand))))
    c = load(R4 / f"confirm_{cand}.json") if cand else None
    S = (c or {}).get("sets", {})
    for s, mt in (("pub30", "Pub"), ("old40", "Old"), ("old34", "OldClean"), ("old_screen6", "OldScr"), ("fresh40", "Fresh"),
                  ("fresh_shipped20", "FreshShip"), ("fresh_default20", "FreshDef"), ("pooled74", "Pool")):
        d = S.get(s) or {}
        L.append(macro(f"RFConf{mt}N", fmt(d.get("n"), int_=True)))
        L.append(macro(f"RFConf{mt}Cand", fmt(d.get("cand"), 5)))
        L.append(macro(f"RFConf{mt}VSix", fmt(d.get("v6"), 5)))
        L.append(macro(f"RFConf{mt}Diff", fmt(None if d.get("diff") is None else d["diff"] * 1e5, 1, signed=True)))
        L.append(macro(f"RFConf{mt}Lo", fmt(None if d.get("ci_lo") is None else d["ci_lo"] * 1e5, 1, signed=True)))
        L.append(macro(f"RFConf{mt}Hi", fmt(None if d.get("ci_hi") is None else d["ci_hi"] * 1e5, 1, signed=True)))
        L.append(macro(f"RFConf{mt}Rel", fmt(d.get("rel"), pct=True, signed=True)))
        L.append(macro(f"RFConf{mt}RelLo", fmt(d.get("rel_ci_lo"), pct=True, signed=True)))
        L.append(macro(f"RFConf{mt}RelHi", fmt(d.get("rel_ci_hi"), pct=True, signed=True)))
        L.append(macro(f"RFConf{mt}Wins", MISSING if d.get("wins") is None else f"{d['wins']}/{d['n']}"))
        # unsigned reductions for prose ("lowers the loss by X%, CI lo to hi")
        L.append(macro(f"RFConf{mt}Red", fmt(None if d.get("rel") is None else -d["rel"], pct=True)))
        L.append(macro(f"RFConf{mt}RedLo", fmt(None if d.get("rel_ci_hi") is None else -d["rel_ci_hi"], pct=True)))
        L.append(macro(f"RFConf{mt}RedHi", fmt(None if d.get("rel_ci_lo") is None else -d["rel_ci_lo"], pct=True)))
    shipped = (c or {}).get("ship_rule_met")
    L.append(macro("RFShipRuleMet", MISSING if shipped is None else ("met" if shipped else "not met")))
    return L


def chosen_param_macros():
    """Parameter values of the chosen round-4 candidate (v7 defaults + its overrides)."""
    import importlib.util
    dec = load(R4 / "decision.json") or {}
    cand = dec.get("chosen")
    spec = importlib.util.spec_from_file_location("v7_params", HERE / "policy_candidates" / "transfer_policy_v7.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prm = dict(mod.DEFAULT_PARAMS)
    ov = load(HERE / "policy_candidates" / f"{cand}.json") if cand else None
    if ov:
        prm.update(ov)
    L = []
    for k, name in (("disch_margin_k", "ParRFDischMargin"), ("occ_press_e0", "ParRFOccEzero"),
                    ("occ_press_span", "ParRFOccSpan"), ("flush_dt_k", "ParRFFlushDt"), ("f_cap_pre", "ParRFFCapPre"),
                    ("flush_window_h", "ParRFFlushWindow")):
        v = prm.get(k) if ov is not None else None
        L.append(macro(name, MISSING if v is None else (f"{v:.3f}" if k == "f_cap_pre" else f"{v:g}")))
    return L


def round4_macros():
    return diag_macros() + set_macros() + screen_macros() + confirm_macros() + pid_water_macros() + chosen_param_macros() + dec_macros() + max_scen_macros() + v6_param_macros()


def write_round4_table():
    """Round-4 ledger: every candidate on both screening sets vs the shipped v6 (r4_c00)."""
    ss = load(R4 / "screen_summary_screen_vs_r4_c00_v6.json")
    if not ss:
        return []
    dec = load(R4 / "decision.json") or {}
    chosen = dec.get("chosen")
    rows = sorted(ss["rows"], key=lambda r: r["name"])
    L = ["\\begin{table}[h]\n\\caption{Round-4 candidates (v7 code, every switch off = the shipped v6) on the two "
         f"screening sets at {ss['steps']:,} steps: public-{len(ss['sets']['public'])} (the six earlier public screening "
         "scenarios and the other four Fairbanks strips) and held-" + str(len(ss['sets']['held'])) + " (the six round-3 "
         "held-out screening scenarios and 20 scenarios of four new screening buildings). $\\Delta$ = paired mean "
         "difference against the shipped v6 in units of $10^{-5}$ per step with its bootstrap 95\\% CI (negative "
         "favours the candidate); verdict as in Table~\\ref{tab:candidates_r3} (\\emph{helps} = held-out CI below "
         "zero and public CI not above it). $\\star$ marks the candidate chosen for full-length confirmation. "
         "Pre-registration and parameter files: \\texttt{experiments/results/round4/PREREG.md}, "
         "\\texttt{experiments/src/policy\\_candidates/r4\\_*.json}.}\n"
         "\\label{tab:candidates_r4}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{2.2pt}\n"
         "\\begin{tabular}{llrrrrl}\n\\toprule\n"
         " & & \\multicolumn{2}{c}{public screen} & \\multicolumn{2}{c}{held-out screen} & \\\\\n"
         "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\n"
         "id & change vs shipped v6 & metric & $\\Delta$ [CI] & metric & $\\Delta$ [CI] & verdict \\\\\n\\midrule\n"]

    def delta(d):
        if not d or d.get("diff") is None:
            return "--"
        return f"{d['diff'] * 1e5:+.1f} [{d['ci_lo'] * 1e5:+.1f}, {d['ci_hi'] * 1e5:+.1f}]"
    for r in rows:
        n = r["name"]
        ident = n.split("_")[1] if n != "r4_c00_v6" else "c00"
        if n == chosen:
            ident = "$\\star$" + ident
        label = SHORT.get(n) or _tex(dec.get("labels", {}).get(n, n))
        pub, held = r.get("public") or {}, r.get("held") or {}
        verdict = "base" if n == "r4_c00_v6" else r.get("class", "--")
        pm = "--" if pub.get("metric") is None else f"{pub['metric']:.5f}"
        hm = "--" if held.get("metric") is None else f"{held['metric']:.5f}"
        L.append(f"{ident} & {label} & {pm} & {delta(pub)} & {hm} & {delta(held)} & {verdict} \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n\n")
    return L


def write_round4_per_scenario():
    """paper/per_scenario_table_r4.tex: the fresh confirmation set, v6 vs the confirmed candidate."""
    out = ROOT / "paper" / "per_scenario_table_r4.tex"
    dec = load(R4 / "decision.json") or {}
    cand = dec.get("chosen")
    c = load(R4 / f"confirm_{cand}.json") if cand else None
    fr = ((c or {}).get("sets", {}).get("fresh40") or {}).get("per_scenario") or {}
    L = ["% AUTO-GENERATED by experiments/src/make_macros_r4.py -- do not edit by hand\n"]
    if not fr:
        L.append("% fresh-40: no data yet\n")
        out.write_text("".join(L))
        return
    sizes = building_sizes("r4c")
    keys = sorted(fr, key=lambda k: (k.split("/")[0] not in SHIPPED_FRESH, k))
    half = (len(keys) + 1) // 2
    L.append(r"\begin{table}[h]" "\n" r"\caption{Fresh confirmation set (round 4, never screened; 8,640 steps): score "
             r"($|$total$/8640|$, lower is better) of the shipped v6 and of the round-4 candidate " + _tex(cand) +
             r"; z/A = zones/AHUs; buildings 0601, 0602, 0603 and 0606 are drawn in the shipped six's parameter "
             r"ranges, 0604, 0607, 0610 and 0639 in the kit's default ranges (0610: largest rooms, 0639: largest floor "
             r"area of seeds 606--699).}" "\n" r"\label{tab:per_scenario_fresh}" "\n" r"\centering\scriptsize" "\n"
             r"\setlength{\tabcolsep}{2.5pt}" "\n" r"\begin{tabular}{lrrrr@{\hspace{10pt}}lrrrr}" "\n" r"\toprule" "\n"
             r"scenario & z/A & v6 & cand. & $\Delta$ & scenario & z/A & v6 & cand. & $\Delta$ \\" "\n" r"\midrule" "\n")

    def cells(k):
        if k is None:
            return " & & & & "
        b = k.split("/")[0]
        s = sizes.get(b, {})
        v = fr[k]
        rel = v["cand"] / v["v6"] - 1.0
        return (f"{_tex(k.replace('building_', ''))} & {s.get('zones', '?')}/{s.get('ahus', '?')} & {v['v6']:.4f} & "
                f"{v['cand']:.4f} & {100 * rel:+.1f}" + r"\%")
    for i in range(half):
        a = keys[i]
        b2 = keys[i + half] if i + half < len(keys) else None
        L.append(cells(a) + " & " + cells(b2) + r" \\" + "\n")
    L.append(r"\bottomrule" "\n" r"\end{tabular}" "\n" r"\end{table}" "\n")
    out.write_text("".join(L))


def _ratio_ci(a, b, keys, n_boot=5000):
    A = np.array([a[k] for k in keys])
    B = np.array([b[k] for k in keys])
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    r = A[idx].mean(axis=1) / B[idx].mean(axis=1)
    lo, hi = np.percentile(r, [2.5, 97.5])
    return float(A.mean() / B.mean()), float(lo), float(hi), int((A < B).sum())


def pid_water_macros():
    """The confirmed candidate against the locally re-run pid_water (public and old held-out sets)."""
    L = []
    dec = load(R4 / "decision.json") or {}
    cand = dec.get("chosen")
    c = load(R4 / f"confirm_{cand}.json") if cand else None
    S = (c or {}).get("sets", {})
    pw = {}
    for f in ("final_scores.json", "heldout_scores.json", "heldout_r3_scores.json"):
        d = load(RES / f) or {}
        for k, v in ((d.get("policies") or {}).get("pid_water", {}).get("per_scenario") or {}).items():
            pw[k] = v["score"]
    for s, mt in (("pub30", "Pub"), ("old40", "Old")):
        ps = (S.get(s) or {}).get("per_scenario") or {}
        cs = {k: v["cand"] for k, v in ps.items()}
        keys = sorted(k for k in cs if k in pw)
        if keys:
            r, lo, hi, w = _ratio_ci(cs, pw, keys)
            L += [macro(f"RFPw{mt}Ratio", fmt(r, 3)), macro(f"RFPw{mt}RatioLo", fmt(lo, 3)),
                  macro(f"RFPw{mt}RatioHi", fmt(hi, 3)), macro(f"RFPw{mt}Wins", f"{w}/{len(keys)}"),
                  macro(f"RFPw{mt}Metric", fmt(float(np.mean([pw[k] for k in keys])), 5))]
        else:
            L += [macro(f"RFPw{mt}{x}", MISSING) for x in ("Ratio", "RatioLo", "RatioHi", "Wins", "Metric")]
    # per-station means of the candidate on the public set (for Table 1)
    ps = (S.get("pub30") or {}).get("per_scenario") or {}
    for st, sn in (("fairbanks", "Fairbanks"), ("denver", "Denver"), ("atlanta", "Atlanta"), ("phoenix", "Phoenix"),
                   ("singapore", "Singapore")):
        v = [x["cand"] for k, x in ps.items() if k.split("/")[1].startswith(st)]
        L.append(macro(f"RFConfPubCand{sn}", fmt(float(np.mean(v)) if v else None, 4)))
    return L


def dec_macros():
    """Loss decomposition of v6 and v7 on the three confirmation sets (decompose_loss.py outputs)."""
    L = []
    pairs = {"Pub": (RES / "round3" / "loss_decomposition_public_v6.json", R4 / "loss_decomposition_public_v7.json"),
             "Old": (R4 / "loss_decomposition_old40_v6.json", R4 / "loss_decomposition_old40_v7.json"),
             "Fresh": (R4 / "loss_decomposition_fresh40_v6.json", R4 / "loss_decomposition_fresh40_v7.json")}
    for tag, (fa, fb) in pairs.items():
        A, B = load(fa), load(fb)
        oa, ob = (A or {}).get("overall") or {}, (B or {}).get("overall") or {}
        for c in ("comfort", "fan", "cooling", "gas"):
            va = (oa.get("components") or {}).get(c)
            vb = (ob.get("components") or {}).get(c)
            cn = c.capitalize()
            L.append(macro(f"RFDec{tag}{cn}VSix", fmt(va, 5)))
            L.append(macro(f"RFDec{tag}{cn}VSeven", fmt(vb, 5)))
            L.append(macro(f"RFDec{tag}{cn}Diff", fmt(None if va is None or vb is None else (vb - va) * 1e5, 1, signed=True)))
        sa = ((A or {}).get("by_station") or {}).get("fairbanks") or {}
        sb = ((B or {}).get("by_station") or {}).get("fairbanks") or {}
        L.append(macro(f"RFDec{tag}FairbanksVSix", fmt(sa.get("metric"), 5)))
        L.append(macro(f"RFDec{tag}FairbanksVSeven", fmt(sb.get("metric"), 5)))
        L.append(macro(f"RFDec{tag}FairbanksRel", fmt(None if not sa.get("metric") or sb.get("metric") is None
                                                      else sb["metric"] / sa["metric"] - 1.0, pct=True, signed=True)))
    return L


def max_scen_macros():
    """The confirmed candidate's costliest public scenario and how many public scenarios it loses to pid_water."""
    dec = load(R4 / "decision.json") or {}
    cand = dec.get("chosen")
    c = load(R4 / f"confirm_{cand}.json") if cand else None
    ps = (((c or {}).get("sets") or {}).get("pub30") or {}).get("per_scenario") or {}
    if not ps:
        return [macro("RFMaxCandScen", MISSING), macro("RFMaxCandScore", MISSING), macro("RFNScenWorseCand", MISSING)]
    k = max(ps, key=lambda x: ps[x]["cand"])
    pw = (((load(RES / "final_scores.json") or {}).get("policies") or {}).get("pid_water") or {}).get("per_scenario") or {}
    worse = sum(1 for x, v in ps.items() if x in pw and v["cand"] > pw[x]["score"])
    return [macro("RFMaxCandScen", r"\texttt{" + _tex(k) + "}"), macro("RFMaxCandScore", fmt(ps[k]["cand"], 4)),
            macro("RFNScenWorseCand", fmt(worse if pw else None, int_=True))]


def v6_param_macros():
    """The shipped v6 values that v7 changed (results/tune/best_params_v6.json)."""
    b = load(RES / "tune" / "best_params_v6.json") or {}
    return [macro("VSixFCapPre", MISSING if "f_cap_pre" not in b else f"{b['f_cap_pre']:.3g}"),
            macro("VSixDischMargin", MISSING if "disch_margin_k" not in b else f"{b['disch_margin_k']:g}")]
