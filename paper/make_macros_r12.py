"""Rounds 12-13 macros and tables for the paper (CMA-ES tuning of v12's constants; frost guard; v13), and their rows
in paper/AUDIT.md.

Same pattern as make_macros_r11.py: every number is read or computed from a result file; a missing input prints
\\textbf{??}. The v13 Kaggle score prints "pending" until kaggle_feedback.json has an entry labelled "v13_r12var";
rerun this script once it lands.

Writes  paper/results_macros_r12.tex   (\\input after results_macros_r11.tex)
        paper/table_tuning_r12.tex      (sensitivity table: v12, r12cand, r13cand, v13 = r12var)
        paper/table_params_r12.tex      (appendix: the 14 tuned constants for each controller, with bounds)
        paper/AUDIT.md                  (replaces the block between the r12 markers, or appends it)
Reads   experiments/results/round12/{PLAN.md,PLAN.sha256,cma_state.json,candidate_mean.json,
        candidate_v12setback.json,decision.json,decision_r12var.json,frost.json,frost_r12var.json},
        experiments/results/round13/{PLAN.md,PLAN.sha256,cma_state.json,candidate_mean.json,decision.json,frost.json,
        choice.json}, experiments/results/tune/best_params_v12.json, experiments/results/kaggle_feedback.json

    python paper/make_macros_r12.py
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
RES = ROOT / "experiments" / "results"
R12 = RES / "round12"
R13 = RES / "round13"
OUT = PAPER / "results_macros_r12.tex"
TAB = PAPER / "table_tuning_r12.tex"
PTAB = PAPER / "table_params_r12.tex"
AUDIT = PAPER / "AUDIT.md"
BEGIN, END = "<!-- r12 begin -->", "<!-- r12 end -->"
MISSING = r"\textbf{??}"
PENDING = "pending"
KAG_LABEL = "v13_r12var"

MACROS: dict[str, str] = {}
SOURCES: dict[str, str] = {}
CHECKS: list[tuple[str, bool | None, str]] = []


def put(name: str, val, src: str) -> None:
    assert name not in MACROS, name
    assert re.fullmatch(r"[A-Za-z]+", name), name
    MACROS[name] = MISSING if val is None else str(val)
    SOURCES[name] = src


def check(label: str, cond, detail: str = "") -> None:
    CHECKS.append((label, None if cond is None else bool(cond), detail))


def ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def spct(x, nd=2):
    """Signed percentage with a math minus/plus (x is a fraction)."""
    if not ok(x):
        return None
    s = f"{abs(100 * x):.{nd}f}"
    sign = "$-$" if (x < 0 and float(s) != 0.0) else "$+$"
    return f"{sign}{s}\\%"


def pabs(x, nd=2):
    return f"{abs(100 * x):.{nd}f}\\%" if ok(x) else None


def pct(x, nd=2):
    return f"{100 * x:.{nd}f}\\%" if ok(x) else None


def degc(x, nd=1):
    if not ok(x):
        return None
    s = f"{abs(x):.{nd}f}"
    return ("$-$" if x < 0 and float(s) != 0.0 else "") + s


def fnum(x, nd):
    return f"{x:.{nd}f}" if ok(x) else None


# parameter display: (key, label in the table, decimals)
PARAMS = [
    ("night_low_ext", r"weeknight setback, floor (K)", 1),
    ("night_high_ext", r"weeknight setback, ceiling (K)", 1),
    ("wk_ext_lo", r"weekend setback, floor (K)", 1),
    ("sb_boost_floor_k", r"near-floor boost band (K)", 2),
    ("sb_boost_h", r"set-back air boost window (h)", 1),
    ("lead_safety", r"lead safety", 2),
    ("lead_base_h", r"base lead $\ell_0$ (h)", 2),
    ("margin_pre", r"precondition margin (K)", 2),
    ("margin_occ", r"occupied margin (K)", 2),
    ("q_sb_w", r"setback burst (W)", 0),
    ("kq_w_per_k", r"$k_q$ (W/K)", 0),
    ("ki_w_per_k_step", r"$k_i$ (W/K per step)", 0),
    ("valve_target", r"valve target", 2),
    ("sat_mix_floor", r"mixed-handler SAT floor (K)", 1),
]


def plan_bounds(plan: str) -> dict[str, tuple[float, float, float, str]]:
    out = {}
    for m in re.finditer(r"^\s*\|\s*([a-z_]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(\w+)\s*\|",
                         plan, re.M):
        out[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5))
    return out


def main() -> int:
    plan12 = (R12 / "PLAN.md").read_text(encoding="utf-8")
    plan13 = (R13 / "PLAN.md").read_text(encoding="utf-8")
    st12, st13 = load(R12 / "cma_state.json"), load(R13 / "cma_state.json")
    v12 = load(RES / "tune" / "best_params_v12.json") or {}
    cand = load(R12 / "candidate_mean.json") or {}
    var = load(R12 / "candidate_v12setback.json") or {}
    thr = load(R13 / "candidate_mean.json") or {}
    dec = {"Cand": load(R12 / "decision.json"), "Var": load(R12 / "decision_r12var.json"),
           "Thr": load(R13 / "decision.json")}
    frost = {"Cand": load(R12 / "frost.json"), "Var": load(R12 / "frost_r12var.json"), "Thr": load(R13 / "frost.json")}
    choice = load(R13 / "choice.json") or {}
    src = {"Cand": "round12/decision.json, round12/frost.json", "Var": "round12/decision_r12var.json, round12/frost_r12var.json",
           "Thr": "round13/decision.json, round13/frost.json"}

    # --- plan hashes
    for tag, d in (("12", R12), ("13", R13)):
        import hashlib
        h = hashlib.sha256((d / "PLAN.md").read_bytes()).hexdigest()
        rec = (d / "PLAN.sha256").read_text().split()[0] if (d / "PLAN.sha256").exists() else None
        check(f"round-{tag} PLAN.md matches PLAN.sha256", rec == h, f"{h[:12]} vs {str(rec)[:12]}")
        st = st12 if tag == "12" else st13
        check(f"round-{tag} cma_state plan_sha256 matches", st and st.get("plan_sha256") == h, "")

    # --- search setup (round 12)
    bounds = plan_bounds(plan12)
    check("round-12 PLAN lists 14 parameters", len(bounds) == len(PARAMS), str(len(bounds)))
    put("RTwNParams", len(st12["mean"]), "round12/cma_state.json len(mean)")
    put("RTwNParamsThr", len(st13["mean"]), "round13/cma_state.json len(mean)")
    put("RTwNFixedThr", len(st13.get("fixed", {})), "round13/cma_state.json fixed")
    put("RTwPop", len(st12["history"][0]["candidates"]), "round12/cma_state.json history[0].candidates")
    put("RTwGens", len(st12["history"]), "round12/cma_state.json len(history)")
    put("RTwGensThr", len(st13["history"]), "round13/cma_state.json len(history)")
    put("RTwSigmaZero", fnum(st12["history"][0]["sigma_before"], 2), "round12/cma_state.json history[0].sigma_before")
    put("RTwSigmaZeroThr", fnum(st13["history"][0]["sigma_before"], 2), "round13/cma_state.json history[0].sigma_before")
    nh, npub = len(st12["scenarios"]["harsh"]), len(st12["scenarios"]["public"])
    put("RTwNWin", nh + npub, "round12/cma_state.json scenarios")
    put("RTwNWinHarsh", nh, "round12/cma_state.json scenarios.harsh")
    put("RTwNWinPub", npub, "round12/cma_state.json scenarios.public")
    check("round-13 uses round 12's windows", st13["scenarios"] == st12["scenarios"], "")
    m = re.search(r"(\d+)-day windows \(([\d,]+) steps\)", plan12)
    put("RTwWinDays", m.group(1) if m else None, "round12/PLAN.md 'N-day windows'")
    put("RTwWinSteps", m.group(2).replace(",", "{,}") if m else None, "round12/PLAN.md '(N steps)'")
    m = re.search(r"at most (\d+) K deeper", plan12)
    put("RTwDepthMaxDeeper", m.group(1) if m else None, "round12/PLAN.md depth bound")
    med0 = st12["history"][0]["median"]
    medL = st12["history"][-1]["median"]
    put("RTwMedFirst", fnum(med0, 3), "round12/cma_state.json history[0].median (window objective, ratio to v12)")
    put("RTwMedLast", fnum(medL, 3), "round12/cma_state.json history[-1].median")
    put("RTwMedLastThr", fnum(st13["history"][-1]["median"], 3), "round13/cma_state.json history[-1].median")

    # --- confirmation results
    for k, d in dec.items():
        f = frost[k]
        if d is None or f is None:
            continue
        s = src[k]
        put(f"RTw{k}Mix", spct(d["mixture"]), s + " mixture")
        put(f"RTw{k}MixLo", spct(d["mixture_ci"][0]), s + " mixture_ci[0]")
        put(f"RTw{k}MixHi", spct(d["mixture_ci"][1]), s + " mixture_ci[1]")
        put(f"RTw{k}MixAbs", pabs(d["mixture"]), s + " |mixture| (a reduction; checked negative)")
        put(f"RTw{k}MixLoAbs", pabs(d["mixture_ci"][0]), s + " |mixture_ci[0]|")
        put(f"RTw{k}MixHiAbs", pabs(d["mixture_ci"][1]), s + " |mixture_ci[1]|")
        put(f"RTw{k}PubAbs", pabs(d["pub30"], 1), s + " |pub30|")
        check(f"{k}: mixture CI and pub30 negative (Abs macros read as reductions)",
              d["mixture_ci"][1] < 0 and d["pub30"] < 0, "")
        put(f"RTw{k}HCThree", spct(d["hc3"]), s + " hc3")
        put(f"RTw{k}HH", spct(d["hh"]), s + " hh")
        put(f"RTw{k}HCThreeWins", f"{d['hc3_wins']}/{d['n']['r10hc']}", s + " hc3_wins/n")
        put(f"RTw{k}HHWins", f"{d['hh_wins']}/{d['n']['r10hh']}", s + " hh_wins/n")
        put(f"RTw{k}Pub", spct(d["pub30"], 1), s + " pub30")
        put(f"RTw{k}PubWins", f"{d['pub30_wins']}/{d['n']['pub30']}", s + " pub30_wins/n")
        put(f"RTw{k}HS", spct(f["hs_loss_ratio"] - 1, 1), s + " hs_loss_ratio - 1")
        put(f"RTw{k}Coldest", degc(f["coldest_c_cand"]), s + " coldest_c_cand")
        put(f"RTw{k}BelowFive", pct(f["below5_cand"]), s + " below5_cand")
        check(f"{k}: primary pass = CI below 0", d["primary_pass"] == (d["mixture_ci"][1] < 0), "")
        check(f"{k}: guard pass = pub30 <= 0", d["guard_pass"] == (d["pub30"] <= 0), "")
        check(f"{k}: frost v12 reference identical across files",
              abs(f["coldest_c_v12"] - frost["Cand"]["coldest_c_v12"]) < 1e-9
              and abs(f["below5_v12"] - frost["Cand"]["below5_v12"]) < 1e-12, "")
    fv = frost["Cand"]
    put("RTwNHS", fv["n_cand"], "round12/frost.json n_cand")
    put("RTwVTwelveColdest", degc(fv["coldest_c_v12"]), "round12/frost.json coldest_c_v12")
    put("RTwVTwelveBelowFive", pct(fv["below5_v12"]), "round12/frost.json below5_v12")
    put("RTwCandColderK", fnum(fv["coldest_c_v12"] - fv["coldest_c_cand"], 1), "round12/frost.json v12 - cand coldest")
    put("RTwVarColderK", fnum(fv["coldest_c_v12"] - frost["Var"]["coldest_c_cand"], 1), "round12/frost_r12var.json v12 - cand coldest")
    put("RTwThrColderK", fnum(fv["coldest_c_v12"] - frost["Thr"]["coldest_c_cand"], 1), "round13/frost.json v12 - cand coldest")
    put("RTwCandBelowFiveRise", fnum(100 * (fv["below5_cand"] - fv["below5_v12"]), 2),
        "round12/frost.json (below5_cand - below5_v12) in pp")
    put("RTwThrBelowFiveRise", fnum(100 * (frost["Thr"]["below5_cand"] - fv["below5_v12"]), 2),
        "round13/frost.json (below5_cand - below5_v12) in pp")
    put("RTwVarMixShare", fnum(100 * dec["Var"]["mixture"] / dec["Cand"]["mixture"], 0),
        "decision_r12var.mixture / decision.mixture, in %")

    # --- frost guard (round 13 PLAN) and the mechanical choice
    mpp = re.search(r"v12's \+ ([\d.]+) percentage points", plan13)
    mk = re.search(r"v12's - ([\d.]+) C", plan13)
    pp = float(mpp.group(1)) if mpp else None
    dk = float(mk.group(1)) if mk else None
    put("RTwGuardPP", fnum(pp, 2) if pp is not None else None, "round13/PLAN.md Guard 2 (pp)")
    put("RTwGuardK", fnum(dk, 1) if dk is not None else None, "round13/PLAN.md Guard 2 (K)")
    lim5 = fv["below5_v12"] + pp / 100 if pp is not None else None
    limc = fv["coldest_c_v12"] - dk if dk is not None else None
    put("RTwGuardBelowFiveLim", pct(lim5), "below5_v12 + Guard 2 pp")
    put("RTwGuardColdestLim", degc(limc), "coldest_c_v12 - Guard 2 K")
    guard = {}
    for k in ("Cand", "Var", "Thr"):
        f = frost[k]
        guard[k] = f["below5_cand"] <= lim5 and f["coldest_c_cand"] >= limc
    for k, name in (("Var", "r12var"), ("Thr", "r13cand")):
        check(f"{name}: recomputed frost guard matches choice.json", guard[k] == choice.get(name, {}).get("guard2_frost"),
              f"{guard[k]}")
    eligible = [n for k, n in (("Var", "r12var"), ("Thr", "r13cand"))
                if guard[k] and dec[k]["primary_pass"] and dec[k]["guard_pass"]]
    pick = min(eligible, key=lambda n: dec["Var" if n == "r12var" else "Thr"]["mixture"]) if eligible else "v12"
    check("mechanical choice reproduces choice.json", pick == choice.get("choice"), f"{pick} vs {choice.get('choice')}")
    check("r12cand fails the frost guard (sensitivity only)", not guard["Cand"], "")

    # --- constants
    for key, nm in (("night_low_ext", "NightLow"), ("night_high_ext", "NightHigh"), ("q_sb_w", "QSb"),
                    ("lead_base_h", "LeadBase"), ("sb_boost_floor_k", "BoostFloor")):
        nd = dict((p[0], p[2]) for p in PARAMS)[key]
        put(f"RTwVTwelve{nm}", fnum(v12.get(key), nd), f"tune/best_params_v12.json {key}")
        put(f"RTwCand{nm}", fnum(cand.get(key), nd), f"round12/candidate_mean.json {key}")
        put(f"RTwVar{nm}", fnum(var.get(key), nd), f"round12/candidate_v12setback.json {key}")
        put(f"RTwThr{nm}", fnum(thr.get(key), nd), f"round13/candidate_mean.json {key}")
        if key in bounds:
            put(f"RTwMax{nm}", fnum(bounds[key][2], nd), f"round12/PLAN.md bound {key}")
    check("r12var = r12cand except the two depths",
          all(abs(var[k] - cand[k]) < 1e-12 for k in cand if k not in ("night_low_ext", "night_high_ext")), "")
    check("r12var depths = v12 depths", all(var[k] == v12[k] for k in ("night_low_ext", "night_high_ext")), "")
    check("r13cand depths = v12 depths", all(thr[k] == v12[k] for k in ("night_low_ext", "night_high_ext")), "")

    # --- Kaggle (v13)
    fb = load(RES / "kaggle_feedback.json") or {}
    ent = [x for v in fb.values() if isinstance(v, list) for x in v
           if isinstance(x, dict) and x.get("label") == KAG_LABEL and ok(x.get("public_score"))]
    if ent:
        k = ent[-1]
        put("RTwKagVThirteen", f"{k['public_score']:.5f}", f"kaggle_feedback.json {KAG_LABEL} public_score")
    else:
        MACROS["RTwKagVThirteen"] = PENDING
        SOURCES["RTwKagVThirteen"] = f"kaggle_feedback.json: no '{KAG_LABEL}' entry yet -> '{PENDING}' (rerun when it lands)"
    check("v13 Kaggle score present", True if ent else None, "pending: rerun once it lands" if not ent else "")

    # --- sensitivity table
    rows = [
        (r"v12", f"{MACROS['RTwVTwelveNightLow']}/{MACROS['RTwVTwelveNightHigh']}", "--",
         "--", "--", "--", "--", MACROS["RTwVTwelveColdest"], MACROS["RTwVTwelveBelowFive"], "--"),
    ]
    for k, name, depth in (("Cand", "r12cand", "tuned"), ("Thr", "r13cand", "fixed"),
                           ("Var", r"\textbf{v13}", "restored")):
        g = "pass" if guard[k] else "fail"
        nl = MACROS[f"RTw{k}NightLow"]
        nhv = MACROS[f"RTw{k}NightHigh"]
        rows.append((name, f"{nl}/{nhv}",
                     f"{MACROS[f'RTw{k}Mix']} [{MACROS[f'RTw{k}MixLo']}, {MACROS[f'RTw{k}MixHi']}]",
                     f"{MACROS[f'RTw{k}HCThree']} ({MACROS[f'RTw{k}HCThreeWins']})",
                     f"{MACROS[f'RTw{k}HH']} ({MACROS[f'RTw{k}HHWins']})",
                     f"{MACROS[f'RTw{k}Pub']} ({MACROS[f'RTw{k}PubWins']})",
                     MACROS[f"RTw{k}HS"], MACROS[f"RTw{k}Coldest"], MACROS[f"RTw{k}BelowFive"], g))
    cap = (r"Tuning the constants (rounds 12--13): full-length confirmation against v12. r12cand: round 12's CMA mean "
           r"(\RTwNParams{} constants); r13cand: round 13's (setback depths fixed at v12's); v13: r12var, r12cand with "
           r"v12's depths restored. Depths: weeknight floor/ceiling widening in K. Mixture: the pre-registered $\tfrac13$\,HC3 $+$ $\tfrac23$\,HH mean ratio to "
           r"v12 minus one, with its paired bootstrap 95\% CI (stratified by set); HC3, HH and P: mean change of the "
           r"loss (wins). HS (\RTwNHS{} harsh scenarios with time series): loss change, coldest zone temperature "
           r"($^\circ$C) and share of zone-steps below 5\,$^\circ$C. Guard: the frost guard (fixed in round 13's plan): below-5"
           r"\,$^\circ$C share at most \RTwGuardBelowFiveLim{} and coldest zone at least \RTwGuardColdestLim\,$^\circ$C. "
           r"All three candidates pass the primary rule and the public guard; only r12var passes the frost guard.")
    T = [r"\begin{table}[t]", f"\\caption{{{cap}}}", r"\label{tab:tuning13}", r"\centering\scriptsize",
         r"\setlength{\tabcolsep}{2pt}", r"\begin{tabular}{@{}llcccccccc@{}}", r"\toprule",
         r"controller & depths & mixture [95\% CI] & HC3 & HH & P & HS & coldest & $<$5\,$^\circ$C & guard \\",
         r"\midrule"]
    T += [" & ".join(r) + r" \\" for r in rows]
    T += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    TAB.write_text("% generated by paper/make_macros_r12.py; do not edit\n" + "\n".join(T) + "\n", encoding="utf-8")

    # --- parameter table (appendix)
    def cell(d, key, nd):
        v = d.get(key)
        return fnum(v, nd) if ok(v) else "--"
    P = [r"\begin{table}[h]",
         r"\caption{The \RTwNParams{} constants tuned in rounds 12--13, with the search bounds of round 12's plan "
         r"(setback burst, $k_q$ and $k_i$ searched on a log scale). r12var, shipped as v13, is r12cand with v12's "
         r"two weeknight setback depths; round 13 held those depths fixed and re-tuned the other "
         r"\RTwNParamsThr{} from r12var.}",
         r"\label{tab:params13}", r"\centering\scriptsize", r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
         r"constant & bounds & v12 & r12cand & \textbf{v13} (r12var) & r13cand \\", r"\midrule"]
    for key, lab, nd in PARAMS:
        b = bounds.get(key)
        bs = f"{fnum(b[1], nd)}--{fnum(b[2], nd)}" if b else "--"
        P.append(" & ".join([lab, bs, cell(v12, key, nd), cell(cand, key, nd), cell(var, key, nd), cell(thr, key, nd)])
                 + r" \\")
    P += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    PTAB.write_text("% generated by paper/make_macros_r12.py; do not edit\n" + "\n".join(P) + "\n", encoding="utf-8")
    for key, _, _ in PARAMS:
        check(f"v12 {key} matches PLAN table", bounds.get(key) and abs(bounds[key][0] - v12[key]) < 1e-9, "")

    # --- write
    n_missing = sum(v == MISSING for v in MACROS.values())
    OUT.write_text("% generated by paper/make_macros_r12.py; do not edit\n" +
                   "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in MACROS.items()), encoding="utf-8")
    L = [BEGIN + "\n", "## Rounds 12-13: claims -> artifacts -> values (generated by paper/make_macros_r12.py)\n\n",
         "| macro | value | source |\n|---|---|---|\n"]
    L += [f"| `{k}` | {v} | {SOURCES[k]} |\n" for k, v in MACROS.items()]
    L.append("\n| check | result | detail |\n|---|---|---|\n")
    L += [f"| {c} | {'PASS' if r else ('n/a' if r is None else 'FAIL')} | {d} |\n" for c, r, d in CHECKS]
    L.append(f"\nMissing values (rounds 12-13): {n_missing}\n{END}\n")
    block = "".join(L)
    a = AUDIT.read_text(encoding="utf-8") if AUDIT.exists() else ""
    if BEGIN in a and END in a:
        a = a[:a.index(BEGIN)] + block + a[a.index(END) + len(END) + 1:]
    else:
        a = a.rstrip("\n") + "\n\n" + block
    AUDIT.write_text(a, encoding="utf-8")
    fails = [c for c, r, _ in CHECKS if r is False]
    print(f"wrote {OUT} ({len(MACROS)} macros, {n_missing} missing); checks failed: {fails or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
