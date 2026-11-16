# Experiment 4 — Error taxonomy (testing_data_advisory)

Total errors: 17  (false-positives: 9, false-negatives: 8).

| Failure mode | Count | Share |
|---|---|---|
| conditional_effusion | 6 | 35.3% |
| stage_or_other | 4 | 23.5% |
| cardiac | 3 | 17.6% |
| temporal_washout | 3 | 17.6% |
| molecular | 1 | 5.9% |

Most residual errors fall in semantic/judgement (Type-B) categories the structural gate deliberately delegates to the LLM ensemble.

## Per-error detail

| Pair | Trial | Direction | Category |
|---|---|---|---|
| P0001__NCT00266877 | NCT00266877 | false_negative | conditional_effusion |
| P0002__NCT03057340 | NCT03057340 | false_negative | cardiac |
| P0011__NCT03141359 | NCT03141359 | false_negative | stage_or_other |
| P0012__NCT00753714 | NCT00753714 | false_positive | temporal_washout |
| P0015__NCT00049543 | NCT00049543 | false_positive | molecular |
| P0015__NCT03057340 | NCT03057340 | false_negative | cardiac |
| P0019__NCT02182232 | NCT02182232 | false_positive | conditional_effusion |
| P0022__NCT02182232 | NCT02182232 | false_positive | conditional_effusion |
| P0024__NCT03057340 | NCT03057340 | false_negative | cardiac |
| P0025__NCT03141359 | NCT03141359 | false_positive | stage_or_other |
| P0025__NCT00753714 | NCT00753714 | false_positive | temporal_washout |
| P0030__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0031__NCT02073968 | NCT02073968 | false_negative | stage_or_other |
| P0031__NCT03141359 | NCT03141359 | false_negative | stage_or_other |
| P0041__NCT01047059 | NCT01047059 | false_positive | conditional_effusion |
| P0042__NCT02182232 | NCT02182232 | false_positive | conditional_effusion |
| P0044__NCT00465907 | NCT00465907 | false_positive | conditional_effusion |
