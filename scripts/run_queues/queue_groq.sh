#!/usr/bin/env bash
# Groq-only queue (cloud stand-in edge). Resumable: re-running skips cached calls/files.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
PY=.venv/Scripts/python
echo "start $(date)" > runtime/queue_groq.status
$PY experiments/run_ablations.py --only AB_single AB_noverify AB_nocompiler >> runtime/ablations_test.log 2>&1 || echo "FAIL ablations" >> runtime/queue_groq.status
for s in redaction counterfactual noisy; do
  $PY experiments/run_stress.py $s --edge proxy > runtime/stress_${s}_proxy.log 2>&1 || echo "FAIL $s" >> runtime/queue_groq.status
done
echo "done $(date)" >> runtime/queue_groq.status
