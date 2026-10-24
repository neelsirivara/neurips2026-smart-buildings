"""Round-4 figure: per-building metric of the shipped v6 and the round-4 candidate on every generated
held-out building (the 8 old ones and the 8 fresh ones), from results/round4/confirm_<cand>.json.

    python make_figures_r4.py        -> paper/figures/fig_round4_buildings.{pdf,png}
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from make_figures import C_OURS, INK2, MUTED, plt, save
from make_macros_r4 import SHIPPED_FRESH, building_sizes

HERE = Path(__file__).resolve().parent
R4 = HERE.parent / "results" / "round4"
OLD_SIZES = {"building_0501": 25, "building_0502": 17}   # fallback zone counts (zones.npz read below when present)


def main() -> int:
    dec = json.loads((R4 / "decision.json").read_text())
    cand = dec.get("chosen")
    f = R4 / f"confirm_{cand}.json"
    if not cand or not f.exists():
        print("fig_round4_buildings: no confirmation yet")
        return 0
    S = json.loads(f.read_text())["sets"]
    rows = {}
    for s in ("old40", "fresh40"):
        for k, v in (S.get(s, {}).get("per_scenario") or {}).items():
            b = k.split("/")[0]
            r = rows.setdefault(b, {"v6": [], "cand": [], "set": s})
            r["v6"].append(v["v6"])
            r["cand"].append(v["cand"])
    sizes = {**building_sizes("r4c")}
    for b in rows:
        if b not in sizes:
            zf = sorted((HERE.parent / "results" / "mac" / "round3").glob(f"final_v6_*/{b}/*/transfer/zones.npz"))
            if zf:
                sizes[b] = {"zones": int(len(np.load(zf[0])["zone_area_m2"]))}
            else:
                sizes[b] = {"zones": OLD_SIZES.get(b, 0)}

    def group(b):
        if rows[b]["set"] == "old40":
            return 0
        return 1 if b in SHIPPED_FRESH else 2
    order = sorted(rows, key=lambda b: (group(b), sizes[b]["zones"]))
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    x = np.arange(len(order))
    for i, b in enumerate(order):
        rel = 100.0 * (np.array(rows[b]["cand"]) / np.array(rows[b]["v6"]) - 1.0)
        ax.plot(np.full(len(rel), i) + np.linspace(-0.12, 0.12, len(rel)), rel, "o", color=MUTED, markersize=2.6,
                alpha=0.8, zorder=2, label="scenario" if i == 0 else None)
        m = 100.0 * (np.mean(rows[b]["cand"]) / np.mean(rows[b]["v6"]) - 1.0)
        ax.plot([i], [m], "D", color=C_OURS, markersize=5, zorder=3, label="building mean" if i == 0 else None)
    ax.axhline(0.0, color=INK2, linewidth=0.8, zorder=1)
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("building_", "b") + "\n(" + str(sizes[b]["zones"]) + " z)" for b in order], fontsize=5.8)
    ax.set_ylabel("v7 vs v6 (% change of\nthe metric; < 0 is better)")
    ax.grid(axis="x", visible=False)
    bounds = [i for i in range(1, len(order)) if group(order[i]) != group(order[i - 1])]
    for i in bounds:
        ax.axvline(i - 0.5, color=MUTED, linewidth=0.6, linestyle=":")
    labels = {0: "old held-out (rounds 2-3)", 1: "fresh, shipped ranges", 2: "fresh, default ranges"}
    starts = [0] + bounds + [len(order)]
    ytop = ax.get_ylim()[1]
    for j in range(len(starts) - 1):
        g = group(order[starts[j]])
        ax.text((starts[j] + starts[j + 1] - 1) / 2, ytop, labels[g], ha="center", va="bottom", fontsize=6, color=INK2)
    ax.legend(fontsize=6.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    save(fig, "fig_round4_buildings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
