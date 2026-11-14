"""Round 12: frost exposure of the CMA mean on HS (reported before shipping, PLAN.md). Compares with v12 (ab12_ref)."""
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "paper"))
import cma_r12 as c  # noqa: E402
import make_macros_r11 as m  # noqa: E402

V = "r12cand"
for _ in range(60):
    n = c.ssh(f"ls {c.MAC_ROOT}/out/runs/{V}/r6hs/*/*/transfer/summary.json 2>/dev/null | wc -l").stdout.decode().strip()
    if n.isdigit() and int(n) >= 18:
        break
    time.sleep(120)
r = c.ssh(f"cd {c.MAC_ROOT}/out/runs && find ./{V}/r6hs -type f | tar cf - -T -", timeout=600)
with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
    for mem in tf.getmembers():
        name = mem.name.lstrip("./")
        if mem.isfile() and ".." not in Path(name).parts:
            dst = c.RUNS / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(tf.extractfile(mem).read())
cand = m.summaries(f"round6/runs/{V}/r6hs/*/*/transfer/summary.json")
ref = m.summaries("round6/runs/ab12_ref/r6hs/*/*/transfer/summary.json")
tc, bc, nc = m.coldest(cand)
tr, br, nr = m.coldest(ref)
loss_c = sum(abs(s["avg_reward"]) for s in cand.values()) / len(cand)
loss_r = sum(abs(s["avg_reward"]) for s in ref.values()) / len(ref)
out = {"n_cand": len(cand), "n_ts_cand": nc, "n_ts_ref": nr,
       "coldest_c_cand": tc - 273.15 if tc else None, "coldest_c_v12": tr - 273.15 if tr else None,
       "below5_cand": bc, "below5_v12": br, "hs_loss_ratio": loss_c / loss_r}
(c.R12 / "frost.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
