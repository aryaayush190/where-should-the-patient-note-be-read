#!/usr/bin/env bash
# Local CPU runs for the pre-submission review (2026-11-09). All exploratory; resumable.
# 1) gpt-oss-20b local feasibility pilot (20 pairs); 2) 40-pair subset if the pilot is fast enough;
# 3) Qwen3-1.7B full test (capacity sweep); 4) Qwen3-4B on long cluttered notes.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_review.status
L=runtime/review_local.log
echo "local start $(date)" >> $ST
until "$OLL" list | grep -q "gpt-oss:20b"; do sleep 60; done
echo "gptoss20b pulled $(date)" >> $ST
if ! curl -s -m 10 http://127.0.0.1:11434/api/version >/dev/null; then
  LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
    "$OLL" serve >> runtime/ollama_serve6.log 2>&1 &
  sleep 15
fi
$PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_pilot --pairs pilot20 \
    --think low --max-tokens 1500 --timeout 1800 --stop-on-error >> $L 2>&1
echo "pilot20 finished $(date)" >> $ST
# continue to 40 pairs only if the pilot completed all 20 pairs with median latency <= 240 s
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
  cp results/review/LOC_gptoss20b_pilot.jsonl results/review/LOC_gptoss20b_sub40.jsonl
  $PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_sub40 --pairs sub40 \
      --think low --max-tokens 1500 --timeout 1800 --stop-on-error >> $L 2>&1
  echo "sub40 finished $(date)" >> $ST
fi
"$OLL" pull qwen3:1.7b >> runtime/pull_qwen3_1p7b.log 2>&1 && echo "qwen3:1.7b pulled $(date)" >> $ST
$PY experiments/review_runs.py zs-local --model qwen3:1.7b --name CAP_qwen3_1p7b_local --think false --json \
    --max-tokens 300 >> $L 2>&1 && echo "ok cap_1p7b $(date)" >> $ST
until [ -f results/review/long_notes_screened.json ]; do sleep 120; done
$PY experiments/review_runs.py zs-local --model qwen3:4b-instruct --name LONG_edge4b_local --notes long --json \
    --max-tokens 300 >> $L 2>&1 && echo "ok long_4b $(date)" >> $ST
echo "local_done $(date)" >> $ST
