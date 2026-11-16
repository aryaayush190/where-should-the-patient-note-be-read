#!/usr/bin/env bash
# Pre-submission review, round 2 (2026-11-09): gpt-oss-20b reading the full note ON THE LAPTOP for all
# 270 test pairs, with the same prompt and settings as the hosted runs and the 40-pair local subset.
# The 40 pairs already run locally replay from runtime/review_cache (identical requests), so only 230 are new.
# Resumable: rerunning this script skips pairs that already have a prediction.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_review.status
L=runtime/review_local20b_full.log
stop_servers() { powershell -NoProfile -Command "Get-Process ollama,llama-server -ErrorAction SilentlyContinue | Stop-Process -Force" ; sleep 5; }
echo "full20b start $(date)" >> $ST
stop_servers
# weights memory-mapped (the default load needs a 10.2 GB repack buffer that does not fit in 16 GB)
LLAMA_ARG_NO_REPACK=1 LLAMA_ARG_CACHE_RAM=0 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 \
  OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=120m \
  "$OLL" serve >> runtime/ollama_serve_norepack2.log 2>&1 &
sleep 15
echo "norepack server up $(date)" >> $ST
for attempt in 1 2 3; do
  $PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_test \
      --think low --max-tokens 1500 --timeout 2400 >> $L 2>&1
  n=$(grep -c '"prediction"' results/review/LOC_gptoss20b_test.jsonl 2>/dev/null || echo 0)
  echo "full20b pass $attempt done: $n/270 predictions $(date)" >> $ST
  [ "$n" -ge 270 ] && break
  # error rows are retried on the next pass (done_keys counts only rows with a prediction)
  stop_servers
  LLAMA_ARG_NO_REPACK=1 LLAMA_ARG_CACHE_RAM=0 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=120m \
    "$OLL" serve >> runtime/ollama_serve_norepack2.log 2>&1 &
  sleep 15
done
stop_servers
echo "full20b_done $(date)" >> $ST
