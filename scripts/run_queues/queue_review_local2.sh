#!/usr/bin/env bash
# Replaces queue_review_local.sh after its first gpt-oss-20b load failed (llama.cpp could not allocate a
# 10.2 GB CPU_REPACK buffer next to the 13 GB weights in 16 GB RAM). Order:
#   1) gpt-oss-20b pilot on a dedicated server with weight repacking disabled (LLAMA_ARG_NO_REPACK=1,
#      weights memory-mapped from disk); 40-pair subset if the pilot is fast enough
#   2) normal server (prompt cache off): Qwen3-1.7B full test, then Qwen3-4B on long notes
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_review.status
L=runtime/review_local.log
echo "local2 start $(date)" >> $ST
until "$OLL" list | grep -q "qwen3:1.7b"; do sleep 30; done
stop_servers() { powershell -NoProfile -Command "Get-Process ollama,llama-server -ErrorAction SilentlyContinue | Stop-Process -Force" ; sleep 5; }
stop_servers
LLAMA_ARG_NO_REPACK=1 LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
  "$OLL" serve >> runtime/ollama_serve_norepack.log 2>&1 &
sleep 15
echo "norepack server up $(date)" >> $ST
$PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_pilot --pairs pilot20 \
    --think low --max-tokens 1500 --timeout 2400 --stop-on-error >> $L 2>&1
echo "pilot20 (norepack) finished $(date)" >> $ST
GO=$($PY - <<'EOF'
import json, statistics
rows = [json.loads(l) for l in open("results/review/LOC_gptoss20b_pilot.jsonl", encoding="utf-8")]
ok = [r for r in rows if "prediction" in r]
lat = [r["latency_s"] for r in ok]
print("yes" if len(ok) >= 20 and lat and statistics.median(lat) <= 240 else "no")
EOF
)
echo "sub40 decision: $GO $(date)" >> $ST
if [ "$GO" = "yes" ]; then
  grep '"prediction"' results/review/LOC_gptoss20b_pilot.jsonl > results/review/LOC_gptoss20b_sub40.jsonl
  $PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_sub40 --pairs sub40 \
      --think low --max-tokens 1500 --timeout 2400 --stop-on-error >> $L 2>&1
  echo "sub40 finished $(date)" >> $ST
fi
stop_servers
LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
  "$OLL" serve >> runtime/ollama_serve7.log 2>&1 &
sleep 15
echo "normal server up $(date)" >> $ST
$PY experiments/review_runs.py zs-local --model qwen3:1.7b --name CAP_qwen3_1p7b_local --think false --json \
    --max-tokens 300 >> $L 2>&1 && echo "ok cap_1p7b $(date)" >> $ST
until [ -f results/review/long_notes_screened.json ]; do sleep 120; done
$PY experiments/review_runs.py zs-local --model qwen3:4b-instruct --name LONG_edge4b_local --notes long --json \
    --max-tokens 300 >> $L 2>&1 && echo "ok long_4b $(date)" >> $ST
echo "local_done $(date)" >> $ST
