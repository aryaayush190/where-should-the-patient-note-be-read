# Experiment 2 — Component ablation (dev_validation)

Pairs: 26. Each row removes ONE component from `full`. The `full` row is the reference; ΔF1 is the drop from it. The core claim rows are `no_sql_gate` (ensemble only) and `no_ensemble` (symbolic only) — `full` must beat both.

| Variant | Accuracy | Precision | Recall | F1 | ΔF1 vs full | Coverage | Mean LLM calls |
|---|---|---|---|---|---|---|---|
| full | 0.8846 | 0.8571 | 0.75 | 0.8 | - | 1.0 | 6.8077 |
| no_sql_gate | 0.8462 | 0.75 | 0.75 | 0.75 | -0.05 | 1.0 | 6.8077 |
| no_ensemble | 0.9615 | 0.8889 | 1.0 | 0.9412 | 0.1412 | 1.0 | 4.8077 |
| no_retrieval | 0.8846 | 0.8571 | 0.75 | 0.8 | 0.0 | 1.0 | 6.8077 |
| single_voter | 0.8462 | 0.8333 | 0.7143 | 0.7692 | -0.0308 | 0.9615 | 5.7692 |
| no_refusal | 0.8462 | 0.75 | 0.75 | 0.75 | -0.05 | 1.0 | 6.8077 |
| no_refinement | 0.8846 | 0.8571 | 0.75 | 0.8 | 0.0 | 1.0 | 6.8077 |
