# Experiment 8 — Hard-veto vs Advisory gate (DEV 130 pairs)

Identical ensemble/gate inputs per pair; the two variants differ only in _predict_node combination. Positive class = Eligible.

| Variant | Scored | Refused | Accuracy | Precision | Recall | F1 | Confusion (scored) |
|---|---|---|---|---|---|---|---|
| Hard-veto (committed) | 126/130 | 4 | 0.9444 | 0.881 | 0.9487 | 0.9136 | TP=37 FP=5 FN=2 TN=82 |
| Advisory (EXP_GATE_MODE) | 130/130 | 0 | 0.9308 | 0.881 | 0.9024 | 0.8916 | TP=37 FP=5 FN=4 TN=84 |

## Recall / false-negative change (the key metric)

| Variant | Recall | False-negatives (FN) |
|---|---|---|
| Hard-veto | 0.9487 | 2 |
| Advisory | 0.9024 | 4 |
| Δ (advisory − veto) | -0.0463 | 2 |
