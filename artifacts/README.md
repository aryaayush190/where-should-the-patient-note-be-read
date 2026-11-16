# Artifacts

Compressed runtime files needed to regenerate every number and to replay the experiments without API keys. Unpack them with

```bash
python scripts/restore_artifacts.py   # -> runtime/ (git-ignored)
```

| File | Unpacked to | Content |
|---|---|---|
| `llm_calls.jsonl.gz` (≈106 MB unpacked) | `runtime/llm_calls.jsonl` | One record per model call: channel (`cloud_public`, `cloud_fact`, `edge_local`, `edge_proxy`, `baseline_cloud`), model, run, timings, disclosed fields, and the verbatim payload of every call that left (or would leave) the device. Used for the privacy audit (H2), the gateway suite and the re-identification simulation |
| `llm_cache.tar.gz` | `runtime/llm_cache/` | Replies keyed by a hash of the full request, so an identical re-run replays them |
| `review_cache.tar.gz` | `runtime/review_cache/` | Replies of the review runs (`experiments/review_runs.py`), keyed the same way |
| `TEST_deploy.log.gz` | `runtime/TEST_deploy.log` | Log of the laptop SPLIT-Match run; supplies the laptop-judge timings |

All patients in these files are synthetic. No API keys are included; key prefixes printed in rate-limit warnings were redacted from the log.
