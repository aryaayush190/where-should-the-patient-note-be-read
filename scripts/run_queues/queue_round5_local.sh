#!/usr/bin/env bash
# Round-5 review (2026-11-10): laptop runs that address the reviewer's ablation and benchmarking flags.
#   1) Qwen3-4B decides from its own SPLIT-Match fact sheets (TEST_deploy), no rules: separates the
#      fact-sheet representation from the rule layer at a fixed device model (run_record_cloud --decider edge_local)
#   2) Qwen3-4B full-note zero-shot, fresh repeat of all 270 pairs (no cache): latency distribution,
#      cold-start load time, peak memory and decision stability of the laptop result
#   3) gpt-oss-20b full-note zero-shot, fresh repeat of the 40-pair stratified subset (no cache, no-repack server)
# Resumable: every step skips pairs that already have a prediction (step 1 replays its call cache).
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
OLL="C:/Users/aryaa/AppData/Local/Programs/Ollama/ollama.exe"
ST=runtime/queue_round5.status
L=runtime/queue_round5_local.log
stop_servers() { powershell -NoProfile -Command "Get-Process ollama,llama-server -ErrorAction SilentlyContinue | Stop-Process -Force" ; sleep 5; }
echo "round5 start $(date)" >> $ST
"$OLL" --version >> $ST 2>&1
stop_servers
LLAMA_ARG_CACHE_RAM=0 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_KEEP_ALIVE=60m "$OLL" serve >> runtime/ollama_serve_round5.log 2>&1 &
sleep 15
echo "normal server up $(date)" >> $ST
for attempt in 1 2; do
  $PY experiments/run_record_cloud.py --split test --factsheets-from TEST_deploy --name REC_edge4b_test_deploy \
      --decider edge_local >> $L 2>&1 && { echo "ok rec_edge4b $(date)" >> $ST; break; }
  echo "rec_edge4b attempt $attempt failed $(date)" >> $ST
done
$PY experiments/review_runs.py zs-local --model qwen3:4b-instruct --name LOC_qwen4b_test_rep1 --json \
    --max-tokens 300 --nocache --rep 1 >> $L 2>&1
echo "4b rep1 done: $(grep -c '"prediction"' results/review/LOC_qwen4b_test_rep1.jsonl) $(date)" >> $ST
stop_servers
LLAMA_ARG_NO_REPACK=1 LLAMA_ARG_CACHE_RAM=0 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 \
  OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=120m "$OLL" serve >> runtime/ollama_serve_round5_norepack.log 2>&1 &
sleep 15
echo "norepack server up $(date)" >> $ST
for attempt in 1 2; do
  $PY experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_sub40_rep1 --pairs sub40 \
      --think low --max-tokens 1500 --timeout 2400 --nocache --rep 1 >> $L 2>&1
  n=$(grep -c '"prediction"' results/review/LOC_gptoss20b_sub40_rep1.jsonl 2>/dev/null || echo 0)
  echo "20b sub40 rep1 pass $attempt: $n/40 $(date)" >> $ST
  [ "$n" -ge 40 ] && break
done
"$OLL" show qwen3:4b-instruct >> $ST 2>&1
"$OLL" show gpt-oss:20b >> $ST 2>&1
"$OLL" show qwen3:1.7b >> $ST 2>&1
stop_servers
echo "round5_done $(date)" >> $ST
