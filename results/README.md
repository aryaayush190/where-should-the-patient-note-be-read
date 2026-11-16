# Results

Every output of the study. Prediction files have one row per patient–trial pair with `pair_id`, `label` and the system's prediction; SPLIT-Match runs also have a full decision trace per pair in `runs/<run>/pairs/`.

## Summary analyses

| File | Content |
|---|---|
| `ANALYSIS_TEST_deploy.json`, `ANALYSIS_TEST_proxy.json` | Pre-specified hypotheses H1–H3 for the laptop run and the hosted-proxy run |
| `ANALYSIS_EXTRA.json` | Pre-specified ablations, H5/H7/H8 CIs, frontier table |
| `ANALYSIS_STRESS_TEST_proxy_proxy.json` | Stress tests (H4 redaction, H6 social cues, H8 noisy notes) |
| `FIDELITY_TEST_deploy_vs_TEST_proxy.json` | Agreement between laptop and hosted-proxy runs |
| `REVIEW_ANALYSIS.json` | Exploratory analyses: missed-patient tests, fixed-model decomposition, model capacity, laptop gpt-oss-20b, repeats, noise floor, long notes, privacy and network simulations |
| `PAPER_NUMBERS.json` | Inputs to `paper/generated/numbers.tex` |
| `DEV_LEDGER.md` | Development iterations (development data only) |
| `RESULTS.md` | Lab log of every result with its source file |

## Runs

| Path | System |
|---|---|
| `runs/TEST_deploy/` | **SPLIT-Match on the laptop** (Qwen3-4B device model), the frozen single test run |
| `runs/TEST_proxy/` | SPLIT-Match with hosted gpt-oss-20b as the device model (proxy run) |
| `runs/AB_*` | Pre-specified ablations on the proxy run: `AB_noL2` (offline, no cloud judge), `AB_noL1`, `AB_noverify`, `AB_hardveto`, `AB_boolean`, `AB_single` (single compiler) |
| `runs/STRESS_*` | Stress tests on the proxy run |
| `runs/dev_*` | Development iterations (development data only) |
| `baselines/ZS_*` | Zero-shot full-note reading: cloud re-run, Qwen3-4B on the laptop (test and development) |
| `baselines/AB_nocompiler_proxy20b*.jsonl` | Pre-specified −compiler ablation: hosted gpt-oss-20b reading the note |
| `baselines/REC_*` | Decisions from a SPLIT-Match fact sheet without rules: cloud model (`REC_cloud_*`), hosted gpt-oss-20b (`REC_edge20b_*`), Qwen3-4B on the laptop (`REC_edge4b_*`) |
| `review/LOC_gptoss20b_test.jsonl` | gpt-oss-20b reading the note on the laptop, all 270 pairs, with latency, tokens/s and peak memory |
| `review/LOC_*_rep1.jsonl` | Fresh (uncached) laptop repeats: Qwen3-4B on 270 pairs, gpt-oss-20b on 40 pairs |
| `review/NF_*` | Repeated hosted runs for the noise floor (cloud gpt-oss-120b, gpt-oss-20b) |
| `review/CAP_*` | Capacity points: Qwen3-1.7B (laptop), Qwen3.8-27B (hosted) |
| `review/LONG_*`, `review/long_notes*.json` | Long, cluttered notes and their screening record |
| `review/GATEWAY_SUITE.*` | Privacy-gateway regression suite |
| `review/L2_ATTRIBUTION.json` | Exclusion route of every missed eligible pair (cloud-judge attribution) |
| `programs/` | Compiled criteria programs for development, test and expansion trials |
| `fresh/` | Fresh checks: compiler audit on 11 unseen trials, extraction on 25 new patients |
| `stress/` | Raw stress-test predictions |

The full-note cloud baselines of the earlier study (zero-shot, few-shot, retrieval-augmented, hybrid) are in `../baselines_indicon/cache/`.
