# Job queues used for the study

These are the exact queues that produced the released outputs, kept for transparency. They were run detached under Git Bash on Windows and contain machine-specific paths (the Ollama executable); adapt them before reuse. Each queue writes a status file to `runtime/` and is resumable: steps skip pairs that already have a prediction.

| Script | Runs |
|---|---|
| `queue_groq.sh`, `queue_local.sh` | First test-set queues: the laptop SPLIT-Match run (`TEST_deploy`), proxy run, compilation |
| `queue_final.sh` | Noisy-note stress test, development replication, Qwen3-4B full-note runs on test and development |
| `retry_redaction.sh`, `retry_counterfactual.sh` | Resumed stress tests after interruptions |
| `resume_devval_local.sh` | Resumed laptop development validation |
| `queue_review_groq.sh`, `queue_review_local.sh`, `queue_review_local2.sh` | Hosted repeats (noise floor), capacity points, long notes, laptop gpt-oss-20b pilot and 40-pair subset |
| `queue_local20b_full.sh` | gpt-oss-20b reading the note on the laptop, all 270 pairs (weights memory-mapped: `LLAMA_ARG_NO_REPACK=1`) |
| `queue_round5_local.sh` | Qwen3-4B deciding from its fact sheets; fresh laptop repeats of Qwen3-4B and gpt-oss-20b |
| `keep_awake_until_done.ps1` | Keeps Windows from idle-sleeping until a queue writes its done marker |
