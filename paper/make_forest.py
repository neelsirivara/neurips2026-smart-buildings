"""Forest plot of the leave-one-out ablation (Table tab:ablation12), grouped by the three design facts.

    python paper/make_forest.py      # reads paper/table_ablation_final.tex, writes paper/figures/fig_ablation_forest.pdf/.png

The numbers come from the table itself (one source of truth); the grouping is the paper's Section 2 design facts.
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
TAB = HERE / "table_ablation_final.tex"

# design fact of each mechanism (Section 2): 1 idle and start late, 2 heat only through reheat, 3 fan and coldest air
GROUP = {
    "per-zone optimum start": 1, "setback floor limited to what the zone recovers": 1, "deeper weekend setback": 1,
    "set-back air boost": 1, "model-based starts": 1, "day of week rounded after decoding": 1,
    "zone gains scaled with zone area": 2, "requests capped at the coil's delivery": 2,
    "350\\,K hot water in heating season (arm: 330\\,K)": 2, "set-back forced air reheated to zone temperature": 2,
    "request cap 20\\,kW per 100\\,m$^2$ (arm: 12\\,kW)": 2, "7-day heating season below 15\\,$^\\circ$C": 2,
    "coldest supply air (arm: upward reset, ceiling 293\\,K)": 3, "economizer": 3, "night flush": 3,
    "occupied flow in proportion to the error": 3,
}
TITLE = {1: "(1) comfort is free while empty", 2: "(2) heat enters only through reheat", 3: "(3) fan power and coldest air"}
COLOR = {1: "#2a6f97", 2: "#c2571a", 3: "#4a7c3a"}


def pct(s):
    return float(s.replace("$", "").replace("\\%", "").replace("+", "").replace("-", "-").strip())


def plain(label):
    s = label.replace("\\,", " ").replace("$^2$", "²").replace("$^\\circ$", "°")
    return re.sub(r"\s+", " ", s).strip()


def rows():
    out = []
    for line in TAB.read_text(encoding="utf-8").splitlines():
        if line.count("&") != 5 or line.startswith("mechanism"):
            continue
        name, _loss, change, _cl, _wl, _terms = [c.strip() for c in line.rstrip("\\ ").split("&")]
        m = re.match(r"(.+?)\s*\[(.+?),\s*(.+?)\]", change)
        out.append((name, pct(m.group(1)), pct(m.group(2)), pct(m.group(3))))
    return out


def main():
    data = rows()
    assert len(data) == len(GROUP) and all(n in GROUP for n, *_ in data), [n for n, *_ in data if n not in GROUP]
    order = []
    for g in (1, 2, 3):
        order += [("hdr", g)] + [("row", r) for r in sorted([r for r in data if GROUP[r[0]] == g], key=lambda r: -r[1])]
    fig, ax = plt.subplots(figsize=(6.6, 0.24 * len(order) + 0.5))
    y = len(order)
    yt, yl = [], []
    for kind, v in order:
        y -= 1
        if kind == "hdr":
            ax.text(0.3, y, TITLE[v], fontsize=8, fontweight="bold", color=COLOR[v], va="center", ha="left")
            continue
        name, m, lo, hi = v
        g = GROUP[name]
        ax.plot([lo, hi], [y, y], color=COLOR[g], lw=1.4)
        ax.plot([m], [y], "o", color=COLOR[g], ms=3.5)
        yt.append(y)
        yl.append(plain(name))
    ax.axvline(0, color="0.4", lw=0.7, ls="--")
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=7)
    ax.set_xlim(-1.6, 14)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlabel("loss increase without the mechanism (%, 95% CI)", fontsize=8)
    ax.tick_params(axis="x", labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    out = HERE / "figures" / "fig_ablation_forest"
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=200)
    print(out.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
