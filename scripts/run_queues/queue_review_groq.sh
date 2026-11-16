#!/usr/bin/env bash
# Hosted (Groq) runs for the pre-submission review (2026-11-09). All exploratory; resumable.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
ST=runtime/queue_review.status
L=runtime/review_groq.log
retry() { local tag=$1; shift; for i in 1 2 3; do "$@" && { echo "ok $tag $(date)" >> $ST; return 0; }; echo "retry $tag #$i $(date)" >> $ST; sleep 90; done; echo "FAIL $tag $(date)" >> $ST; }
echo "groq start $(date)" >> $ST
retry rec_deploy  sh -c "$PY experiments/run_record_cloud.py --split test --factsheets-from TEST_deploy --name REC_cloud_test_deploy >> $L 2>&1"
retry nf_cloud    sh -c "$PY experiments/review_runs.py zs-groq --model openai/gpt-oss-120b --name NF_cloud120b --reps 3 --nocache >> $L 2>&1"
retry nf_edge20b  sh -c "$PY experiments/review_runs.py zs-groq --model openai/gpt-oss-20b --name NF_edge20b --reps 3 --nocache >> $L 2>&1"
retry cap_qwen27  sh -c "$PY experiments/review_runs.py zs-groq --model qwen/qwen3.8-27b --name CAP_qwen27b >> $L 2>&1"
retry render_long sh -c "$PY experiments/review_runs.py render-long >> $L 2>&1"
retry screen_long sh -c "$PY experiments/review_runs.py screen-long >> $L 2>&1"
retry long_cloud  sh -c "$PY experiments/review_runs.py zs-groq --model openai/gpt-oss-120b --name LONG_cloud120b --notes long >> $L 2>&1"
retry long_edge20b sh -c "$PY experiments/review_runs.py zs-groq --model openai/gpt-oss-20b --name LONG_edge20b --notes long >> $L 2>&1"
echo "groq_done $(date)" >> $ST
