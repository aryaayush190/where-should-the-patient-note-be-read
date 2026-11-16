# Experiment 6 — Cost / accuracy-per-call (TEST, 270 pairs)

From cached test predictions; LLM calls/pair from cached counts. Positive class = Eligible.

| Condition | Accuracy | Precision | Recall | F1 | Mean LLM calls/pair |
|---|---|---|---|---|---|
| Majority (Not Eligible) | 0.7444 | — | — | — | 0 |
| Symbolic-only (Type-A gate) | 0.5852 | 0.3537 | 0.7536 | 0.4815 | 0 |
| Zero-shot LLM | 0.9481 | 0.8767 | 0.9275 | 0.9014 | 1 |
| Hybrid — hard-veto (committed) | 0.8977 | 0.8824 | 0.6818 | 0.7692 | 6.63 |
| Hybrid — advisory gate | 0.9358 | 0.8657 | 0.8788 | 0.8722 | 6.63 |

Advisory hybrid: F1 0.872 at ~6.6 calls, near 1-call zero-shot (0.901). Symbolic gate free but weakest alone. The hybrid's extra cost over zero-shot buys auditability + calibrated refusal, not F1.
