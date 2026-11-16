#!/usr/bin/env bash
# Resume the last job of scripts/queue_final.sh (local dev_validation), which died at ~07:02
# on 2026-11-09 when the session ended. Fact sheets and model calls already done replay
# from results/runs/dev_val_LOCAL_v9 and runtime/llm_cache.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_final.status
echo "resume devval_local $(date)" >> $ST
if ! curl -s -m 10 http://127.0.0.1:11434/api/version >/dev/null; then
  LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
    "$OLL" serve >> runtime/ollama_serve5.log 2>&1 &
  sleep 15
fi
for i in 1 2 3; do
  SPLITMATCH_MODE=dev OLLAMA_URL=http://127.0.0.1:11434 $PY experiments/run_splitmatch.py \
    --split dev_validation --edge local --name dev_val_LOCAL_v9 >> runtime/dev_val_local_v9.log 2>&1 \
    && { echo "ok devval_local $(date)" >> $ST; echo "local_done $(date)" >> $ST; exit 0; }
  echo "retry devval_local #$i $(date)" >> $ST; sleep 120
done
echo "FAIL devval_local $(date)" >> $ST
