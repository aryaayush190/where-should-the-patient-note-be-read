#!/usr/bin/env bash
# Local-model queue (CPU, Qwen3-4B via Ollama). Starts its own Ollama server with the
# llama-server prompt cache disabled (it otherwise fills RAM). Resumable.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
echo "start $(date)" > runtime/queue_local.status
LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
  "$OLL" serve >> runtime/ollama_serve3.log 2>&1 &
sleep 15
"$OLL" --version >> runtime/queue_local.status 2>&1
$PY experiments/run_splitmatch.py --split test --edge local --name TEST_deploy >> runtime/TEST_deploy.log 2>&1 || echo "FAIL TEST_deploy" >> runtime/queue_local.status
echo "TEST_deploy finished $(date)" >> runtime/queue_local.status
$PY experiments/fresh_checks.py extraction --edge local > runtime/fresh_extraction_local.log 2>&1 || echo "FAIL fresh" >> runtime/queue_local.status
$PY experiments/run_zero_shot.py --split test --where local --name ZS_edge_qwen4b_test > runtime/zs_edge_test.log 2>&1 || echo "FAIL zs_edge" >> runtime/queue_local.status
SPLITMATCH_MODE=dev $PY experiments/run_splitmatch.py --split dev_validation --edge local --name dev_val_LOCAL_v9 > runtime/dev_val_local_v9.log 2>&1 || echo "FAIL devval" >> runtime/queue_local.status
echo "done $(date)" >> runtime/queue_local.status
