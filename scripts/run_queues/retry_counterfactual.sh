#!/usr/bin/env bash
# Resume the counterfactual stress study after a Groq connection error (cached calls replay free).
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
echo "start $(date)" > runtime/retry_counterfactual.status
.venv/Scripts/python experiments/run_stress.py counterfactual --edge proxy > runtime/stress_counterfactual_proxy_retry1.log 2>&1 && echo "done $(date)" >> runtime/retry_counterfactual.status || echo "FAIL $(date)" >> runtime/retry_counterfactual.status
