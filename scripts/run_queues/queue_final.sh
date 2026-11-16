#!/usr/bin/env bash
# Final queue (user instruction 2026-11-09: start the remaining runs after 45 min, then
# complete all of them). Two sub-queues run in parallel: Groq (network) and local CPU.
# Every job is resumable: completed model calls replay from the response cache.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_final.status
echo "scheduled $(date); sleeping 2700 s" > $ST
sleep 2700
echo "start $(date)" >> $ST

# Retry a job up to 3 times (Groq connection drops have killed runs before).
retry() { local tag=$1; shift; for i in 1 2 3; do "$@" && { echo "ok $tag $(date)" >> $ST; return 0; }; echo "retry $tag #$i $(date)" >> $ST; sleep 120; done; echo "FAIL $tag $(date)" >> $ST; }

groq_q() {
  retry noisy        sh -c "$PY experiments/run_stress.py noisy --edge proxy >> runtime/stress_noisy_proxy.log 2>&1"
  retry dev_edge20b  sh -c "$PY experiments/run_replication_dev.py >> runtime/replication_dev_20b.log 2>&1"
  echo "groq_done $(date)" >> $ST
}

local_q() {
  # Reuse the running Ollama server (prompt cache disabled) if it answers; else start one.
  if ! curl -s -m 10 http://127.0.0.1:11434/api/version >/dev/null; then
    LLAMA_ARG_CACHE_RAM=0 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m \
      "$OLL" serve >> runtime/ollama_serve4.log 2>&1 &
    sleep 15
  fi
  "$OLL" --version >> $ST 2>&1
  retry zs4b_test    sh -c "$PY experiments/run_zero_shot.py --split test --where local --name ZS_edge_qwen4b_test >> runtime/zs_edge_test.log 2>&1"
  retry fresh_local  sh -c "$PY experiments/fresh_checks.py extraction --edge local >> runtime/fresh_extraction_local.log 2>&1"
  retry zs4b_dev     sh -c "$PY experiments/run_zero_shot.py --split dev --where local --name ZS_edge_qwen4b_dev >> runtime/zs_edge_dev.log 2>&1"
  retry devval_local sh -c "SPLITMATCH_MODE=dev $PY experiments/run_splitmatch.py --split dev_validation --edge local --name dev_val_LOCAL_v9 >> runtime/dev_val_local_v9.log 2>&1"
  echo "local_done $(date)" >> $ST
}

groq_q &
local_q &
wait
echo "done $(date)" >> $ST
