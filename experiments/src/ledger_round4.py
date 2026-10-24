"""Merge the round-4 notes, screen summaries and full-length comparisons into results/round4/candidates.json.

Inputs: candidates_notes_r4.json (hand-written: change, hypothesis, family),
        results/round4/screen_summary_screen_vs_r4_c00_v6.json (screen_round4.py summarize),
        results/round4/decision.json (the choice made under the pre-registered rule, written by hand
        from the screen summary and checked here), results/round4/confirm_<cand>.json (confirm_round4.py).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R4 = HERE.parent / "results" / "round4"


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def slim(d):
    if not d:
        return None
    return {k: d[k] for k in ("n", "n_paired", "metric", "ref_metric", "diff", "ratio", "ci_lo", "ci_hi", "wins", "losses") if k in d}


def main() -> int:
    notes = load(HERE / "candidates_notes_r4.json")
    ss = load(R4 / "screen_summary_screen_vs_r4_c00_v6.json") or {"rows": []}
    dec = load(R4 / "decision.json") or {}
    rows = {r["name"]: r for r in ss["rows"]}
    out = {"doc": notes["doc"], "code": notes["code"], "prereg": "results/round4/PREREG.md",
           "screen_steps": ss.get("steps"), "screen_sets": ss.get("sets"), "decision": dec, "candidates": {}}
    names = list(notes["candidates"]) + [n for n in rows if n not in notes["candidates"]]
    for n in names:
        e = dict(notes["candidates"].get(n, {}))
        r = rows.get(n)
        if r:
            e["screen"] = {"class_vs_c00": r.get("class"), "complete": r.get("complete"),
                           "public": slim(r.get("public")), "held": slim(r.get("held")),
                           "held_old6": slim(r.get("held_old6")), "held_new20": slim(r.get("held_new20"))}
        c = load(R4 / f"confirm_{n}.json")
        if c:
            e["full_length_vs_v6"] = {k: {kk: v[kk] for kk in ("n", "cand", "v6", "diff", "rel", "ci_lo", "ci_hi", "rel_ci_lo", "rel_ci_hi", "wins", "losses") if kk in v}
                                      for k, v in c["sets"].items() if v.get("n")}
            e["ship_rule_met"] = c.get("ship_rule_met")
        out["candidates"][n] = e
    (R4 / "candidates.json").write_text(json.dumps(out, indent=1))
    print(f"-> {R4 / 'candidates.json'} ({len(out['candidates'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
