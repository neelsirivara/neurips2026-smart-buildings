"""Round 6: fetch Mac batches (mac_shard_runner_r6.py) into the same tree as the Kaggle shards.

    python fetch_mac_r6.py mac-screen-a [mac-screen-b ...]

Copies ~/neurips/sb/r6/out/<batch>/{results,progress.jsonl,runner_log.txt,logs} to results/round6/mac_out/<batch>/
(tar over ssh) and merges results/<tag>/... into results/round6/runs/<tag>/... (8,640-step summaries only, same
layout as kaggle_sim.py fetch). Records the batch in results/round6/mac_registry.json.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import io
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R6 = ROOT / "experiments" / "results" / "round6"
OUT = R6 / "mac_out"
RUNS = R6 / "runs"
REG = R6 / "mac_registry.json"


def fetch(batch: str) -> dict:
    remote = f"cd ~/neurips/sb/r6/out/{batch} && tar czf - results progress.jsonl runner_log.txt logs 2>/dev/null"
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "mac", remote], capture_output=True)
    if not r.stdout:
        raise SystemExit(f"{batch}: nothing fetched ({r.stderr.decode(errors='replace')[-300:]})")
    od = OUT / batch
    od.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout), mode="r:gz") as tf:
        for m in tf.getmembers():
            if m.name.startswith("/") or ".." in Path(m.name).parts or not (m.isfile() or m.isdir()):
                continue
            tf.extract(m, od)
    n = 0
    res = od / "results"
    if res.exists():
        for f in res.rglob("summary.json"):
            s = json.loads(f.read_text())
            if s.get("total_steps") != 8640:
                continue
            dst_dir = RUNS / f.parent.relative_to(res)
            dst_dir.mkdir(parents=True, exist_ok=True)
            for g in f.parent.iterdir():
                if g.is_file():
                    shutil.copyfile(g, dst_dir / g.name)
            n += 1
    prog = od / "progress.jsonl"
    rows = [json.loads(x) for x in prog.read_text().splitlines()] if prog.exists() else []
    log = (od / "runner_log.txt").read_text() if (od / "runner_log.txt").exists() else ""
    entry = {"batch": batch, "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "n_summaries_merged": n, "n_progress": len(rows), "n_failed": sum(1 for x in rows if not x.get("ok")),
             "all_done": "all done" in log}
    reg = json.loads(REG.read_text()) if REG.exists() else {}
    reg[batch] = entry
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1))
    os.replace(tmp, REG)
    print(json.dumps(entry))
    return entry


if __name__ == "__main__":
    for b in sys.argv[1:]:
        fetch(b)
