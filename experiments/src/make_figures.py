"""Paper figures (matplotlib, PDF + PNG) from the result trees.

  fig_scores_by_scenario   per-scenario leaderboard score (|mean reward|), ours vs pid_water,
                           grouped by station; lower is better
  fig_station_decomp       per-station comfort / energy / carbon decomposition, ours vs pid_water
  fig_trace_<scenario>     one weekday: zone-temperature envelope vs comfort band, occupancy,
                           for ours and pid_water (two panels)
  fig_tuning               screening score of every tuned configuration (sorted) with the default

Usage:  python make_figures.py --results-dir ../results/full --scores ../results/final_scores.json \
            --trace building_train_8/fairbanks_8 --trace-day 8
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIG = ROOT / "paper" / "figures"

# Reference categorical palette (validated, fixed order): ours, pid_water, 3rd, 4th.
C_OURS, C_PID, C_THIRD, C_FOURTH = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
STATIONS = ["fairbanks", "denver", "atlanta", "phoenix", "singapore"]
COMFORT = (294.0, 297.0)
ECO = (289.0, 298.0)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 8, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "pdf.fonttype": 42,
})


def save(fig, name: str):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("wrote", FIG / f"{name}.pdf")


def _dumbbell(ax, ours: dict, base: dict, title: str, show_legend: bool):
    """Paired per-scenario scores: one dot per policy, joined by a thin line; log y."""
    keys = [k for st in STATIONS for k in sorted(ours) if k.split("/")[1].startswith(st) and k in base]
    if not keys:
        ax.set_title(title + ": no data", fontsize=8)
        return
    x = np.arange(len(keys))
    yo = np.array([ours[k]["score"] for k in keys])
    yb = np.array([base[k]["score"] for k in keys])
    ax.vlines(x, np.minimum(yo, yb), np.maximum(yo, yb), color=BASE, linewidth=1.0, zorder=1)
    ax.scatter(x, yb, s=34, color=C_PID, edgecolor="#fcfcfb", linewidth=1.0, zorder=3, label="pid_water (local re-run)")
    ax.scatter(x, yo, s=34, color=C_OURS, edgecolor="#fcfcfb", linewidth=1.0, zorder=4, label="SADR (ours)")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([k.split("/")[0].replace("building_train_", "b").replace("building_0", "g") for k in keys],
                       rotation=90, fontsize=6)
    ax.set_xlim(-0.7, len(keys) - 0.3)
    ymin, ymax = min(yo.min(), yb.min()), max(yo.max(), yb.max())
    ax.set_ylim(ymin / 1.6, ymax * 2.2)
    bounds = []
    for st in STATIONS:
        idx = [i for i, k in enumerate(keys) if k.split("/")[1].startswith(st)]
        if idx:
            bounds.append((st, min(idx), max(idx)))
    for st, lo, hi in bounds:
        ax.text((lo + hi) / 2, ymax * 1.9, st.capitalize(), ha="center", va="top", fontsize=6.5, color=INK2)
        if hi + 1 < len(keys):
            ax.axvline(hi + 0.5, color=GRID, linewidth=0.6, zorder=0)
    ax.grid(axis="x", visible=False)
    ax.set_title(title, fontsize=8, loc="left", color=INK)
    if show_legend:
        ax.legend(loc="lower left", fontsize=6.5, ncol=1, handletextpad=0.3, borderaxespad=0.2)


def fig_scores(scores: dict, held: dict | None = None):
    pol = scores["policies"]
    ours = pol.get("transfer", {}).get("per_scenario", {})
    base = pol.get("pid_water", {}).get("per_scenario") or pol.get("pid_water_official", {}).get("per_scenario", {})
    if not ours or not base:
        print("fig_scores: missing data")
        return
    hours = (held or {}).get("policies", {}).get("transfer", {}).get("per_scenario", {})
    hbase = (held or {}).get("policies", {}).get("pid_water", {}).get("per_scenario", {})
    two = bool(hours and hbase)
    if two:
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5), sharey=True,
                                 gridspec_kw={"width_ratios": [len(ours), max(len(hours), 4)], "wspace": 0.06})
        _dumbbell(axes[0], ours, base, "30 public scenarios", True)
        _dumbbell(axes[1], hours, hbase, f"{len(hours)} held-out scenarios (generated buildings)", False)
        axes[1].tick_params(axis="y", length=0)
        ax0 = axes[0]
    else:
        fig, ax0 = plt.subplots(figsize=(7.0, 2.5))
        _dumbbell(ax0, ours, base, "30 public scenarios", True)
    ax0.set_ylabel("|mean per-step reward|\n(log scale, lower is better)")
    save(fig, "fig_scores_by_scenario")


def fig_decomp(scores: dict):
    pol = scores["policies"]
    ours = pol.get("transfer", {})
    base = pol.get("pid_water", {})
    if "decomp_by_station" not in ours or "decomp_by_station" not in base:
        print("fig_decomp: missing local decomposition")
        return
    fig, ax = plt.subplots(figsize=(5.2, 2.4))
    x = np.arange(len(STATIONS))
    w = 0.38
    comps = [("comfort", C_THIRD), ("energy", C_OURS), ("carbon", C_FOURTH)]
    for off, d, lab in ((-w / 2, ours, "SADR"), (w / 2, base, "pid_water")):
        bottom = np.zeros(len(STATIONS))
        for comp, col in comps:
            vals = np.array([d["decomp_by_station"].get(st, {}).get(comp, 0.0) for st in STATIONS])
            ax.bar(x + off, vals, w, bottom=bottom, color=col, linewidth=0.8, edgecolor="#fcfcfb",
                   label=comp if lab == "SADR" else None)
            bottom += vals
        for xi, b in zip(x + off, bottom):
            ax.text(xi, b, lab, ha="center", va="bottom", fontsize=5.5, color=INK2, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in STATIONS])
    ax.set_ylabel("per-step loss (metric units)")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=7, ncol=3, loc="upper right")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    save(fig, "fig_station_decomp")


def fig_trace(results_dir: Path, scen: str, day: int, policies=("transfer", "pid_water")):
    fig, axes = plt.subplots(1, len(policies), figsize=(7.0, 2.3), sharey=True)
    axes = np.atleast_1d(axes)
    titles = {"transfer": "SADR (ours)", "pid_water": "pid_water"}
    any_ok = False
    for ax, pol in zip(axes, policies):
        f = results_dir / scen / pol / "timeseries.csv"
        if not f.exists():
            ax.set_title(f"{titles.get(pol, pol)}: no timeseries", fontsize=8)
            continue
        any_ok = True
        ts = pd.read_csv(f, parse_dates=["timestamp"])
        zcols = [c for c in ts.columns if c.startswith("zone_") and c.endswith("_temp")]
        d0 = ts.timestamp.iloc[0].normalize() + pd.Timedelta(days=day)
        sel = ts[(ts.timestamp >= d0) & (ts.timestamp < d0 + pd.Timedelta(days=1))]
        if sel.empty:
            continue
        hours = (sel.timestamp - d0).dt.total_seconds() / 3600.0
        Z = sel[zcols].values
        hod = hours.values
        wd = d0.dayofweek < 5
        band_lo = np.where((hod >= 6) & (hod < 19) & wd, COMFORT[0], ECO[0])
        band_hi = np.where((hod >= 6) & (hod < 19) & wd, COMFORT[1], ECO[1])
        ax.fill_between(hod, band_lo, band_hi, color=C_THIRD, alpha=0.12, linewidth=0, label="comfort band")
        ax.fill_between(hod, Z.min(axis=1), Z.max(axis=1), color=C_OURS if pol == "transfer" else C_PID,
                        alpha=0.18, linewidth=0, label="zone min-max")
        ax.plot(hod, np.median(Z, axis=1), color=C_OURS if pol == "transfer" else C_PID, linewidth=2,
                solid_capstyle="round", label="zone median")
        occ = sel.occupancy.values
        if occ.max() > 0:
            ax2 = ax.twinx()
            ax2.fill_between(hod, 0, occ, color=MUTED, alpha=0.15, linewidth=0, step="mid")
            ax2.set_ylim(0, occ.max() * 4)
            ax2.set_yticks([])
            ax2.spines["right"].set_visible(False)
        ax.set_title(f"{titles.get(pol, pol)} - {scen.replace('_', chr(92) + '_')}, day {day} ({d0.strftime('%a %Y-%m-%d')})"
                     .replace(chr(92) + "_", "_"), fontsize=7.5)
        ax.set_xlabel("hour of day")
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
    axes[0].set_ylabel("zone temperature (K)")
    axes[0].legend(fontsize=6.5, loc="lower left", ncol=1)
    if any_ok:
        save(fig, f"fig_trace_{scen.replace('/', '_')}_day{day}")
    else:
        plt.close(fig)


def fig_loss_by_hour(analysis: Path):
    """Mean per-step loss by hour of day (metric units), ours vs pid_water, split into comfort
    regret and energy+carbon; mean over the scenarios in analysis.json."""
    if not analysis.exists():
        print("fig_loss_by_hour: no analysis.json")
        return
    an = json.loads(analysis.read_text())
    means = an.get("means", {})
    if "transfer" not in means or "pid_water" not in means or not means["transfer"].get("loss_by_hour"):
        print("fig_loss_by_hour: incomplete")
        return
    hours = np.arange(24) + 0.5
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.2), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, (pol, col, lab) in zip(axes, (("transfer", C_OURS, "SADR (ours)"), ("pid_water", C_PID, "pid_water"))):
        tot = np.array(means[pol]["loss_by_hour"])
        reg = np.array(means[pol]["regret_by_hour"])
        ax.fill_between(hours, 0, tot, step="mid", color=col, alpha=0.22, linewidth=0, label="energy + carbon")
        ax.fill_between(hours, 0, reg, step="mid", color=C_THIRD, alpha=0.55, linewidth=0, label="comfort regret")
        ax.step(hours, tot, where="mid", color=col, linewidth=1.8, label="total")
        ax.axvspan(6, 19, color=MUTED, alpha=0.07, linewidth=0)
        ax.set_title(f"{lab} (n={an['n_scenarios']} scenarios)", fontsize=8, loc="left", color=INK)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xlabel("hour of day")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("mean loss per step\n(metric units)")
    axes[0].legend(fontsize=6.5, loc="upper left")
    axes[1].tick_params(axis="y", length=0)
    save(fig, "fig_loss_by_hour")


def fig_tuning(tune_log: Path, baseline_agg: Path | None = None):
    if not tune_log.exists():
        print("fig_tuning: no tune log")
        return
    log = json.loads(tune_log.read_text())
    rows = [(v["score"], v.get("is_default", False)) for v in log["evals"].values() if "score" in v]
    if not rows:
        return
    rows.sort()
    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    sc = [r[0] for r in rows]
    cols = [C_PID if r[1] else C_OURS for r in rows]
    ax.bar(np.arange(len(sc)), sc, color=cols, linewidth=0.8, edgecolor="#fcfcfb", width=0.85)
    ax.set_xlabel("configuration (sorted by screening score)")
    ax.set_ylabel("screening score\n(6 scenarios, 5 days)")
    ax.set_xticks([])
    ax.grid(axis="x", visible=False)
    handles = []
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    handles.append(Patch(color=C_OURS, label="searched configuration"))
    if any(r[1] for r in rows):
        handles.append(Patch(color=C_PID, label="default parameters"))
    ref = None
    if baseline_agg is not None and baseline_agg.exists():
        agg = json.loads(baseline_agg.read_text())
        if agg.get("n_scenarios") == 6 and agg.get("leaderboard_metric"):
            ref = float(agg["leaderboard_metric"])
    if ref is not None:
        ax.axhline(ref, color=INK2, linewidth=1.2, linestyle=(0, (4, 2)))
        ax.text(len(sc) - 0.5, ref, f"pid_water {ref:.4f}", ha="right", va="bottom", fontsize=6.5, color=INK2)
        handles.append(Line2D([0], [0], color=INK2, linewidth=1.2, linestyle=(0, (4, 2)), label="pid_water, same runs"))
        ax.set_ylim(0, ref * 1.25)
    ax.legend(handles=handles, fontsize=6.5, loc="upper left")
    save(fig, "fig_tuning")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="../results/full")
    ap.add_argument("--scores", default="../results/final_scores.json")
    ap.add_argument("--trace", nargs="*", default=[])
    ap.add_argument("--trace-day", type=int, default=1)
    ap.add_argument("--tune-log", default="../results/tune/tune_log.json")
    ap.add_argument("--tune-baseline", default="../results/tune_baseline/pid_water__agg.json")
    ap.add_argument("--held-scores", default="../results/heldout_scores.json")
    ap.add_argument("--analysis", default="../results/analysis.json")
    a = ap.parse_args()
    rd = (HERE / a.results_dir).resolve() if not Path(a.results_dir).is_absolute() else Path(a.results_dir)
    sp = (HERE / a.scores).resolve() if not Path(a.scores).is_absolute() else Path(a.scores)
    hp = (HERE / a.held_scores).resolve() if not Path(a.held_scores).is_absolute() else Path(a.held_scores)
    held = json.loads(hp.read_text()) if hp.exists() else None
    if sp.exists():
        scores = json.loads(sp.read_text())
        fig_scores(scores, held)
        fig_decomp(scores)
    else:
        print("no scores json yet:", sp)
    for scen in a.trace:
        fig_trace(rd, scen, a.trace_day)
    tl = (HERE / a.tune_log).resolve() if not Path(a.tune_log).is_absolute() else Path(a.tune_log)
    ba = (HERE / a.tune_baseline).resolve() if not Path(a.tune_baseline).is_absolute() else Path(a.tune_baseline)
    fig_tuning(tl, ba)
    an = (HERE / a.analysis).resolve() if not Path(a.analysis).is_absolute() else Path(a.analysis)
    fig_loss_by_hour(an)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
