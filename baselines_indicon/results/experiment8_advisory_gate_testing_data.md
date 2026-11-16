# Experiment 8 — Hard-veto vs Advisory gate (testing_data, 270 pairs)

Identical ensemble/gate inputs per pair; the two variants differ only in _predict_node combination. Positive class = Eligible.

| Variant | Scored | Refused | Accuracy | Precision | Recall | F1 | Confusion (scored) |
|---|---|---|---|---|---|---|---|
| Hard-veto (committed) | 264/270 | 6 | 0.8977 | 0.8824 | 0.6818 | 0.7692 | TP=45 FP=6 FN=21 TN=192 |
| Advisory (EXP_GATE_MODE) | 265/270 | 5 | 0.9358 | 0.8657 | 0.8788 | 0.8722 | TP=58 FP=9 FN=8 TN=190 |

## Recall / false-negative change (the key metric)

| Variant | Recall | False-negatives (FN) |
|---|---|---|
| Hard-veto | 0.6818 | 21 |
| Advisory | 0.8788 | 8 |
| Δ (advisory − veto) | 0.197 | -13 |
