# Earlier full-note baselines

Predictions of the full-note cloud baselines from our earlier study on the same benchmark (Arya et al., IEEE INDICON 2026), reused as comparators.

- `cache/experiment1_testing_data_zero_shot.jsonl` — cloud gpt-oss-120b zero-shot (the paper's reference run)
- `cache/experiment1_testing_data_few_shot.jsonl`, `cache/experiment1_testing_data_rag_only.jsonl` — few-shot and retrieval-augmented
- `cache/experiment8_testing_data_advisory.jsonl` — the earlier hybrid system (advisory variant)
- `cache/*dev_validation*`, `cache/*dev130*` — the same systems on development data
- `results/` — the earlier study's summary analyses

Each row has `pair_id`, `trial_id`, `target` (gold label) and the prediction. These files are read by `experiments/analyze.py` and `experiments/review_analysis.py`.
