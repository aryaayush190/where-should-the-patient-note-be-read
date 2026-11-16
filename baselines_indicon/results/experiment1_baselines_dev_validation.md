# Experiment 1 — Baseline comparison (dev_validation)

Pairs: 26. Majority-class accuracy: None. Positive class: Eligible.

| Condition | Accuracy | Precision | Recall | F1 | Coverage | Mean Brier | Mean LLM calls |
|---|---|---|---|---|---|---|---|
| zero_shot | 0.8462 | 0.75 | 0.75 | 0.75 | 1.0 | 0.1351 | 1.0 |
| few_shot | 0.7692 | 0.8333 | 0.7143 | 0.7692 | 0.8846 | 0.11 | 0.8846 |
| rag_only | 0.9231 | 1.0 | 0.75 | 0.8571 | 1.0 | 0.0621 | 1.0 |
| full | 0.8462 | 0.75 | 0.75 | 0.75 | 1.0 | 0.0819 | 6.8077 |
