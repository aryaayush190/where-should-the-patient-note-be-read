# Experiment 4 — Error taxonomy (testing_data_veto)

Total errors: 27  (false-positives: 6, false-negatives: 21).

| Failure mode | Count | Share |
|---|---|---|
| conditional_effusion | 9 | 33.3% |
| temporal_washout | 9 | 33.3% |
| cardiac | 4 | 14.8% |
| stage_or_other | 4 | 14.8% |
| molecular | 1 | 3.7% |

Most residual errors fall in semantic/judgement (Type-B) categories the structural gate deliberately delegates to the LLM ensemble.

## Per-error detail

| Pair | Trial | Direction | Category |
|---|---|---|---|
| P0001__NCT00266877 | NCT00266877 | false_negative | conditional_effusion |
| P0002__NCT03057340 | NCT03057340 | false_negative | cardiac |
| P0005__NCT01766739 | NCT01766739 | false_negative | cardiac |
| P0007__NCT01766739 | NCT01766739 | false_negative | cardiac |
| P0007__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0009__NCT02182232 | NCT02182232 | false_negative | conditional_effusion |
| P0010__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0011__NCT03141359 | NCT03141359 | false_negative | stage_or_other |
| P0012__NCT00753714 | NCT00753714 | false_positive | temporal_washout |
| P0013__NCT02182232 | NCT02182232 | false_negative | conditional_effusion |
| P0015__NCT00049543 | NCT00049543 | false_positive | molecular |
| P0019__NCT03360929 | NCT03360929 | false_negative | temporal_washout |
| P0020__NCT00266877 | NCT00266877 | false_negative | conditional_effusion |
| P0025__NCT03141359 | NCT03141359 | false_positive | stage_or_other |
| P0025__NCT00753714 | NCT00753714 | false_positive | temporal_washout |
| P0028__NCT03141359 | NCT03141359 | false_negative | stage_or_other |
| P0029__NCT02182232 | NCT02182232 | false_negative | conditional_effusion |
| P0030__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0031__NCT03141359 | NCT03141359 | false_negative | stage_or_other |
| P0033__NCT02182232 | NCT02182232 | false_negative | conditional_effusion |
| P0035__NCT01766739 | NCT01766739 | false_negative | cardiac |
| P0038__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0040__NCT02182102 | NCT02182102 | false_negative | temporal_washout |
| P0041__NCT01047059 | NCT01047059 | false_positive | conditional_effusion |
| P0043__NCT02182232 | NCT02182232 | false_negative | conditional_effusion |
| P0044__NCT00465907 | NCT00465907 | false_positive | conditional_effusion |
| P0045__NCT03360929 | NCT03360929 | false_negative | temporal_washout |
