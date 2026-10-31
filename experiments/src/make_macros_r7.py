"""Round-7 macros and the round-7 ledger table (called from make_macros.py). Missing inputs -> \\textbf{??}.

Inputs: results/round7/{check_identities.json, check_identities_minneapolis.json, zone_model_fit.json, analysis_r7.json,
checks_r7.json, screen_summary.json, decision.json, confirm_<chosen>.json, sets_r7.json}; results/kaggle_feedback.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R7 = RES / "round7"
PAPER = ROOT / "paper"
MISSING = r"\textbf{??}"
NAMES = {"r7_base": "base: v9 with the shorter lead (c07) instead of the nearer target (c06)",
         "r7_mbr": "base + model-based start", "r7_mbf": "base + model-chosen setback floor",
         "r7_mb": "base + model-based start and floor"}
TAG = {"r7_base": "Base", "r7_mbr": "Mbr", "r7_mbf": "Mbf", "r7_mb": "Mb"}


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def macro(name, val):
    return f"\\newcommand{{\\{name}}}{{{val}}}\n"


def f(x, nd=2, pct=False, signed=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return MISSING
    if pct:
        return (f"{100 * x:+.{nd}f}\\%" if signed else f"{100 * x:.{nd}f}\\%")
    return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"


def pabs(x, nd=1):
    return MISSING if x is None else f"{abs(100 * x):.{nd}f}\\%"


def analysis_macros():
    L = []
    ci = load(R7 / "check_identities.json") or {}
    cm = load(R7 / "check_identities_minneapolis.json") or {}
    an = load(R7 / "analysis_r7.json") or {}
    L.append(macro("RSevGErr", MISSING if ci.get("g_formula_max_abs_err") is None else
                   f"$10^{{{math.ceil(math.log10(max(ci['g_formula_max_abs_err'], 1e-16)))}}}$"))
    L.append(macro("RSevRecircCapShare", f(ci.get("recirc_share_at_cap_0p7"), 0, pct=True)))
    L.append(macro("RSevCapHeatShare", f(ci.get("net_heat_share_at_cap"), 0, pct=True)))
    L.append(macro("RSevCapStepShare", f(ci.get("discharge_at_cap_share"), 0, pct=True)))
    L.append(macro("RSevGasOverCoil", f(ci.get("boiler_over_reheat_sum"), 3)))
    L.append(macro("RSevGPaidFair", f(ci.get("g_energy_weighted"), 2)))
    L.append(macro("RSevGPaidMinn", f(cm.get("g_energy_weighted"), 2)))
    tab = {r["tout_c"]: r for r in an.get("L1_L2_table_T294", [])}
    for c, nm in ((0, "Zero"), (-20, "MinusTwenty"), (-40, "MinusForty")):
        r = tab.get(c, {})
        L.append(macro(f"RSevG{nm}", f(r.get("g"), 2)))
        L.append(macro(f"RSevGCold{nm}", f(r.get("g_at_zone_281K"), 2)))
        L.append(macro(f"RSevDgDTd{nm}", f(abs(r["dg_dTd_per_k"]) if r else None, 3)))
    zp = an.get("zone_params", {})
    t = zp.get("tau_h_p10_p50_p90") or [None] * 3
    C = zp.get("C_kwh_per_k_p10_p50_p90") or [None] * 3
    L += [macro("RSevNZones", zp.get("n", MISSING)), macro("RSevTauMed", f(t[1], 0)), macro("RSevTauLo", f(t[0], 0)),
          macro("RSevTauHi", f(t[2], 0)), macro("RSevCMed", f(C[1], 2)),
          macro("RSevRateSlope", f(abs(zp["recovery_rate_slope_kph_per_k_median"]) if zp else None, 2))]
    l4 = an.get("L4_start", {})
    L += [macro("RSevRTwo", f(l4.get("model_r2_median"), 2)),
          macro("RSevRecErr", f(l4.get("model_recovery_rel_err_median"), 0, pct=True)),
          macro("RSevNRec", f"{l4['n_recoveries']:,}" if l4.get("n_recoveries") else MISSING),
          macro("RSevRecDur", f(l4.get("recovery_dur_h_mean"), 2)),
          macro("RSevHoldH", f(l4.get("hold_h_mean"), 2)),
          macro("RSevHoldGas", f(l4.get("hold_gas_share_of_all_gas"), 1, pct=True))]
    pr = an.get("predictions_7d", {})
    sh = [v["share_periods_floor_reached"] for v in pr.values()]
    L += [macro("RSevBindLo", f(min(sh), 0, pct=True) if sh else MISSING),
          macro("RSevBindHi", f(max(sh), 0, pct=True) if sh else MISSING)]
    ck = load(R7 / "checks_r7.json") or {}
    for scen, nm in (("building_train_8/fairbanks_c2", "Eight"), ("building_train_7/denver_c1", "Seven"),
                     ("building_train_1/fairbanks_c2", "One")):
        row = ck.get(scen, {})
        for v, vn in (("r7chk_nle12", "Nle"), ("r7chk_nle14", "NleF"), ("r7chk_ls115", "Ls"), ("r7chk_ls100", "LsO")):
            r = row.get(v, {})
            L.append(macro(f"RSevChk{nm}{vn}Meas", f(r.get("meas_rel_gas"), 1, pct=True, signed=True)))
            L.append(macro(f"RSevChk{nm}{vn}Pred", f(r.get("pred_rel_gas"), 1, pct=True, signed=True)))
            L.append(macro(f"RSevChk{nm}{vn}Loss", f(r.get("meas_rel_loss"), 1, pct=True, signed=True)))
    return L


def screen_macros():
    sc = (load(R7 / "screen_summary.json") or {}).get("cands", {})
    L = []
    for c, tg in TAG.items():
        v = sc.get(c) or {}
        for s, sn in (("HS", "Hs"), ("P", "Pub")):
            r = v.get(s) or {}
            L.append(macro(f"RSevScr{tg}{sn}Rel", f(r.get("rel"), 1, pct=True, signed=True)))
            L.append(macro(f"RSevScr{tg}{sn}Lo", f(r.get("rel_ci_lo"), 1, pct=True, signed=True)))
            L.append(macro(f"RSevScr{tg}{sn}Hi", f(r.get("rel_ci_hi"), 1, pct=True, signed=True)))
            L.append(macro(f"RSevScr{tg}{sn}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
            L.append(macro(f"RSevScr{tg}{sn}RelAbs", pabs(r.get("rel"))))
        L.append(macro(f"RSevScr{tg}Class", v.get("class", MISSING)))
    # post-hoc ledger variant (not eligible): r7L_mbr2 = base + model start capped at the learned-rate lead (v10b)
    try:
        import compare_r6 as c6
        import compare_r7 as c7
        for s_, sn in (("r6hs", "Hs"), ("pub30", "Pub")):
            r = c6.paired(c7.ref(s_), c7.runs("r7L_mbr2", s_))
            full = bool(r) and r["n"] == (18 if s_ == "r6hs" else 30)
            L.append(macro(f"RSevLedger{sn}Rel", f(r["rel"], 1, pct=True, signed=True) if full else MISSING))
            L.append(macro(f"RSevLedger{sn}Lo", f(r["rel_ci_lo"], 1, pct=True, signed=True) if full else MISSING))
            L.append(macro(f"RSevLedger{sn}Hi", f(r["rel_ci_hi"], 1, pct=True, signed=True) if full else MISSING))
        rb = c6.paired(c7.runs("r7_base", "r6hs"), c7.runs("r7_mbf", "r6hs"))
        L.append(macro("RSevMbfVsBaseHsRel", f(rb["rel"], 2, pct=True, signed=True) if rb and rb["n"] == 18 else MISSING))
        L.append(macro("RSevMbfVsBaseHsLo", f(rb["rel_ci_lo"], 2, pct=True, signed=True) if rb and rb["n"] == 18 else MISSING))
        L.append(macro("RSevMbfVsBaseHsHi", f(rb["rel_ci_hi"], 2, pct=True, signed=True) if rb and rb["n"] == 18 else MISSING))
        # model-based start on HS: best / worst single scenario against v9 and the win count
        rm = c6.paired(c7.ref("r6hs"), c7.runs("r7_mbr", "r6hs"))
        if rm and rm["n"] == 18:
            rel = {k: v["cand"] / v["ref"] - 1 for k, v in rm["per_scenario"].items()}
            kb, kw = min(rel, key=rel.get), max(rel, key=rel.get)
            L.append(macro("RSevMbrHsBestRel", f(rel[kb], 1, pct=True, signed=True)))
            L.append(macro("RSevMbrHsBestScen", kb.replace("_", "\\_")))
            L.append(macro("RSevMbrHsWorstRel", f(rel[kw], 1, pct=True, signed=True)))
            L.append(macro("RSevMbrHsWorstScen", kw.replace("_", "\\_")))
            L.append(macro("RSevMbrHsWins", f"{rm['wins']}/{rm['n']}"))
        else:
            L += [macro(n, MISSING) for n in ("RSevMbrHsBestRel", "RSevMbrHsBestScen", "RSevMbrHsWorstRel",
                                              "RSevMbrHsWorstScen", "RSevMbrHsWins")]
        hc2 = c7.ref("r7hc")
        L.append(macro("RSevVNineHCTwo", f(sum(hc2.values()) / len(hc2), 5) if len(hc2) == 44 else MISSING))
    except Exception as e:  # noqa: BLE001
        print("ledger macros:", e)
    dec = load(R7 / "decision.json") or {}
    ch = dec.get("chosen")
    L.append(macro("RSevChosen", NAMES.get(ch, "none") if dec else MISSING))
    L.append(macro("RSevChosenId", ch.replace("_", "\\_") if ch else ("none" if dec else MISSING)))
    c = load(R7 / f"confirm_{ch}.json") if ch else None
    for s, sn in (("P", "Pub"), ("HC2", "HarshCTwo"), ("HS", "HarshS"), ("HC", "HarshC"), ("M", "Minn"),
                  ("FD", "FreshDef")):
        r = ((c or {}).get("sets") or {}).get(s) or {}
        L.append(macro(f"RSevConf{sn}N", r.get("n", MISSING)))
        L.append(macro(f"RSevConf{sn}Rel", f(r.get("rel"), 1, pct=True, signed=True)))
        L.append(macro(f"RSevConf{sn}RelLo", f(r.get("rel_ci_lo"), 1, pct=True, signed=True)))
        L.append(macro(f"RSevConf{sn}RelHi", f(r.get("rel_ci_hi"), 1, pct=True, signed=True)))
        L.append(macro(f"RSevConf{sn}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
    rule = (c or {}).get("rule") or {}
    L.append(macro("RSevRuleMet", {True: "met", False: "not met"}.get(rule.get("met"), MISSING)))
    s7 = load(R7 / "sets_r7.json") or {}
    L.append(macro("RSevHCTwoN", len(s7.get("r7hc", [])) or MISSING))
    fb = load(RES / "kaggle_feedback.json") or {}
    L.append(macro("RSevKagVNine", f((fb.get("scores_by_policy") or {}).get("v9_r6_comp"), 5)))
    return L


def write_round7_table() -> None:
    sc = (load(R7 / "screen_summary.json") or {}).get("cands", {})

    def cell(r):
        if not r:
            return "--"
        return (f"{100 * r['rel']:+.2f}\\% [{100 * r['rel_ci_lo']:+.2f}, {100 * r['rel_ci_hi']:+.2f}] "
                f"{r['wins']}/{r['n']}")
    rows = [f"{c.replace('_', '{\\_}')} & {NAMES[c]} & {cell(v.get('HS'))} & {cell(v.get('P'))} & {v.get('class', '--')} \\\\"
            for c, v in sc.items()]
    # post-hoc ledger row (not eligible this round): r7L_mbr2 = base + model start that may only shorten the learned lead
    try:
        import compare_r6 as c6
        import compare_r7 as c7
        hs = c6.paired(c7.ref("r6hs"), c7.runs("r7L_mbr2", "r6hs"))
        pu = c6.paired(c7.ref("pub30"), c7.runs("r7L_mbr2", "pub30"))
        if hs and pu and hs["n"] == 18 and pu["n"] == 30:
            rows.append("\\midrule\nr7L{\\_}mbr2$^\\dagger$ & base + model start, may only shorten the learned lead & "
                        f"{cell(hs)} & {cell(pu)} & ({c6.classify(hs, pu)}) \\\\")
    except Exception as e:  # noqa: BLE001
        print("ledger row:", e)
    body = "\n".join(rows) if rows else "\\multicolumn{5}{c}{\\textbf{??}} \\\\"
    tex = ("\\begin{table}[h]\n\\caption{Round-7 screen (8,640 steps): relative change of the mean against v9 with the "
           "paired-bootstrap 95\\% CI (5,000 resamples, seed 0) and wins, on the harsh screening set HS (18) and the "
           "public 30; classes as pre-registered (the same for bootstrap seeds 0--9). No candidate helps, so none was "
           "confirmed and v9 stays. $^\\dagger$Post hoc, after the first r7\\_mb shard (ledger only, not eligible).}\n"
           "\\label{tab:candidates_r7}\n\\centering\\scriptsize\n\\setlength{\\tabcolsep}{3pt}\n"
           "\\begin{tabular}{p{1.3cm}p{4.2cm}ccl}\n"
           "\\toprule\nid & change & HS & public-30 & class \\\\\n\\midrule\n" + body
           + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    (PAPER / "tuning_tables_r7.tex").write_text(tex, encoding="utf-8")


def round7_macros():
    return analysis_macros() + screen_macros()


if __name__ == "__main__":
    ls = round7_macros()
    write_round7_table()
    print("".join(ls))
    print(sum(1 for x in ls if MISSING in x), "missing of", len(ls))
