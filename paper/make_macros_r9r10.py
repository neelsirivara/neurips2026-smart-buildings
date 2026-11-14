"""Rounds 9-10 macros (v11, v12) for the paper, and their rows in paper/AUDIT.md.

experiments/src/ was frozen when the paper was brought up to the shipped v12, so these macros come from this script
rather than from experiments/src/make_macros.py. The pattern is the same: every number is read or computed from a
result file, and a missing input prints \\textbf{??}.

Writes  paper/results_macros_r9r10.tex  (\\input after results_macros.tex in main.tex)
        paper/AUDIT.md                   (replaces the block between the r9r10 markers, or appends it; run this after
                                          experiments/src/make_audit.py, which rewrites AUDIT.md from scratch)
Reads   experiments/results/round9/{confirm_r9_dow.json, saturday_precondition_share.json, decomp_r9_summary.json,
          PREREG.md, xcheck_shipped_v11.json}
        experiments/results/round10/{confirm_r10_K.json, PREREG.md, xcheck_shipped_v12.json, sets/sets_r10.json,
          jobs/*.json, jobs/r10_*.log, dev/**/summary.json, xcheck_shipped/**/summary.json}
        experiments/results/round6/runs/{r9_dow,r10_v11,r10_K}/<set>/*/*/transfer/summary.json (comfort shares)
        experiments/results/tune/best_params_v{11,12}.json, experiments/results/kaggle_feedback.json
        experiments/src/mac_runner_r9.py (thread setting of the Mac runner; read only)
        paper/results_macros.tex (cross-check of the parameter macros against v12)

    python paper/make_macros_r9r10.py
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import re
import struct
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
RES = ROOT / "experiments" / "results"
R9, R10 = RES / "round9", RES / "round10"
RUNS = RES / "round6" / "runs"
OUT = PAPER / "results_macros_r9r10.tex"
AUDIT = PAPER / "AUDIT.md"
BEGIN, END = "<!-- r9r10 begin -->", "<!-- r9r10 end -->"
MISSING = r"\textbf{??}"
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore")
STEPS_PER_DAY = 288          # 24 h of 5-minute steps (the kit's control step)
SETS9 = (("P", "Pub"), ("HC2", "HarshCTwo"), ("HS", "HarshS"), ("M", "Minn"), ("FD", "FreshDef"))
SETS10 = (("HC3", "HarshCThree"), ("HH", "HotH"), ("P", "Pub"), ("HS", "HarshS"), ("M", "Minn"), ("FD", "FreshDef"))

MACROS: dict[str, str] = {}
CHECKS: list[tuple[str, bool | None, str]] = []


def load(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def text(p: Path) -> str:
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def put(name: str, val) -> None:
    assert name not in MACROS, name
    MACROS[name] = MISSING if val is None else str(val)


def ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def num(x, nd):
    return f"{x:.{nd}f}" if ok(x) else None


def pct(x, nd=1, signed=False):
    """x is a fraction; signed values carry a math minus or plus."""
    if not ok(x):
        return None
    s = f"{abs(100 * x):.{nd}f}"
    if not signed:
        return f"{100 * x:.{nd}f}\\%"
    sign = "$-$" if (x < 0 and float(s) != 0.0) else "$+$"
    return f"{sign}{s}\\%"


def pabs(x, nd=1):
    return f"{abs(100 * x):.{nd}f}\\%" if ok(x) else None


def tex(s: str) -> str:
    return s.replace("_", r"\_")


def check(label: str, cond, detail: str = "") -> None:
    CHECKS.append((label, None if cond is None else bool(cond), detail))


# ---------------------------------------------------------------- confirmations
def conf_macros(prefix: str, conf: dict, sets) -> None:
    for s, sn in sets:
        r = (conf.get("sets") or {}).get(s) or {}
        n = r.get("n")
        put(f"{prefix}{sn}N", n)
        put(f"{prefix}{sn}Ref", num(r.get("ref"), 5))
        put(f"{prefix}{sn}Cand", num(r.get("cand"), 5))
        put(f"{prefix}{sn}Rel", pct(r.get("rel"), 2, signed=True))
        put(f"{prefix}{sn}RelLo", pct(r.get("rel_ci_lo"), 2, signed=True))
        put(f"{prefix}{sn}RelHi", pct(r.get("rel_ci_hi"), 2, signed=True))
        put(f"{prefix}{sn}RelAbs", pabs(r.get("rel"), 1))
        put(f"{prefix}{sn}RelLoAbs", pabs(r.get("rel_ci_lo"), 1))
        put(f"{prefix}{sn}RelHiAbs", pabs(r.get("rel_ci_hi"), 1))
        put(f"{prefix}{sn}Wins", f"{r['wins']}/{n}" if r else None)
        put(f"{prefix}{sn}Losses", r.get("losses"))
        put(f"{prefix}{sn}WorstRel", pct(r.get("worst_rel"), 2, signed=True))
        put(f"{prefix}{sn}Worst", tex(r["worst"]) if r.get("worst") else None)
        if r:
            ps = r.get("per_scenario") or {}
            check(f"{prefix}{sn}: per-scenario count = n", len(ps) == n, f"{len(ps)} vs {n}")
    ps = (((conf.get("sets") or {}).get("P") or {}).get("per_scenario")) or {}
    for st in STATIONS:
        v = [x["cand"] for k, x in ps.items() if k.split("/")[1].rsplit("_", 1)[0] == st]
        put(f"{prefix}PubCand{st.capitalize()}", num(sum(v) / len(v), 5) if len(v) == 6 else None)
    rule = conf.get("rule") or {}
    put(f"{prefix}RuleMet", {True: "met", False: "not met"}.get(rule.get("met")))


def kaggle_score(fb: dict, tags) -> str | None:
    """Kaggle public score of a version, '--' when no submission of it is recorded."""
    if not fb:
        return None
    for lab, sc in (fb.get("scores_by_policy") or {}).items():
        if any(t in lab for t in tags):
            return num(sc, 5)
    for s in fb.get("submissions", []):
        if any(t in str(s.get("label", "")) for t in tags):
            return "pending" if s.get("public_score") is None else num(s["public_score"], 5)
    return "--"


def decode_day(d: int) -> float:
    """The policy's decode of an integer day sent as float32 sin/cos (Monday = 0): atan2, mapped to [0, 7)."""
    f32 = lambda x: struct.unpack("f", struct.pack("f", x))[0]
    a = 2.0 * math.pi * d / 7.0
    ang = math.atan2(f32(math.sin(a)), f32(math.cos(a)))
    if ang < 0:
        ang += 2.0 * math.pi
    return 7.0 * ang / (2.0 * math.pi)


def summaries(variant: str, set_name: str) -> dict:
    """Loss components per scenario, as experiments/src/compare_r10.summaries (8,640-step runs only)."""
    out = {}
    for f in sorted((RUNS / variant / set_name).glob("building*/*/transfer/summary.json")):
        j = load(f) or {}
        n = j.get("total_steps")
        if n != 8640:
            continue
        out[f"{f.parts[-4]}/{f.parts[-3]}"] = {
            "loss": -j["total_reward"] / n,
            "comfort": -0.6 * j["total_normalized_productivity_regret"] / n,
            "energy": 0.2 * j["total_normalized_energy_cost"] / n,
            "carbon": 0.2 * j["total_normalized_carbon_emission"] / n}
    return out


def comfort_macros(tag: str, ref_v: str, cand_v: str, set_name: str, conf_set: dict) -> None:
    r, c = summaries(ref_v, set_name), summaries(cand_v, set_name)
    keys = sorted(set(r) & set(c))
    n_need = (conf_set or {}).get("n")
    if not keys or len(keys) != n_need:
        for m in ("ComfShare{0}Ref", "ComfShare{0}Cand", "ComfRise{0}"):
            put("RTen" + m.format(tag), None)
        check(f"comfort {tag}: run trees complete", False, f"{len(keys)} of {n_need}")
        return
    mean = lambda d, q: sum(d[k][q] for k in keys) / len(keys)
    put(f"RTenComfShare{tag}Ref", pct(mean(r, "comfort") / mean(r, "loss"), 1))
    put(f"RTenComfShare{tag}Cand", pct(mean(c, "comfort") / mean(c, "loss"), 1))
    put(f"RTenComfRise{tag}", pct(mean(c, "comfort") / mean(r, "comfort") - 1.0, 0))
    d = {q: (mean(c, q) - mean(r, q)) / mean(r, "loss") for q in ("comfort", "energy", "carbon")}
    check(f"comfort {tag}: run-tree loss means = confirmation file (ref, cand)",
          abs(mean(r, "loss") - conf_set["ref"]) < 1e-12 and abs(mean(c, "loss") - conf_set["cand"]) < 1e-12,
          f"{mean(r, 'loss'):.8f}/{conf_set['ref']:.8f}, {mean(c, 'loss'):.8f}/{conf_set['cand']:.8f}")
    check(f"comfort {tag}: 'lower energy cost and carbon more than pay for it' (energy + carbon < -comfort)",
          d["energy"] + d["carbon"] < -d["comfort"] and d["comfort"] > 0,
          f"points of v11's loss: comfort {100 * d['comfort']:+.2f}, energy {100 * d['energy']:+.2f}, "
          f"carbon {100 * d['carbon']:+.2f}")


# ---------------------------------------------------------------- main
def main() -> int:
    c9 = load(R9 / "confirm_r9_dow.json") or {}
    c10 = load(R10 / "confirm_r10_K.json") or {}
    fb = load(RES / "kaggle_feedback.json") or {}
    pre9, pre10 = text(R9 / "PREREG.md"), text(R10 / "PREREG.md")

    # ---- round 9: confirmation of v11 = v10 + dow_snap
    conf_macros("RNineConf", c9, SETS9)
    m = re.search(r"\((\d[\d,]*) resamples, seed 0", pre9)
    put("RNineNBoot", m.group(1) if m else None)
    sat = load(R9 / "saturday_precondition_share.json") or {}
    hc, pub = sat.get("r7hc") or {}, sat.get("pub30") or {}
    put("RNineSatShareHCTwo", pct(hc.get("mean"), 1))
    put("RNineSatShareHCTwoMin", num(100 * hc["min"], 2) if ok(hc.get("min")) else None)
    put("RNineSatShareHCTwoMax", pct(hc.get("max"), 2))
    put("RNineSatSharePub", pct(pub.get("mean"), 1))
    check("Saturday share: HC2 n = 44, public n = 30", hc.get("n") == 44 and pub.get("n") == 30,
          f"{hc.get('n')}, {pub.get('n')}")
    dec = load(R9 / "decomp_r9_summary.json") or {}
    nd = [dec.get(s, {}).get("unpacked") for s in ("pub30", "r7hc")]
    put("RNineNDecomp", sum(nd) if all(isinstance(x, int) for x in nd) else None)
    check("decomposition runs reproduce the round-8 runs (no mismatch)",
          all(not (dec.get(s, {}).get("ref_check") or {}).get("mismatch", [1]) for s in ("pub30", "r7hc")) if dec else None)
    sat_dec, sun_next = f"{decode_day(5):.9f}", f"{decode_day(6) + 1.0:.8f}"
    put("RNineSatDecode", sat_dec)
    put("RNineSunDecode", sun_next)
    check("decoded Saturday and the day after Sunday match round-9 PREREG.md (debug_saturday_r9.py)",
          sat_dec in pre9 and sun_next in pre9, f"{sat_dec}, {sun_next}")
    fd = ((c9.get("sets") or {}).get("FD") or {}).get("per_scenario") or {}
    loss_by_b: dict[str, int] = {}
    for k, v in fd.items():
        b = k.split("/")[0]
        loss_by_b.setdefault(b, 0)
        loss_by_b[b] += v["cand"] > v["ref"]
    put("RNineFDNBuild", len(loss_by_b) if fd else None)
    top = sorted(loss_by_b.items(), key=lambda kv: -kv[1])[:2]
    put("RNineFDTopTwoLosses", sum(v for _, v in top) if fd else None)
    put("RNineFDTopTwoBuild", " and ".join(b.replace("building_", "") for b, _ in sorted(top)) if fd else None)
    check("round-9 FD losses = sum over buildings", sum(loss_by_b.values()) == (c9.get("sets") or {}).get("FD", {}).get("losses"))
    put("RNineKagVEleven", kaggle_score(fb, ("v11", "r9_dow")))
    x11 = load(R9 / "xcheck_shipped_v11.json") or {}
    check("v11: shipped file = confirmation runs bit for bit", all(v.get("identical") for v in x11.values()) if x11 else None,
          f"{len(x11)} scenarios")

    # ---- round 10: confirmation of v12 = v11 + E + C + gated long season
    conf_macros("RTenConf", c10, SETS10)
    m = re.search(r"(\d[\d,]*) resamples, seed 0", pre10)
    put("RTenNBoot", m.group(1) if m else None)
    m = re.search(r"wins \(scenarios with a lower loss than v11\) >= (\d+) of (\d+) \((\d+)%\)", pre10)
    put("RTenRuleWins", f"{m.group(1)}/{m.group(2)}" if m else None)
    put("RTenRuleWinsPct", f"{m.group(3)}\\%" if m else None)
    m = re.search(r"mean relative change is above \+(\d+\.\d+)%", pre10)
    put("RTenRuleMaterial", f"$+${m.group(1)}\\%" if m else None)
    S10 = c10.get("sets") or {}
    hh = S10.get("HH") or {}
    put("RTenConfHotHTies", hh["n"] - hh["wins"] - hh["losses"] if hh else None)
    sets = load(R10 / "sets" / "sets_r10.json") or {}
    w = (hh.get("worst") or "/").split("/")[1]
    ts = ((sets.get("hot_strips") or {}).get(w) or {}).get("start_timestamp")
    put("RTenConfHotHWorstMonth", _dt.datetime.strptime(ts, "%Y-%m-%d %H:%M").strftime("%B") if ts else None)
    put("RTenConfHotHWorstStation", w.rsplit("_", 1)[0].capitalize() if ts else None)
    b3 = sorted({k.split("/")[0] for k in (S10.get("HC3") or {}).get("per_scenario", {})})
    bh = sorted({k.split("/")[0] for k in hh.get("per_scenario", {})})
    put("RTenNNewBuild", len(b3) if b3 else None)
    check("HC3 and HH use the same new buildings", b3 == bh and bool(b3), ", ".join(b3))
    comfort_macros("HCThree", "r10_v11", "r10_K", "r10hc", S10.get("HC3"))
    comfort_macros("Pub", "r9_dow", "r10_K", "pub30", S10.get("P"))
    for s in ("P", "HS", "M", "FD"):
        a, b = (S10.get(s) or {}).get("ref"), ((c9.get("sets") or {}).get(s) or {}).get("cand")
        check(f"round-10 reference on {s} = round-9 v11 runs", ok(a) and ok(b) and abs(a - b) < 1e-15, f"{a} vs {b}")
    v11, v12 = load(RES / "tune" / "best_params_v11.json") or {}, load(RES / "tune" / "best_params_v12.json") or {}
    g = lambda d, k: d.get(k) if isinstance(d.get(k), (int, float)) else None
    put("RTenWkExtLo", f"{g(v12, 'wk_ext_lo'):g}" if g(v12, "wk_ext_lo") is not None else None)
    put("RTenWkExtLoVEleven", f"{g(v11, 'wk_ext_lo'):g}" if g(v11, "wk_ext_lo") is not None else None)
    se, hs, so = g(v12, "season_ext_steps"), g(v12, "heat_season_steps"), g(v12, "season_oat_k")
    put("RTenSeasonSteps", f"{int(se):,}" if se is not None else None)
    put("RTenSeasonDays", f"{se / STEPS_PER_DAY:g}" if se is not None else None)
    put("RTenHeatSeasonDays", f"{hs / STEPS_PER_DAY:g}" if hs is not None else None)
    put("RTenSeasonOatC", f"{so - 273.15:.0f}" if so is not None else None)
    put("RTenMprSafety", f"{g(v12, 'mpr_safety'):g}" if g(v12, "mpr_safety") is not None else None)
    check("v12 switches on: mpr_on 1, mpr_burst 0, dow_snap 1; v11: dow_snap 1, mpr_on 0",
          (g(v12, "mpr_on"), g(v12, "mpr_burst"), g(v12, "dow_snap"), g(v11, "dow_snap"), g(v11, "mpr_on")) == (1, 0, 1, 1, 0))
    check("results/tune/best_params.json = best_params_v12.json (the shipped parameters)",
          load(RES / "tune" / "best_params.json") == v12 and bool(v12))
    x12 = load(R10 / "xcheck_shipped_v12.json") or {}
    put("RTenXcheckN", len(x12) if x12 and all(v.get("identical") and v.get("steps") == 8640 for v in x12.values()) else None)
    put("RTenKagVTwelve", kaggle_score(fb, ("v12", "r10_K")))

    # ---- round-10 compute (Mac): job files, runner logs, fetched summaries
    jobs, steps_ok = {}, True
    for f in sorted((R10 / "jobs").glob("*.json")):
        js = load(f) or []
        jobs[f.stem] = len(js)
        for j in js:
            a = j.get("argv", [])
            steps_ok &= "--steps" in a and a[a.index("--steps") + 1] == "8640"
    done, workers, bad = {}, [], 0
    for f in sorted((R10 / "jobs").glob("r10_*.log")):
        t = text(f)
        done[f.stem] = len(re.findall(r" done \S+ rc=0\b", t))
        bad += len(re.findall(r" done \S+ rc=[1-9]", t))
        workers += [int(x) for x in re.findall(r"workers (\d+)", t)]
    dev1 = [p for p in (R10 / "dev").glob("**/summary.json") if (load(p) or {}).get("total_steps") == 8640]
    xch = [p for p in (R10 / "xcheck_shipped").glob("**/summary.json") if (load(p) or {}).get("total_steps") == 8640]
    need = ("r10_dev_a", "r10_dev_b", "r10_dev_c", "r10_devcheck_K", "r10_confirm_K")
    if all(k in done for k in need) and jobs.get("mac_dev1") == len(dev1) and steps_ok and bad == 0:
        total = sum(done[k] for k in need) + len(dev1) + len(xch)
        put("RTenMacRuns", f"{total:,}")
        put("RTenMacConfRuns", done["r10_confirm_K"])
        put("RTenMacDevRuns", sum(done[k] for k in need[:4]) + len(dev1))
        put("RTenMacXcheckRuns", len(xch))
    else:
        for k in ("RTenMacRuns", "RTenMacConfRuns", "RTenMacDevRuns", "RTenMacXcheckRuns"):
            put(k, None)
    put("RTenMacWorkersMax", max(workers) if workers else None)
    put("RTenSteps", "8,640" if steps_ok and jobs else None)
    runner = text(ROOT / "experiments" / "src" / "mac_runner_r9.py")
    put("RTenOmpThreads", "1" if 'OMP_NUM_THREADS="1"' in runner else None)
    check("round-10 batches: done/rc != 0/workers", bad == 0,
          ", ".join(f"{k} {v}" for k, v in done.items()) + f"; mac_dev1 {len(dev1)} (job file {jobs.get('mac_dev1')}); "
          f"xcheck {len(xch)}; rc != 0: {bad}; workers {sorted(set(workers))}")
    check("dev_b: 94 of its 122 jobs ran (runner stopped, STATUS round 10)", done.get("r10_dev_b") == 94 and jobs.get("dev_b") == 122,
          f"{done.get('r10_dev_b')} of {jobs.get('dev_b')}")

    # ---- cross-check: parameter macros of results_macros.tex (written when v10 shipped) against the shipped v12
    old = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", text(PAPER / "results_macros.tex"), re.M))
    par = {"ParMarginOcc": "margin_occ", "ParMarginPre": "margin_pre", "ParNightLowExt": "night_low_ext",
           "ParNightHighExt": "night_high_ext", "ParKqWPerK": "kq_w_per_k", "ParKiWPerKStep": "ki_w_per_k_step",
           "ParSatCoolHi": "sat_cool_hi", "ParSatMixFloor": "sat_mix_floor", "ParLeadSafety": "lead_safety",
           "ParRateZeroKph": "rate0_kph", "ParHolidayCheckH": "holiday_check_h", "ParHeatSeasonSteps": "heat_season_steps",
           "ParMinOnSteps": "min_on_steps", "ParDischMarginK": "disch_margin_k", "ParRateEma": "rate_ema",
           "ParLeadMinH": "lead_min_h", "ParLeadMaxH": "lead_max_h", "ParValveTarget": "valve_target",
           "ParSbHystK": "sb_hyst_k", "ParQSbW": "q_sb_w", "ParFCapPre": "f_cap_pre", "ParFCapOcc": "f_cap_occ",
           "ParAreaScaleMin": "area_scale_min", "ParAreaScaleMax": "area_scale_max", "ParAreaRef": "area_ref_m2",
           "ParRFDischMargin": "disch_margin_k", "ParRFOccEzero": "occ_press_e0", "ParRFOccSpan": "occ_press_span",
           "ParRFFlushDt": "flush_dt_k", "ParRFFlushWindow": "flush_window_h", "RFiveParWkHi": "wk_ext_hi",
           "RFiveParWkRampEnd": "wk_ramp_end_h", "REigMbrSafety": "mbr_safety"}
    derived = {"RFiveParWkRampStart": v12.get("wk_ramp_end_h", 0) + v12.get("wk_ramp_h", 0),
               "RFiveParQcapKw": v12.get("q_cap_w", 0) / 1000.0}
    bad_par = []
    for mname, val in [(k, v12.get(p)) for k, p in par.items()] + list(derived.items()):
        try:
            if mname in old and val is not None and not math.isclose(float(old[mname]), float(val), rel_tol=2e-3):
                bad_par.append(f"{mname}={old[mname]} vs v12 {val:g}")
        except ValueError:
            bad_par.append(f"{mname}={old[mname]} (not a number)")
    n_par = sum(1 for k in list(par) + list(derived) if k in old)
    check(f"{n_par} parameter macros of results_macros.tex equal v12's values", not bad_par, "; ".join(bad_par) or "all equal")
    check("RFiveParWkLo (= v8-v11 weekend floor) differs from v12: the paper prints RTenWkExtLo for v12",
          old.get("RFiveParWkLo") == MACROS.get("RTenWkExtLoVEleven") != MACROS.get("RTenWkExtLo"),
          f"RFiveParWkLo={old.get('RFiveParWkLo')}, v11 {MACROS.get('RTenWkExtLoVEleven')}, v12 {MACROS.get('RTenWkExtLo')}")
    check("round-9 reference on P = Table 1's v10 row (REigConfPubCand)",
          old.get("REigConfPubCand") == MACROS.get("RNineConfPubRef"), f"{old.get('REigConfPubCand')} vs {MACROS.get('RNineConfPubRef')}")
    clash = sorted(set(MACROS) & set(old))
    check("no macro name shared with results_macros.tex", not clash, ", ".join(clash))

    # ---- directional statements
    S9 = c9.get("sets") or {}
    check("v11: HC2 CI below zero and public CI not entirely above zero (rule met)",
          S9.get("HC2", {}).get("rel_ci_hi", 1) < 0 and S9.get("P", {}).get("rel_ci_lo", 1) <= 0 and (c9.get("rule") or {}).get("met"))
    check("v12: HC3 CI below zero, wins >= 24/40, public CI not above zero, no guard material (rule met)",
          (c10.get("rule") or {}).get("met") and S10.get("HC3", {}).get("rel_ci_hi", 1) < 0 and S10.get("HC3", {}).get("wins", 0) >= 24)
    r8p = (((load(RES / "round8" / "confirm_r7L_mbr2.json") or {}).get("sets") or {}).get("P") or {}).get("rel")
    check("'gains shrank': public reductions v10 > v11 > v12 (Sec. 4; v10 from round8/confirm_r7L_mbr2.json)",
          ok(r8p) and abs(S10.get("P", {}).get("rel", 0)) < abs(S9.get("P", {}).get("rel", 0)) < abs(r8p),
          f"v10 {pabs(r8p)}, v11 {MACROS.get('RNineConfPubRelAbs')}, v12 {MACROS.get('RTenConfPubRelAbs')}")
    check("FD in round 9: CI includes zero (stated as not significant)", S9.get("FD", {}).get("rel_ci_hi", -1) > 0)

    # ---- write the macros
    lines = ["% Generated by paper/make_macros_r9r10.py from the round-9/10 result files. Do not edit.\n"]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in MACROS.items()]
    OUT.write_text("".join(lines), encoding="utf-8")
    n_missing = sum(MISSING in v for v in MACROS.values())

    # ---- audit rows
    rows = [
        ("Round 9: v10's Saturday bug -- decoded Saturday / day after Sunday, Saturday-morning preconditioning share of the loss (App. G)",
         ["RNineNDecomp", "RNineSatDecode", "RNineSunDecode", "RNineSatShareHCTwo", "RNineSatShareHCTwoMin", "RNineSatShareHCTwoMax", "RNineSatSharePub"],
         "round9/decomp_r9_summary.json -> {pub30,r7hc}.unpacked; decode recomputed here (float32 sin/cos of day d of 7, atan2; Saturday d = 5, Sunday d = 6, +1 for the next day) and checked against round9/PREREG.md amendment 2; round9/saturday_precondition_share.json -> r7hc.{mean,min,max}, pub30.mean"),
        ("Round 9: confirmation of v11 (r9_dow) against v10 under the rule of rounds 6-8 (Table 2, Sec. 4, App. G)",
         [f"RNineConf{sn}{q}" for sn in ("HarshCTwo", "Pub") for q in ("N", "Ref", "Cand", "Rel", "RelLo", "RelHi", "RelAbs", "RelLoAbs", "RelHiAbs", "Wins")]
         + [f"RNineConf{sn}{q}" for sn in ("HarshS", "Minn") for q in ("N", "Rel", "Wins")] + ["RNineRuleMet", "RNineNBoot"],
         "round9/confirm_r9_dow.json -> sets.{HC2,P,HS,M}.{n,ref,cand,rel,rel_ci_lo,rel_ci_hi,wins}, rule.met (compare_r9.py; paired bootstrap, seed 0; resamples from round9/PREREG.md Part 1)"),
        ("Round 9: FD secondary (outside the rule) and where its losses sit (App. G)",
         ["RNineConfFreshDefN", "RNineConfFreshDefRel", "RNineConfFreshDefRelLo", "RNineConfFreshDefRelHi", "RNineConfFreshDefWins",
          "RNineConfFreshDefLosses", "RNineConfFreshDefWorstRel", "RNineConfFreshDefWorst", "RNineFDNBuild", "RNineFDTopTwoLosses", "RNineFDTopTwoBuild"],
         "round9/confirm_r9_dow.json -> sets.FD (losses per building from per_scenario cand > ref)"),
        ("Round 9: v11 per-station public means (Table 1); Kaggle (Table 2)",
         ["RNineConfPubCand"] + [f"RNineConfPubCand{s.capitalize()}" for s in STATIONS] + ["RNineKagVEleven"],
         "round9/confirm_r9_dow.json -> sets.P.per_scenario.*.cand (mean of the six buildings per station); kaggle_feedback.json (no v11 entry -> '--')"),
        ("Round 10: confirmation of v12 (r10_K) against v11 (abstract, Table 2, Sec. 4, App. G)",
         [f"RTenConf{sn}{q}" for sn in ("HarshCThree", "Pub") for q in ("N", "Ref", "Cand", "Rel", "RelLo", "RelHi", "RelAbs", "RelLoAbs", "RelHiAbs", "Wins")]
         + [f"RTenConfHotH{q}" for q in ("N", "Rel", "RelLo", "RelHi", "Wins", "Losses", "WorstRel", "Worst")] + ["RTenConfHotHTies"]
         + [f"RTenConf{sn}{q}" for sn in ("HarshS", "Minn") for q in ("Rel", "Wins")]
         + [f"RTenConfFreshDef{q}" for q in ("Rel", "RelLo", "RelHi", "Wins")] + ["RTenRuleMet", "RTenNBoot"],
         "round10/confirm_r10_K.json -> sets.{HC3,P,HH,HS,M,FD}.{n,ref,cand,rel,rel_ci_lo,rel_ci_hi,wins,losses,worst,worst_rel}, rule.met (compare_r10.py confirm; resamples from round10/PREREG.md Part 1)"),
        ("Round 10: ship-rule thresholds (App. G)", ["RTenRuleWins", "RTenRuleWinsPct", "RTenRuleMaterial"],
         "round10/PREREG.md Part 1, rules 1 and 4 (= compare_r10.py: wins >= 24, MATERIAL 0.0020)"),
        ("Round 10: HH's worst window (App. G)", ["RTenConfHotHWorstStation", "RTenConfHotHWorstMonth"],
         "round10/confirm_r10_K.json -> sets.HH.worst; round10/sets/sets_r10.json -> hot_strips.<window>.start_timestamp"),
        ("Round 10: comfort share of the loss, v11 -> v12, on HC3 and the public 30 (App. G)",
         ["RTenComfShareHCThreeRef", "RTenComfShareHCThreeCand", "RTenComfRiseHCThree", "RTenComfSharePubRef", "RTenComfSharePubCand", "RTenComfRisePub"],
         "round6/runs/{r10_v11,r10_K}/r10hc and {r9_dow,r10_K}/pub30 -> */*/transfer/summary.json: comfort = 0.6 total_normalized_productivity_regret / steps, loss = -total_reward / steps (compare_r10.summaries); share = mean comfort / mean loss over the set"),
        ("Round 10: the new buildings of HC3 and HH (abstract, App. G)", ["RTenNNewBuild"],
         "round10/confirm_r10_K.json -> sets.HC3.per_scenario (distinct buildings; the same eight in HH)"),
        ("Round 10: v12's parameters (Sec. 3, Table 2, Table 10, App. G)",
         ["RTenWkExtLo", "RTenWkExtLoVEleven", "RTenSeasonSteps", "RTenSeasonDays", "RTenHeatSeasonDays", "RTenSeasonOatC", "RTenMprSafety"],
         "results/tune/best_params_v12.json -> wk_ext_lo, season_ext_steps (/288 steps per day), heat_season_steps, season_oat_k (- 273.15), mpr_safety; best_params_v11.json -> wk_ext_lo"),
        ("Round 10: v12 per-station public means (abstract, Table 1, Sec. 4)",
         ["RTenConfPubCand"] + [f"RTenConfPubCand{s.capitalize()}" for s in STATIONS],
         "round10/confirm_r10_K.json -> sets.P.cand and per_scenario.*.cand (mean of the six buildings per station)"),
        ("Round 10: shipped file = confirmation runs; Kaggle (App. G, Table 2)", ["RTenXcheckN", "RTenKagVTwelve"],
         "round10/xcheck_shipped_v12.json (identical totals at 8,640 steps); kaggle_feedback.json (no v12 entry -> '--')"),
        ("Round 10: compute on the M5 Pro (Sec. 4 Setup)",
         ["RTenMacRuns", "RTenMacDevRuns", "RTenMacConfRuns", "RTenMacXcheckRuns", "RTenSteps", "RTenMacWorkersMax", "RTenOmpThreads"],
         "round10/jobs/{mac_dev1,dev_a,dev_b,dev_c,confirm_K}.json (argv --steps 8640) and r10_{dev_a,dev_b,dev_c,devcheck_K,confirm_K}.log ('done ... rc=0' lines, 'workers N'); round10/dev and xcheck_shipped summaries (8,640 steps); experiments/src/mac_runner_r9.py (OMP_NUM_THREADS=1)"),
    ]
    L = [BEGIN + "\n", "## Rounds 9-10: claims -> artifacts -> values (generated by paper/make_macros_r9r10.py)\n\n",
         "Paths are relative to `experiments/results/` unless they start with `experiments/` or `paper/`. Typed constants of "
         "these rounds are listed in `AUDIT_header.md` (\"Rounds 9-10\").\n\n",
         "| # | claim (paper location) | macro = value | artifact |\n|---|---|---|---|\n"]
    for i, (claim, names, src) in enumerate(rows, 1):
        vals = []
        for n in names:
            v = MACROS.get(n, "(no macro)")
            vals.append(f"`{n}`=" + (f"**{v}**" if (MISSING in v or v == "(no macro)") else v))
        L.append(f"| R{i} | {claim} | {'; '.join(vals)} | `{src}` |\n")
    listed = {n for _, names, _ in rows for n in names}
    rest = [n for n in MACROS if n not in listed]
    L.append(f"| R{len(rows) + 1} | Further macros of the same files (not all printed in the paper) | "
             + "; ".join(f"`{n}`={MACROS[n]}" for n in rest) + " | as the rows above |\n")
    L.append("\n### Checks run by the generator\n\n")
    for label, res, detail in CHECKS:
        L.append(f"- {'PASS' if res else ('FAIL' if res is False else 'n/a')}: {label}" + (f" ({detail})" if detail else "") + "\n")
    L.append(f"\nMissing or placeholder values (rounds 9-10): {n_missing}\n{END}\n")
    block = "".join(L)
    a = text(AUDIT)
    if BEGIN in a and END in a:
        a = a[:a.index(BEGIN)] + block + a[a.index(END) + len(END) + 1:]
    else:
        a = a.rstrip("\n") + "\n\n" + block
    AUDIT.write_text(a, encoding="utf-8")
    n_fail = sum(1 for _, r, _ in CHECKS if r is False)
    print(f"wrote {OUT} ({len(MACROS)} macros, {n_missing} missing) and the r9r10 block of {AUDIT} "
          f"({len(CHECKS)} checks, {n_fail} failed)")
    for label, res, detail in CHECKS:
        if not res:
            print("  CHECK", "FAIL" if res is False else "n/a", label, detail)
    return 1 if (n_missing or n_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())
