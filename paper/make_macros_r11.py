"""Round 11 macros and tables for the paper (review 2026-11-05: P4, P6, P7, P8), and their rows in paper/AUDIT.md.

Same pattern as make_macros_r9r10.py: every number is read or computed from a result file; a missing input prints
\\textbf{??}. Run it after make_macros_r9r10.py.

Writes  paper/results_macros_r11.tex   (\\input after results_macros_r9r10.tex)
        paper/table_main_r11.tex        (Table 1: public-30 metric per policy, ratio to v12 with paired bootstrap CI)
        paper/table_versions_r11.tex    (the same for every SADR version, appendix)
        paper/table_ablation_r11.tex    (leave-one-out ablation of v12 on the public 30)
        paper/table_checks_r7.tex       (all twelve round-7 model checks, from results_macros.tex)
        paper/figures/fig_loss_by_hour_v12.pdf (v12 and pid_water loss by hour of day, public 30)
        paper/AUDIT.md                  (replaces the block between the r11 markers, or appends it)
Reads   experiments/results/round6/runs/<variant>/<set>/*/*/<policy>/summary.json (+ timeseries.csv.gz), results/final*,
        results/round5/full/r5_c12_comp, results/round10/confirm_r10_K.json, kit/baseline_returns.json,
        experiments/results/round11/PLAN.md, paper/results_macros.tex

    python paper/make_macros_r11.py
"""
from __future__ import annotations

import csv
import glob
import gzip
import io
import json
import math
import random
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
RES = ROOT / "experiments" / "results"
RUNS = RES / "round6" / "runs"
R11 = RES / "round11"
OUT = PAPER / "results_macros_r11.tex"
AUDIT = PAPER / "AUDIT.md"
BEGIN, END = "<!-- r11 begin -->", "<!-- r11 end -->"
MISSING = r"\textbf{??}"
STATIONS = ("fairbanks", "denver", "atlanta", "phoenix", "singapore")
NBOOT, SEED = 5000, 0
STEPS = 8640

MACROS: dict[str, str] = {}
SOURCES: dict[str, str] = {}
CHECKS: list[tuple[str, bool | None, str]] = []


def put(name: str, val, src: str) -> None:
    assert name not in MACROS, name
    MACROS[name] = MISSING if val is None else str(val)
    SOURCES[name] = src


def check(label: str, cond, detail: str = "") -> None:
    CHECKS.append((label, None if cond is None else bool(cond), detail))


def ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def num(x, nd):
    return f"{x:.{nd}f}" if ok(x) else None


def spct(x, nd=1):
    """Signed percentage with a math minus/plus (x is a fraction)."""
    if not ok(x):
        return None
    s = f"{abs(100 * x):.{nd}f}"
    sign = "$-$" if (x < 0 and float(s) != 0.0) else "$+$"
    return f"{sign}{s}\\%"


def pabs(x, nd=1):
    return f"{abs(100 * x):.{nd}f}\\%" if ok(x) else None


def summaries(pattern: str) -> dict[str, dict]:
    out = {}
    for f in glob.glob(str(RES / pattern)):
        try:
            s = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        if s.get("total_steps") != STEPS:
            continue
        out[f"{s['building']}/{s['weather']}"] = s | {"_path": f}
    return out


def scores(pattern: str) -> dict[str, float]:
    return {k: abs(s["avg_reward"]) for k, s in summaries(pattern).items()}


def organizer_pid() -> dict[str, float]:
    try:
        d = json.loads((ROOT / "kit" / "baseline_returns.json").read_text())
    except (OSError, ValueError):
        return {}
    return {k: abs(v["pid_water"]) / STEPS for k, v in d.items() if "pid_water" in v}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def boot_ratio(a: dict, b: dict, cluster: bool = False):
    """mean(a)/mean(b) over shared keys with a percentile CI (paired; cluster=True resamples buildings)."""
    keys = sorted(set(a) & set(b))
    if not keys:
        return None, None, None, 0
    rng = random.Random(SEED)
    units = sorted({k.split("/")[0] for k in keys}) if cluster else keys
    members = {u: [k for k in keys if (k.split("/")[0] if cluster else k) == u] for u in units}
    est = mean(a[k] for k in keys) / mean(b[k] for k in keys)
    rs = []
    for _ in range(NBOOT):
        pick = [k for _u in range(len(units)) for k in members[units[rng.randrange(len(units))]]]
        rs.append(mean(a[k] for k in pick) / mean(b[k] for k in pick))
    rs.sort()
    return est, rs[int(0.025 * NBOOT)], rs[int(0.975 * NBOOT) - 1], len(units)


# ---------------------------------------------------------------- Table 1 and the version table
ROWS = [
    ("v12", "SADR v12 (shipped)", "round6/runs/r10_K/pub30/*/*/transfer/summary.json", "M5 Pro"),
    ("v11", "SADR v11", "round6/runs/r9_dow/pub30/*/*/transfer/summary.json", "Kaggle"),
    ("v10", "SADR v10", "round6/runs/r7L_mbr2/pub30/*/*/transfer/summary.json", "Kaggle"),
    ("v9", "SADR v9", "round6/runs/r6_comp/pub30/*/*/transfer/summary.json", "M5 Pro"),
    ("v8", "SADR v8", "round5/full/r5_c12_comp/pub30/*/*/transfer/summary.json", "laptop"),
    ("v7", "SADR v7", "final_r4/*/*/transfer/summary.json", "laptop"),
    ("v6", "SADR v6", "final/*/*/transfer/summary.json", "laptop"),
    ("v5", "SADR v5", "final/*/*/transfer_v5/summary.json", "laptop"),
    ("pid_water", "\\texttt{pid\\_water}", "final/*/*/pid_water/summary.json", "laptop"),
    ("fixed_setpoint", "\\texttt{fixed\\_setpoint}", "final/*/*/fixed_setpoint/summary.json", "laptop"),
    ("bang_bang", "\\texttt{bang\\_bang}", "final/*/*/bang_bang/summary.json", "laptop"),
    ("pid_water_org", "\\texttt{pid\\_water} (organizer values)", None, "organizers"),
]
MAIN_ROWS = ("v12", "v6", "v5", "pid_water", "fixed_setpoint", "bang_bang", "pid_water_org")


def table_rows(keys_wanted, data, ref):
    lines = []
    for key, label, pattern, machine in ROWS:
        if key not in keys_wanted:
            continue
        d = data[key]
        cells = [num(mean(d.values()), 5)] + [num(mean(v for k, v in d.items() if k.split("/")[1].startswith(st)), 5)
                                              for st in STATIONS]
        if key == "v12":
            tail = ["1", "--"]
        else:
            r, lo, hi, _ = boot_ratio(d, ref)
            wins = sum(1 for k in ref if k in d and ref[k] < d[k])
            tail = [f"{num(r, 2)} [{num(lo, 2)}, {num(hi, 2)}]" if ok(r) else MISSING, f"{wins}/{len(ref)}"]
        cells = [c if c is not None else MISSING for c in cells]
        bold = key == "v12"
        cells = [f"\\textbf{{{c}}}" if bold and i == 0 else c for i, c in enumerate(cells)]
        lines.append(" & ".join([label] + cells + tail) + r" \\")
    return lines


def write_table(path: Path, caption: str, label: str, keys_wanted, data, ref) -> None:
    head = [r"\begin{table}[t]", f"\\caption{{{caption}}}", f"\\label{{{label}}}", r"\centering\scriptsize",
            r"\setlength{\tabcolsep}{3pt}", r"\begin{tabular}{lcccccccc}", r"\toprule",
            r"policy & all & Fairbanks & Denver & Atlanta & Phoenix & Singapore & ratio to v12 [95\% CI] & v12 wins \\",
            r"\midrule"]
    tail = [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    path.write_text("% generated by paper/make_macros_r11.py; do not edit\n" +
                    "\n".join(head + table_rows(keys_wanted, data, ref) + tail) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- ablation
ABL = [  # arm, mechanism (version), group
    ("ab12_noarea", "zone gains scaled with zone area (v6)", "core"),
    ("ab12_nozone", "per-zone optimum start (v6)", "core"),
    ("ab12_nofloor", "setback floor limited to what the zone recovers (v6)", "core"),
    ("ab12_nowcap", "requests capped at the coil's delivery (v6)", "core"),
    ("ab12_noecon", "economizer", "core"),
    ("ab12_sat293", "coldest supply air (v5; arm: v4's reset, ceiling 293\\,K)", "core"),
    ("ab12_tw330", "350\\,K hot water in heating season (arm: 330\\,K)", "core"),
    ("ab12_nooccdyn", "occupied flow in proportion to the error (v7)", "added"),
    ("ab12_noflush", "night flush (v7)", "added"),
    ("ab12_noneutral", "set-back forced air reheated to zone temperature (v7)", "added"),
    ("ab12_noweekend", "deeper weekend setback (v8, v12)", "added"),
    ("ab12_qcap12", "request cap 20\\,kW per 100\\,m$^2$ (v8; arm: v7's 12\\,kW)", "added"),
    ("ab12_noboost", "set-back air boost (v9)", "added"),
    ("ab12_nomodel", "model-based starts (v10, v12)", "added"),
    ("ab12_nodow", "day of week rounded after decoding (v11)", "added"),
    ("ab12_noseason", "7-day heating season below 15\\,$^\\circ$C (v12)", "added"),
]


def terms(s: dict) -> tuple[float, float, float]:
    """Comfort, energy and carbon cost per step. The runner stores the regret as a (negative) reward and the
    energy and carbon as positive costs: reward = 0.6 regret - 0.2 energy - 0.2 carbon (as compare_r10.py)."""
    n = s["total_steps"]
    return (-0.6 * s["total_normalized_productivity_regret"] / n, 0.2 * s["total_normalized_energy_cost"] / n,
            0.2 * s["total_normalized_carbon_emission"] / n)


def ablation(ref_s: dict) -> list[str]:
    ref = {k: abs(v["avg_reward"]) for k, v in ref_s.items()}
    rows, n_done = [], 0
    ref_loss = mean(ref.values()) if ref else None
    for arm, mech, grp in ABL:
        s = summaries(f"round6/runs/{arm}/pub30/*/*/transfer/summary.json")
        d = {k: abs(v["avg_reward"]) for k, v in s.items()}
        complete = len(d) == 30 and set(d) == set(ref)
        if not complete:
            rows.append(f"{mech} & {len(d)}/30 run & " + " & ".join([MISSING] * 5) + r" \\")
            continue
        n_done += 1
        r, lo, hi, _ = boot_ratio(d, ref)
        rc, loc, hic, nb = boot_ratio(d, ref, cluster=True)
        wins = sum(1 for k in ref if ref[k] < d[k])
        losses = sum(1 for k in ref if ref[k] > d[k])
        dt = [mean(terms(s[k])[i] - terms(ref_s[k])[i] for k in ref) / ref_loss for i in range(3)]
        rows.append(" & ".join([mech, num(mean(d.values()), 5),
                                f"{spct(r - 1)} [{spct(lo - 1)}, {spct(hi - 1)}]",
                                f"[{spct(loc - 1)}, {spct(hic - 1)}]", f"{wins}/{losses}",
                                ", ".join(spct(x) for x in dt)]) + r" \\")
        tag = re.sub(r"[^A-Za-z]", "", arm.replace("ab12_", "").title())
        put(f"RElvAb{tag}Rel", spct(r - 1), f"round6/runs/{arm}/pub30 vs ab12_ref/pub30: mean ratio - 1")
        put(f"RElvAb{tag}Wins", f"{wins}/30", f"round6/runs/{arm}/pub30 vs ab12_ref: scenarios where v12 is lower")
    put("RElvAbNDone", n_done, "arms with all 30 public runs fetched")
    return rows


def write_ablation(ref_s: dict) -> None:
    if ref_s:
        rows = ablation(ref_s)
    else:
        rows = [r"\multicolumn{6}{c}{\textbf{??} runs missing} \\"]
        put("RElvAbNDone", 0, "arms with all 30 public runs fetched (reference runs missing)")
    head = [r"\begin{table}[t]",
            r"\caption{Leave-one-out ablation of the shipped v12 on the 30 public scenarios (8,640 steps, private Kaggle "
            r"CPU kernels). Each row changes one mechanism and keeps the rest of v12 (overrides in "
            r"\texttt{experiments/results/round11/params/}). Change: mean loss of the arm against v12 "
            r"(\RElvAbRefLoss), paired bootstrap 95\% CI over scenarios and over the six buildings (cluster); "
            r"positive = the mechanism helps. Wins/losses: scenarios where v12 is lower/higher. Terms: change in "
            r"comfort, energy cost and carbon as a share of v12's loss. Plan fixed before any run "
            r"(\texttt{round11/PLAN.md}).}",
            r"\label{tab:ablation12}", r"\centering\scriptsize", r"\setlength{\tabcolsep}{2pt}",
            r"\begin{tabular}{>{\raggedright\arraybackslash}p{3.8cm}cccc>{\raggedright\arraybackslash}p{2.5cm}}",
            r"\toprule",
            r"mechanism removed (arm) & loss & change [95\% CI] & cluster CI & v12 wins/losses & comfort, energy, carbon \\",
            r"\midrule"]
    tail = [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (PAPER / "table_ablation_r11.tex").write_text("% generated by paper/make_macros_r11.py; do not edit\n" +
                                                  "\n".join(head + rows + tail) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- time series: coldest zone, loss by hour
def read_ts(summary_path: str):
    d = Path(summary_path).parent
    for name in ("timeseries.csv.gz", "timeseries.csv"):
        p = d / name
        if p.exists():
            raw = gzip.decompress(p.read_bytes()) if name.endswith(".gz") else p.read_bytes()
            return list(csv.reader(io.StringIO(raw.decode())))
    return None


def coldest(ref_hs: dict):
    tmin, below, total, n_ts = None, 0, 0, 0
    for k, s in ref_hs.items():
        rows = read_ts(s["_path"])
        if not rows:
            continue
        n_ts += 1
        zi = [i for i, h in enumerate(rows[0]) if h.startswith("zone_")]
        for r in rows[1:]:
            for i in zi:
                t = float(r[i])
                tmin = t if tmin is None else min(tmin, t)
                below += t < 278.15
                total += 1
    return tmin, (below / total if total else None), n_ts


def loss_by_hour(sets: dict[str, dict]) -> dict[str, list[tuple[float, float]]]:
    out = {}
    for name, ss in sets.items():
        acc = [[0.0, 0.0, 0] for _ in range(24)]
        for k, s in ss.items():
            rows = read_ts(s["_path"])
            if not rows:
                continue
            h = rows[0]
            ir, ip = h.index("reward"), h.index("productivity_regret")
            for r in rows[1:]:
                hr = int(r[0][11:13])
                comfort = -0.6 * float(r[ip])          # the regret column is a (negative) reward
                acc[hr][0] += comfort
                acc[hr][1] += -float(r[ir]) - comfort
                acc[hr][2] += 1
        out[name] = [(a / n, b / n) if n else (float("nan"), float("nan")) for a, b, n in acc]
    return out


def figure_hours(prof: dict) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["pdf.fonttype"] = 42  # TrueType, not Type 3 (NeurIPS font rule)
        matplotlib.rcParams["ps.fonttype"] = 42
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    if not prof or any(all(math.isnan(x[0]) for x in v) for v in prof.values()):
        return False
    fig, axes = plt.subplots(1, len(prof), figsize=(7.0, 2.3), sharey=False)
    for ax, (name, p) in zip(axes, prof.items()):
        hrs = range(24)
        c = [x[0] for x in p]
        e = [x[1] for x in p]
        ax.axvspan(6, 19, color="0.92", zorder=0)
        ax.bar(hrs, e, color="#4C72B0", label="energy + carbon")
        ax.bar(hrs, c, bottom=e, color="#DD8452", label="comfort regret")
        ax.set_ylim(0, 1.08 * max(a + b for a, b in zip(c, e)))
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("hour of day", fontsize=8)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel("mean loss per step", fontsize=8)
    axes[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(PAPER / "figures" / "fig_loss_by_hour_v12.pdf")
    fig.savefig(PAPER / "figures" / "fig_loss_by_hour_v12.png", dpi=150)
    plt.close(fig)
    return True


# ---------------------------------------------------------------- round-7 checks table
def checks_table() -> None:
    mac = (PAPER / "results_macros.tex").read_text(encoding="utf-8")
    have = set(re.findall(r"\\newcommand\{\\(RSevChk\w+)\}", mac))
    arms = (("Nle", "floor 2\\,K deeper"), ("NleF", "floor 4\\,K deeper"), ("Ls", "lead safety 1.15"),
            ("LsO", "lead safety 1.0"))
    rows = []
    for b, word in (("Eight", "8"), ("Seven", "7"), ("One", "1")):
        for a, desc in arms:
            cells = []
            for q in ("Pred", "Meas", "Loss"):
                name = f"RSevChk{b}{a}{q}"
                cells.append(f"$\\{name}$" if name in have else MISSING)
            rows.append(f"{word} & {desc} & " + " & ".join(cells) + r" \\")
    check("all 12 round-7 checks have macros", len(have) >= 36, f"{len(have)} RSevChk macros")
    body = [r"\begin{table}[h]",
            r"\caption{All twelve seven-day model checks of round 7 (three harsh scenarios, v9 code): the first-order "
            r"zone model's predicted change in gas against the measured change, and the measured change in the loss. "
            r"Section~\ref{sec:analysis} quotes four of them.}",
            r"\label{tab:checks_r7}", r"\centering\scriptsize",
            r"\begin{tabular}{llccc}", r"\toprule",
            r"building & change & gas, predicted & gas, measured & loss, measured \\", r"\midrule"]
    body += rows + [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (PAPER / "table_checks_r7.tex").write_text("% generated by paper/make_macros_r11.py; do not edit\n" +
                                              "\n".join(body) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main
def main() -> int:
    data = {}
    for key, label, pattern, machine in ROWS:
        data[key] = organizer_pid() if pattern is None else scores(pattern)
        check(f"{key}: 30 public scenarios", len(data[key]) == 30, f"{len(data[key])} found")
    ref = data["v12"]
    # v12's Kaggle public-leaderboard reading (submitted 2026-11-06 under the user's rule for reversible probes)
    fb = json.loads((RES / "kaggle_feedback.json").read_text(encoding="utf-8"))
    k12 = [x for x in fb["submissions"] if x.get("label") == "v12_r10_K"]
    if k12 and k12[0].get("public_score") is not None:
        k = k12[0]
        put("RElvKagRank", k["public_rank"], "kaggle_feedback.json v12_r10_K public_rank (leaderboard file of read_at)")
        put("RElvKagTeams", k["teams"], "kaggle_feedback.json v12_r10_K teams")
        put("RElvKagBest", f"{k['field']['best']:.4f}", "kaggle_feedback.json v12_r10_K field.best")
        put("RElvKagMedian", f"{k['field']['median']:.4f}", "kaggle_feedback.json v12_r10_K field.median")
        put("RElvKagDate", "6 November", "kaggle_feedback.json v12_r10_K read_at")
        put("RElvKagVsTen", f"{100 * (1 - k['public_score'] / 0.01055):.1f}\\%", "1 - v12 public / v10 public (0.01055)")
        check("v12 Kaggle public score read", True, f"{k['public_score']} rank {k['public_rank']}/{k['teams']}")
    # the confirmation file's v12 must be the same numbers
    conf = json.loads((RES / "round10" / "confirm_r10_K.json").read_text())
    ps = conf["sets"]["P"]["per_scenario"]
    check("v12 runs = confirm_r10_K P.cand", all(abs(ps[k]["cand"] - ref.get(k, -1)) < 1e-12 for k in ps),
          "per scenario, 1e-12")
    write_table(PAPER / "table_main_r11.tex",
                r"Leaderboard metric on the \NScen{} public scenarios (mean over scenarios of $|$mean per-step reward$|$; "
                r"lower is better) and per-station means. Ratio to v12: mean of the row over mean of v12, paired "
                r"bootstrap 95\% CI over scenarios (\RElvNBoot{} resamples); v12 wins: scenarios where v12 is lower. "
                r"Every SADR version is in Table~\ref{tab:versions}; the last row is the organizers' shipped returns. "
                r"Per-scenario numbers: Appendix~\ref{app:per_scenario}.",
                "tab:main", MAIN_ROWS, data, ref)
    write_table(PAPER / "table_versions_r11.tex",
                r"Every SADR version on the public scenarios, as Table~\ref{tab:main}. Machines: v12 and v9 the M5 Pro, "
                r"v11 and v10 Kaggle CPU kernels, v8 and earlier the laptop; SADR reproduces bit for bit on laptop and "
                r"Kaggle and within \RSixMacReproMaxRel{} on the M5 Pro.",
                "tab:versions", [r[0] for r in ROWS], data, ref)
    put("RElvNBoot", f"{NBOOT:,}", "this script: bootstrap resamples")
    r, lo, hi, _ = boot_ratio(ref, data["pid_water"])
    put("RElvPwRatio", num(r, 3), "v12 / pid_water public means")
    put("RElvPwRatioLo", num(lo, 3), "paired bootstrap over scenarios, 2.5%")
    put("RElvPwRatioHi", num(hi, 3), "paired bootstrap over scenarios, 97.5%")
    put("RElvPwTimes", num(1 / r, 1) if ok(r) else None, "pid_water / v12 public means")
    put("RElvPwWins", f"{sum(1 for k in ref if ref[k] < data['pid_water'][k])}/{len(ref)}", "v12 below pid_water")
    rc, loc, hic, nb = boot_ratio(ref, data["pid_water"], cluster=True)
    put("RElvPwRatioCLo", num(loc, 3), "cluster (building) bootstrap, 2.5%")
    put("RElvPwRatioCHi", num(hic, 3), "cluster (building) bootstrap, 97.5%")
    # clustered CIs of the round-10 confirmation (v11 -> v12)
    for sname, tag in (("P", "Pub"), ("HC3", "HCThree")):
        pss = conf["sets"][sname]["per_scenario"]
        cand = {k: v["cand"] for k, v in pss.items()}
        refv = {k: v["ref"] for k, v in pss.items()}
        r0, l0, h0, n0 = boot_ratio(cand, refv)
        rc, lc, hc, nb = boot_ratio(cand, refv, cluster=True)
        check(f"{sname}: scenario bootstrap reproduces the confirmation CI",
              abs((l0 - 1) - conf["sets"][sname]["rel_ci_lo"]) < 0.002 and abs((h0 - 1) - conf["sets"][sname]["rel_ci_hi"]) < 0.002,
              f"{l0 - 1:.4f}/{h0 - 1:.4f} vs {conf['sets'][sname]['rel_ci_lo']:.4f}/{conf['sets'][sname]['rel_ci_hi']:.4f}")
        put(f"RElvCl{tag}Lo", spct(lc - 1), f"round10/confirm_r10_K.json sets.{sname}.per_scenario, building bootstrap 2.5%")
        put(f"RElvCl{tag}Hi", spct(hc - 1), f"... 97.5%")
        put(f"RElvCl{tag}NB", nb, f"... number of buildings")
    # ablation and time series
    ref_s = summaries("round6/runs/ab12_ref/pub30/*/*/transfer/summary.json")
    if ref_s:
        rel = [abs(abs(ref_s[k]["avg_reward"]) / ref[k] - 1) for k in ref_s if k in ref]
        n_same = sum(r == 0.0 for r in rel)
        worst = max(rel) if rel else None
        check("ab12_ref (Kaggle) reproduces r10_K (M5 Pro) on the public 30 within 1e-8",
              len(ref_s) == 30 and worst is not None and worst < 1e-8,
              f"{len(ref_s)} runs; {n_same} bit-identical; largest relative difference {worst:.1e}" if rel else "")
        if len(ref_s) == 30 and worst is not None and worst < 1e-8:
            mant, expo = f"{worst:.0e}".split("e")
            txt = "bit for bit" if worst == 0 else \
                f"to within a relative ${mant}\\times10^{{{int(expo)}}}$ ({n_same} of 30 bit for bit)"
        else:
            txt = None
        put("RElvAbRefMatch", txt, "ab12_ref vs r10_K, public 30: largest relative score difference")
    else:
        put("RElvAbRefMatch", None, "ab12_ref vs r10_K")
    put("RElvAbRefLoss", num(mean(abs(s["avg_reward"]) for s in ref_s.values()), 5) if len(ref_s) == 30 else None,
        "round6/runs/ab12_ref/pub30 mean")
    write_ablation(ref_s if len(ref_s) == 30 else {})
    hs = summaries("round6/runs/ab12_ref/r6hs/*/*/transfer/summary.json")
    fr = summaries("round6/runs/ab12_frost5/r6hs/*/*/transfer/summary.json")
    tmin, below, n_ts = coldest(hs) if len(hs) == 18 else (None, None, 0)
    put("RElvColdestHS", num(tmin - 273.15, 1) if ok(tmin) else None, "round6/runs/ab12_ref/r6hs timeseries: min zone temp")
    put("RElvBelowFiveHS", pabs(below, 1) if ok(below) else None, "... share of zone-steps below 278.15 K")
    if len(hs) == 18 and len(fr) == 18:
        a = {k: abs(v["avg_reward"]) for k, v in fr.items()}
        b = {k: abs(v["avg_reward"]) for k, v in hs.items()}
        r, lo, hi, _ = boot_ratio(a, b)
        put("RElvFrostHsRel", spct(r - 1), "ab12_frost5 vs ab12_ref on HS")
        put("RElvFrostHsLo", spct(lo - 1), "paired bootstrap 2.5%")
        put("RElvFrostHsHi", spct(hi - 1), "paired bootstrap 97.5%")
        put("RElvFrostHsWins", f"{sum(1 for k in b if b[k] < a[k])}/18", "scenarios where v12 is lower")
    else:
        for n in ("Rel", "Lo", "Hi", "Wins"):
            put(f"RElvFrostHs{n}", None, "ab12_frost5 / ab12_ref on HS")
    pid_s = summaries("final/*/*/pid_water/summary.json")
    prof = loss_by_hour({"SADR (base)": ref_s, "pid\\_water": pid_s}) if len(ref_s) == 30 else {}
    if prof:
        prof = {k.replace("\\", ""): v for k, v in prof.items()}
    made = figure_hours(prof)
    check("v12 loss-by-hour figure", made, "needs ab12_ref and pid_water time series")
    if made:
        p = prof["SADR (base)"]
        tot = sum(a + b for a, b in p)
        unocc = sum(a + b for h, (a, b) in enumerate(p) if not 6 <= h < 19)
        put("RElvHourPeak", f"{max(range(24), key=lambda h: p[h][0] + p[h][1]):02d}", "hour with the largest v12 loss")
        put("RElvUnoccHourShare", pabs(unocc / tot, 0), "share of v12's hourly loss outside 06-19 (unweighted)")
    else:
        put("RElvHourPeak", None, "v12 loss-by-hour")
        put("RElvUnoccHourShare", None, "v12 loss-by-hour")
    checks_table()
    # parameters the main text now names, v12's worst public scenario, the round-9 perfect-foresight bound
    p12 = json.loads((RES / "tune" / "best_params_v12.json").read_text())
    put("RElvParLeadBaseH", num(p12["lead_base_h"], 1), "results/tune/best_params_v12.json lead_base_h")
    put("RElvParQOnW", num(p12["q_on_w"], 0), "results/tune/best_params_v12.json q_on_w")
    put("RElvParFrostK", None if "frost_floor_k" not in p12 else num(p12["frost_floor_k"], 0),
        "results/tune/best_params_v12.json frost_floor_k (0 = no frost floor)")
    wk = max(ref, key=ref.get)
    put("RElvWorstPub", num(ref[wk], 4), "v12 public: largest per-scenario score")
    put("RElvWorstPubScen", "\\texttt{" + wk.replace("_", "\\_") + "}", "v12 public: its scenario")
    s_w = summaries(f"round6/runs/r10_K/pub30/{wk}/transfer/summary.json")[wk]
    c, e, cb = terms(s_w)
    put("RElvWorstPubComfortShare", pabs(c / ref[wk], 0), "that scenario: 0.6 regret / loss")
    ab4 = json.loads((RES / "tune" / "ablation.json").read_text())
    put("RElvTuneGain", pabs(ab4["best"]["score"] / ab4["default"]["score"] - 1, 1),
        "results/tune/ablation.json: best/default screening score - 1 (the random search's whole gain)")
    lp = json.loads((RES / "round9" / "lp_summary.json").read_text())
    shares = [v["gs_loss_share"] for k, v in lp.items()
              if not k.startswith("_") and isinstance(v, dict) and "gs_loss_share" in v]
    put("RElvLpN", len(shares), "results/round9/lp_summary.json: heating scenarios with the coordinated LP")
    put("RElvLpMean", pabs(mean(shares), 1) if shares else None, "... mean gs_loss_share (saving / v10 loss)")
    put("RElvLpMin", pabs(min(shares), 1) if shares else None, "... min")
    put("RElvLpMax", pabs(max(shares), 1) if shares else None, "... max")
    plan = R11 / "PLAN.md"
    check("round-11 plan hashed", (R11 / "PLAN.sha256").exists(), "PLAN.sha256")
    # write
    n_missing = sum(v == MISSING for v in MACROS.values())
    OUT.write_text("% generated by paper/make_macros_r11.py; do not edit\n" +
                   "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in MACROS.items()), encoding="utf-8")
    L = [BEGIN + "\n", "## Round 11: claims -> artifacts -> values (generated by paper/make_macros_r11.py)\n\n",
         "| macro | value | source |\n|---|---|---|\n"]
    L += [f"| `{k}` | {v} | {SOURCES[k]} |\n" for k, v in MACROS.items()]
    L.append("\n| check | result | detail |\n|---|---|---|\n")
    L += [f"| {c} | {'PASS' if r else ('n/a' if r is None else 'FAIL')} | {d} |\n" for c, r, d in CHECKS]
    L.append(f"\nMissing values (round 11): {n_missing}\n{END}\n")
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
