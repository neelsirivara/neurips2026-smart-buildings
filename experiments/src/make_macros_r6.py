"""Round-6 macros and tables (called from make_macros.py).

Inputs (missing -> \\textbf{??}):
  results/round6/kaggle_registry.json, kaggle_repro.json, kaggle_out/t01/{env,git_check}.json   (Kaggle compute)
  results/round6/set_match.json            harsh sets vs Kaggle (compare_r6.py match)
  results/round6/decomp_v8_r6hs.json       v8 loss decomposition on HS (decompose_r6.py)
  results/round6/recovery_fit_v8_r6hs.json recovery rate vs lift (fit_recovery_r6.py)
  results/round6/screen_summary.json       screen vs v8 (compare_r6.py screen)
  results/round6/decision.json             choice under the pre-registered rule (decide_r6 in compare_r6.py)
  results/round6/confirm_<cand>.json       full-length confirmation (compare_r6.py confirm)
  results/kaggle_feedback.json             Kaggle public scores
"""
from __future__ import annotations

import json
import re
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
R6 = RES / "round6"
PAPER = ROOT / "paper"
MISSING = r"\textbf{??}"
SETS = {"P": "Pub", "M": "Minn", "P+M": "PubMinn", "HC": "HarshC", "HS": "HarshS", "H": "Harsh", "P+HC": "PubHarshC",
        "P+H": "PubHarsh", "P+M+H": "PubMinnHarsh"}
POL = {"v7": "VSeven", "v6": "VSix", "v5": "VFive", "pid_water": "Pid"}
SHORT = {
    "r6_c00_v8": "v8 (reference; v9 code, switches off)",
    "r6_c01_boost8": "boost set-back zones' forced air, 8\\,h before start",
    "r6_c02_boost4": "same, 4\\,h before start",
    "r6_c03_sync08": "join a burst on the handler within 0.8\\,K of the floor",
    "r6_c09_bfloor2": "boost forced air within 2\\,K of the floor",
    "r6_c06_mpre05": "preconditioning target 0.5\\,K inside the band",
    "r6_c07_safe115": "lead safety 1.15",
    "r6_c08_night10": "weeknight setback 10\\,K",
    "r6_c10_frost5": "frost floor 5$^\\circ$C (sensible practice)",
    "r6_c11_boost8cold": "c01 only while outside air $\\le$ setback floor$^\\dagger$",
    "r6_comp": "composite c11 + c09 + c06 + c08 (v9)",
    "r6_compb": "c11 + c09 + c07 + c08 (post hoc, ledger only)$^\\ddagger$",
}


def short(k: str) -> str:
    return SHORT.get(k, k.replace("_", "\\_"))


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


def pct_abs(x, nd=1):
    return MISSING if x is None else f"{abs(100 * x):.{nd}f}\\%"


def compute_macros():
    L = []
    env = load(R6 / "kaggle_out" / "t01" / "env.json") or {}
    gc = load(R6 / "kaggle_out" / "t01" / "git_check.json") or {}
    rp = load(R6 / "kaggle_repro.json") or {}
    reg = load(R6 / "kaggle_registry.json") or {}
    L.append(macro("RSixKagCpu", env.get("cpu_count", MISSING)))
    L.append(macro("RSixKagRamGb", f(env.get("mem_total_gb"), 0)))
    L.append(macro("RSixKagSlots", 5))
    L.append(macro("RSixKagInternet", "no" if gc.get("clone_rc", 0) != 0 else "yes"))
    L.append(macro("RSixReproN", len(rp) if rp else MISSING))
    L.append(macro("RSixReproIdentical", sum(1 for v in rp.values() if v.get("identical")) if rp else MISSING))
    ks = reg.get("kernels", {})
    n_k = sum(1 for k in ks.values() if k.get("state") == "fetched")
    n_runs = sum(int(k.get("n_summaries") or 0) for k in ks.values() if k.get("state") == "fetched")
    L.append(macro("RSixNKernels", n_k))
    L.append(macro("RSixNRuns", n_runs))
    mr = load(R6 / "mac_repro.json") or {}
    L.append(macro("RSixMacReproN", len(mr) if mr else MISSING))
    mx = max((abs(v["rel_diff"]) for v in mr.values()), default=None)
    L.append(macro("RSixMacReproMaxRel", MISSING if mx is None else
                   ("0" if mx == 0 else f"$10^{{{math.ceil(math.log10(mx))}}}$")))   # bound: |rel diff| < 10^k
    mreg = load(R6 / "mac_registry.json") or {}
    L.append(macro("RSixMacNRuns", sum(int(v.get("n_summaries_merged") or 0) for v in mreg.values())
                   - len(mr) if mreg else MISSING))
    return L


def decomp_macros():
    L = []
    d = load(R6 / "decomp_v8_r6hs.json")
    if not d:
        return [macro(n, MISSING) for n in ("RSixDecGas", "RSixDecComfort", "RSixDecOccWd", "RSixDecPreWd", "RSixDecPreWe",
                                            "RSixDecSbWe", "RSixDecVent", "RSixDecVentHeated", "RSixDecVentIdle",
                                            "RSixDecColdestWe", "RSixDecBelowFive", "RSixDecN", "RSixDecMetric",
                                            "RSixDecHourFive", "RSixDecHourSix")]
    o = d["overall"]
    g = o["sums"]["gas_j"]
    md = o["gas_j_by_mode_daytype"]
    L += [macro("RSixDecN", d["n"]), macro("RSixDecMetric", f(o["metric"])),
          macro("RSixDecGas", f(o["shares"]["gas"], pct=True)), macro("RSixDecComfort", f(o["shares"]["comfort"], pct=True)),
          macro("RSixDecOccWd", f(md["0_wd"] / g, pct=True)), macro("RSixDecPreWd", f(md["1_wd"] / g, pct=True)),
          macro("RSixDecPreWe", f(md["1_we"] / g, pct=True)), macro("RSixDecSbWe", f(md["2_we"] / g, pct=True)),
          macro("RSixDecVent", f(o["sums"]["vent_j_total"] / g, 2)),
          macro("RSixDecVentHeated", f(o["sums"]["vent_j_heated_zones"] / g, 2)),
          macro("RSixDecVentIdle", f(o["sums"]["vent_j_idle_zones"] / g, 2)),
          macro("RSixDecColdestWe", f(o["min_zone_t_weekend"] - 273.15, 1)),
          macro("RSixDecBelowFive", f(sum(r["zone_steps_below_278k"] for r in d["per_scenario"].values())
                                      / len(d["per_scenario"]), pct=True)),
          macro("RSixDecHourFive", f(o["gas_j_by_hour"][5] / g, pct=True)),
          macro("RSixDecHourSix", f(o["gas_j_by_hour"][6] / g, pct=True))]
    rf = load(R6 / "recovery_fit_v8_r6hs.json") or {}
    L.append(macro("RSixRecSlope", f(rf.get("within_zone_slope_kph_per_k"), 3, signed=True)))
    ci = rf.get("slope_ci95") or [None, None]
    L.append(macro("RSixRecSlopeLo", f(ci[0], 3, signed=True)))
    L.append(macro("RSixRecSlopeHi", f(ci[1], 3, signed=True)))
    L.append(macro("RSixRecN", rf.get("n_recoveries", MISSING)))
    return L


def match_macros():
    m = load(R6 / "set_match.json") or {}
    L = []
    sets = m.get("sets", {})
    for s, nm in SETS.items():
        r = sets.get(s, {})
        L.append(macro(f"RSix{nm}N", r.get("n_v8", MISSING)))
        L.append(macro(f"RSix{nm}VEight", f(r.get("L_v8"))))
        L.append(macro(f"RSix{nm}Level", f(r.get("level"), 2)))
        L.append(macro(f"RSix{nm}ShapeErr", f(r.get("shape_err"), 3)))
        for p, pn in POL.items():
            q = (r.get("ratios") or {}).get(p, {})
            L.append(macro(f"RSix{nm}Ratio{pn}", f(q.get("set"), 2 if p == "pid_water" else 3)))
            L.append(macro(f"RSix{nm}Ratio{pn}N", q.get("n", MISSING)))
    kr = m.get("kaggle_ratio_vs_v8", {})
    for p, pn in POL.items():
        L.append(macro(f"RSixKagRatio{pn}", f(kr.get(p), 2 if p == "pid_water" else 3)))
    mx = m.get("mixture_P_HC", {})
    L.append(macro("RSixMixW", f(mx.get("w_HC"), 2)))
    L.append(macro("RSixMixWPct", MISSING if mx.get("w_HC") is None else f"{100 * mx['w_HC']:.0f}\\%"))
    L.append(macro("RSixMixPid", f(mx.get("implied_pid_over_v8"), 2)))
    st = m.get("v8_by_station", {})
    for k, nm in (("fairbanks", "Fairbanks"), ("fairbanks_cold", "FairbanksCold"), ("minneapolis", "Minneapolis"),
                  ("minneapolis_cold", "MinneapolisCold"), ("denver", "Denver"), ("denver_cold", "DenverCold")):
        L.append(macro(f"RSixStation{nm}", f((st.get(k) or {}).get("mean"))))
    return L


NUMW = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
        "Thirteen", "Fourteen", "Fifteen"]


def cand_tag(k: str) -> str:
    """r6_c01_boost8 -> COne; r6_comp_x -> Comp."""
    tok = k.split("_")[1] if "_" in k else k
    if tok.startswith("c") and tok[1:].isdigit():
        return "C" + NUMW[int(tok[1:])]
    return "Comp" if tok == "comp" else "Comp" + tok[4:].upper()


def screen_macros():
    sc = load(R6 / "screen_summary.json") or {}
    L = []
    cands = sc.get("cands", {})
    cls = [v.get("class") for k, v in cands.items() if k != "r6_c00_v8"]
    L.append(macro("RSixNSingles", sum(1 for k in cands if k not in ("r6_c00_v8",) and "comp" not in k)))
    for c in ("helps", "n.s.", "worse", "public only"):
        nm = {"helps": "Helps", "n.s.": "Ns", "worse": "Worse", "public only": "PubOnly"}[c]
        L.append(macro(f"RSixN{nm}", sum(1 for k, v in cands.items() if k != "r6_c00_v8" and "comp" not in k
                                         and v.get("class") == c)))
    for k, v in cands.items():
        tag = cand_tag(k)
        hs, pub = v.get("HS") or {}, v.get("pub12") or {}
        L.append(macro(f"RSixScr{tag}HsRel", f(hs.get("rel"), pct=True, signed=True)))
        L.append(macro(f"RSixScr{tag}HsRelAbs", pct_abs(hs.get("rel"))))
        L.append(macro(f"RSixScr{tag}HsLoAbs", pct_abs(hs.get("rel_ci_lo"))))
        L.append(macro(f"RSixScr{tag}HsHiAbs", pct_abs(hs.get("rel_ci_hi"))))
        L.append(macro(f"RSixScr{tag}PubRelAbs", pct_abs(pub.get("rel"))))
        L.append(macro(f"RSixScr{tag}HsLo", f(hs.get("rel_ci_lo"), pct=True, signed=True)))
        L.append(macro(f"RSixScr{tag}HsHi", f(hs.get("rel_ci_hi"), pct=True, signed=True)))
        L.append(macro(f"RSixScr{tag}PubRel", f(pub.get("rel"), pct=True, signed=True)))
        L.append(macro(f"RSixScr{tag}PubLo", f(pub.get("rel_ci_lo"), pct=True, signed=True)))
        L.append(macro(f"RSixScr{tag}PubHi", f(pub.get("rel_ci_hi"), pct=True, signed=True)))
    return L


def confirm_macros():
    dec = load(R6 / "decision.json") or {}
    cand = dec.get("chosen")
    L = [macro("RSixChosen", SHORT.get(cand, cand or "none").replace("_", "\\_") if cand else "none")]
    c = load(R6 / f"confirm_{cand}.json") if cand else None
    for s, nm in (("pub30", "Pub"), ("HC", "HarshC"), ("HS", "HarshS"), ("H", "Harsh"), ("M", "Minn"),
                  ("P+M", "PubMinn"), ("FD", "FreshDef")):
        r = ((c or {}).get("sets") or {}).get(s) or {}
        L.append(macro(f"RSixConf{nm}N", r.get("n", MISSING)))
        L.append(macro(f"RSixConf{nm}Ref", f(r.get("ref"))))
        L.append(macro(f"RSixConf{nm}Cand", f(r.get("cand"))))
        L.append(macro(f"RSixConf{nm}Rel", f(r.get("rel"), pct=True, signed=True)))
        L.append(macro(f"RSixConf{nm}RelLo", f(r.get("rel_ci_lo"), pct=True, signed=True)))
        L.append(macro(f"RSixConf{nm}RelHi", f(r.get("rel_ci_hi"), pct=True, signed=True)))
        L.append(macro(f"RSixConf{nm}Wins", f"{r['wins']}/{r['n']}" if r else MISSING))
        L.append(macro(f"RSixConf{nm}RelAbs", pct_abs(r.get("rel"))))
        L.append(macro(f"RSixConf{nm}RelLoAbs", pct_abs(r.get("rel_ci_lo"))))
        L.append(macro(f"RSixConf{nm}RelHiAbs", pct_abs(r.get("rel_ci_hi"))))
        L.append(macro(f"RSixConf{nm}WorstRel", f(r.get("worst_rel"), pct=True, signed=True)))
        L.append(macro(f"RSixConf{nm}Worst", r["worst"].replace("_", "\\_") if r.get("worst") else MISSING))
    # comfort share of the change on FD: (comfort delta) / (total delta), from the summaries' reward components
    fd = (((c or {}).get("sets") or {}).get("FD") or {}).get("per_scenario") or {}
    dc = dt = 0.0
    for k in fd:
        b, w = k.split("/")
        cand_f = RES / "round6" / "runs" / cand / "r4c" / b / w / "transfer" / "summary.json"
        ref_f = next((d / b / w / "transfer" / "summary.json" for d in (RES / "round6" / "runs" / "v8" / "r4c",
                      RES / "round5" / "full" / "r5_c12_comp" / "r4c")
                      if (d / b / w / "transfer" / "summary.json").exists()), None)
        if not (cand_f.exists() and ref_f):
            continue
        sc, sr = load(cand_f), load(ref_f)
        comp = lambda s: -s["productivity_weight"] * s["total_normalized_productivity_regret"] / 8640  # noqa: E731
        dc += comp(sc) - comp(sr)
        dt += (abs(sc["total_reward"]) - abs(sr["total_reward"])) / 8640
    L.append(macro("RSixConfFreshDefComfortShare", f"{100 * dc / dt:.0f}\\%" if dt else MISSING))
    ps = (((c or {}).get("sets") or {}).get("pub30") or {}).get("per_scenario") or {}
    for st in ("Fairbanks", "Denver", "Atlanta", "Phoenix", "Singapore"):
        v = [x["cand"] for k, x in ps.items() if k.split("/")[1].startswith(st.lower())]
        L.append(macro(f"RSixConfPubCand{st}", f(sum(v) / len(v)) if v else MISSING))
    rule = (c or {}).get("rule") or {}
    L.append(macro("RSixRuleMet", {True: "met", False: "not met"}.get(rule.get("met"), MISSING)))
    seeds = (c or {}).get("seed_ci") or {}
    hc, pb = seeds.get("HC"), seeds.get("pub30")
    L.append(macro("RSixSeedsHarshCBelow", sum(1 for lo, hi in hc if hi < 0) if hc else MISSING))
    L.append(macro("RSixSeedsPubAbove", sum(1 for lo, hi in pb if lo > 0) if pb else MISSING))
    # post-hoc ledger composite r6_compb (c07 instead of c06) on the full public 30, against v8
    try:
        import compare_r6 as c6
        rb = c6.paired(c6.ref_v8("pub30"), c6.runs("r6_compb", "pub30"))
    except Exception:  # noqa: BLE001
        rb = None
    ok = bool(rb and rb["n"] == 30)
    L.append(macro("RSixCompBPubRel", f(rb["rel"], pct=True, signed=True) if ok else MISSING))
    L.append(macro("RSixCompBPubRelLo", f(rb["rel_ci_lo"], pct=True, signed=True) if ok else MISSING))
    L.append(macro("RSixCompBPubRelHi", f(rb["rel_ci_hi"], pct=True, signed=True) if ok else MISSING))
    dc = load(R6 / "decision_composite.json") or {}
    mem = dc.get("composite_members") or {}
    L.append(macro("RSixCompMembers", ", ".join(v.split("_")[1] for v in mem.values()) if mem
                   else MISSING))
    return L


def kaggle_macros():
    fb = load(RES / "kaggle_feedback.json") or {}
    sc = fb.get("scores_by_policy", {})
    L = []
    r6 = [s for s in fb.get("submissions", []) if s.get("round") == 6]
    L.append(macro("RSixNProbes", len(r6)))
    for i, s in enumerate(r6[:6]):
        nm = "ABCDEF"[i]
        L.append(macro(f"RSixProbe{nm}Label", s.get("label", MISSING).replace("_", "\\_")))
        L.append(macro(f"RSixProbe{nm}Score", f(s.get("public_score")) if s.get("public_score") else "pending"))
    L.append(macro("RSixKagVEight", f(sc.get("v8_r5_c12_comp"))))
    return L


def write_round6_table() -> None:
    """Appendix ledger of the round-6 screen."""
    sc = load(R6 / "screen_summary.json") or {}
    rows = []
    for k, v in (sc.get("cands") or {}).items():
        hs, pub = v.get("HS") or {}, v.get("pub12") or {}

        def cell(r):
            if not r:
                return "--"
            return f"{100 * r['rel']:+.1f}\\% [{100 * r['rel_ci_lo']:+.1f}, {100 * r['rel_ci_hi']:+.1f}]"
        rows.append(f"{re.sub(r'^r6_(c\d\d|compb?)(_.*)?$', r'\1', k)} & {short(k)} & {cell(hs)} & {cell(pub)} & {v.get('class', '--')} \\\\")
    body = "\n".join(rows) if rows else "\\multicolumn{5}{c}{\\textbf{??}} \\\\"
    tex = ("\\begin{table}[h]\n\\caption{Round-6 screen (8,640 steps; relative change of the mean against v8, paired "
           "bootstrap 95\\% CI, 5,000 resamples, seed 0) on the harsh screening set HS (18) and twelve public scenarios. "
           "Classes as pre-registered (helps = HS CI below zero and public CI not above zero); $^\\dagger$ added after a "
           "first look at c01's screen (post hoc, labelled in \\texttt{PREREG.md}); $^\\ddagger$ defined after reading the public "
           "part of v9's confirmation, so not eligible this round (its HS column may cover part of HS).}\n"
           "\\label{tab:candidates_r6}\n\\centering\\scriptsize\n\\begin{tabular}{llccl}\n\\toprule\n"
           "id & change & HS & public-12 & class \\\\\n\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    (PAPER / "tuning_tables_r6.tex").write_text(tex, encoding="utf-8")


def write_round6_kaggle_table() -> None:
    """Main-text table: Kaggle public scores against the local sets incl. the round-6 harsh sets (v8 reference)."""
    m = load(R6 / "set_match.json") or {}
    kr = m.get("kaggle_ratio_vs_v8", {})
    rows = [("Kaggle public LB (about 10 hidden scenarios)", None),
            ("P: public 30 (shipped six, 5 stations)", "P"),
            (r"M: shipped six $\times$ Minneapolis (12, round 5)", "M"),
            ("P+M (42)", "P+M"),
            ("HC: harsh confirmation set (48)", "HC"),
            ("HS: harsh screening set (18)", "HS"),
            ("MIX", "MIX")]

    def cell(x, nd):
        return "--" if x is None else f"{x:.{nd}f}"

    L = [r"\begin{table}[t]" + "\n"
         + r"\caption{Which local set predicts Kaggle? Leaderboard metric of v8 and the ratio of each other policy to v8 "
         r"on the same scenarios, against the Kaggle public scores of the same policy files. $E$ = mean over the "
         r"policies run on the set of $|\ln r_{\text{set}} - \ln r_{\text{Kaggle}}|$ (pre-registered shape error; "
         r"smaller matches better). HC and HS: the shipped six under the Minneapolis strips not used before, the "
         r"coldest Fairbanks and Denver strips and new 30-day strips cut from the coldest months of the shipped weather "
         r"files. A superscript is the number of scenarios when a ratio covers only part of the set; the mixture's weight is fitted to v8's Kaggle score, its \texttt{pid\_water} ratio is a prediction (HC part on the superscripted scenarios).}" + "\n"
         + r"\label{tab:kaggle}" + "\n" + r"\centering\scriptsize" + "\n"
         + r"\setlength{\tabcolsep}{3.5pt}" + "\n" + r"\begin{tabular}{lrrrrrrr}" + "\n" + r"\toprule" + "\n"
         + r"set & v8 & v8 / Kaggle & v7 / v8 & v6 / v8 & v5 / v8 & \texttt{pid\_water} / v8 & $E$ \\" + "\n"
         + r"\midrule" + "\n"]
    for label, key in rows:
        if key is None:
            L.append(f"{label} & {cell(m.get('kaggle', {}).get('v8'), 5)} & 1 & {cell(kr.get('v7'), 3)} & "
                     f"{cell(kr.get('v6'), 3)} & {cell(kr.get('v5'), 3)} & {cell(kr.get('pid_water'), 2)} & -- "
                     + "\\\\\n\\midrule\n")
            continue
        if key == "MIX":
            mx = m.get("mixture_P_HC") or {}
            if mx:
                w = mx["w_HC"]
                L.append(f"mixture {100 * w:.0f}\\% HC + {100 * (1 - w):.0f}\\% P & "
                         f"{cell(m.get('kaggle', {}).get('v8'), 5)} & 1 (fitted) & -- & -- & -- & "
                         f"{cell(mx.get('implied_pid_over_v8'), 2)}$^{{{mx.get('pid_n_HC')}}}$ & -- " + "\\\\\n")
            continue
        r = (m.get("sets") or {}).get(key, {})
        rat = r.get("ratios", {})
        nv8 = r.get("n_v8")

        def rc(p, nd):
            q = rat.get(p) or {}
            if q.get("set") is None:
                return "--"
            sub = "" if q.get("n") == nv8 else f"$^{{{q.get('n')}}}$"   # ratio on a subset: n as superscript
            return f"{q['set']:.{nd}f}{sub}"
        L.append(f"{label} & {cell(r.get('L_v8'), 5)} & {cell(r.get('level'), 2)} & "
                 f"{rc('v7', 3)} & {rc('v6', 3)} & {rc('v5', 3)} & {rc('pid_water', 2)} & "
                 f"{cell(r.get('shape_err'), 3)} " + "\\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    (PAPER / "round6_kaggle_table.tex").write_text("".join(L), encoding="utf-8")


def round6_macros():
    L = []
    for fn in (compute_macros, decomp_macros, match_macros, screen_macros, confirm_macros, kaggle_macros):
        L += fn()
    return L


if __name__ == "__main__":
    lines = round6_macros()
    write_round6_table()
    write_round6_kaggle_table()
    write_round6_kaggle_table()
    print("".join(lines))
    print(sum(1 for x in lines if MISSING in x), "missing of", len(lines))
