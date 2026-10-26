#!/usr/bin/env bash
# Round 5: wait until the given Kaggle kernels finish, then download each one's output (log + submission.parquet)
# into submission/kaggle/<slug>/run_v<version>/.   Usage: kaggle_wait_kernels.sh <version> <slug> [<slug> ...]
K="$USERPROFILE/.kaggle-cli-venv/Scripts/kaggle.exe"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ver=$1; shift
pending=("$@")
while [ ${#pending[@]} -gt 0 ]; do
  next=()
  for s in "${pending[@]}"; do
    st=$("$K" kernels status neelsiri/$s 2>&1 | tail -1)
    case "$st" in
      *COMPLETE*|*ERROR*|*CANCEL*)
        out="$ROOT/submission/kaggle/$s/run_v$ver"; mkdir -p "$out"
        "$K" kernels output neelsiri/$s -p "$out" > "$out/download.txt" 2>&1
        echo "$(date -u +%FT%TZ) $s: $st"; grep -h "gateway\]" "$out"/*.log 2>/dev/null | tail -3 ;;
      *) next+=("$s") ;;
    esac
  done
  pending=("${next[@]}")
  [ ${#pending[@]} -gt 0 ] && sleep 60
done
echo "all done"
