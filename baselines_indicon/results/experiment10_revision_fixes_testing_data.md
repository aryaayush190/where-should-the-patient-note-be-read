# Experiment 10 — INDICON revision analysis fixes (TEST)
> Cache-only: no new API calls, no pipeline re-run, no test-set fitting. Cluster bootstrap B=5000, seed 20260815; patient-cluster permutation 200,000 flips; trial-cluster permutation exact.

**Test set:** 270 pairs = 45 patients x 18 trials.

## R2.1 — One accuracy convention (refusal = incorrect, denominator N=270)

The stated method counts a refusal as an incorrect classification for accuracy. Table I already followed it; the Table III (policy-comparison) accuracies had used a decided-only denominator. Below, `Acc(270)` is the corrected, consistent figure; `Acc(decided)` is the old decided-only value, shown only to document the discrepancy.

**Corrected Table I (held-out, 270 pairs):**

| System | Acc(270) | Acc(decided) | Prec | Rec | F1 | Ref | Cov |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Majority | 0.7444 | 0.7444 | — | — | — | 0 | 1.0 |
| Symbolic-only | 0.5852 | 0.5852 | 0.3537 | 0.7536 | 0.4815 | 0 | 1.0 |
| Zero-shot LLM | 0.9481 | 0.9481 | 0.8767 | 0.9275 | 0.9014 | 0 | 1.0 |
| Few-shot LLM | 0.9519 | 0.9519 | 0.8784 | 0.942 | 0.9091 | 0 | 1.0 |
| RAG + LLM | 0.9481 | 0.9481 | 0.9104 | 0.8841 | 0.8971 | 0 | 1.0 |
| Hard veto (exp1 run) | 0.8852 | 0.9053 | 0.9184 | 0.6818 | 0.7826 | 6 | 0.9778 |

**Corrected Table III (same-run policy comparison, exp8 pass):**

| Policy | Acc(270) | Acc(decided) | Prec | Rec | F1 | FN | Confusion | Ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hard veto | 0.8778 | 0.8977 | 0.8824 | 0.6818 | 0.7692 | 21 | TP=45 FP=6 FN=21 TN=192 | 6 |
| Advisory | 0.9185 | 0.9358 | 0.8657 | 0.8788 | 0.8722 | 8 | TP=58 FP=9 FN=8 TN=190 | 5 |

*Fix:* report `Acc(270)` in both tables. Table III's previously-printed .898 / .936 were decided-only; the consistent values are above.

## R2.2 — Significance that respects repeated patients & trials

The 270 pairs are 45 patients x 18 trials, not 270 independent observations. Beside the naive per-pair McNemar we add two cluster-robust paired tests on net correctness: a **sign-flip permutation test** over trial clusters (exact, 2^18 flips) and over patient clusters (Monte-Carlo), and a **trial-cluster bootstrap** 95% CI + p of the paired accuracy difference (A−B).

| Comparison (A vs B) | McNemar p (pair) | Trial-cluster p | Patient-cluster p | Acc diff (A−B) [95% CI] | Boot p |
| --- | --- | --- | --- | --- | --- |
| Hard veto (exp1 run) vs Zero-shot LLM | 0.00151* | 0.01758* | 0.00034* | -0.063 [-0.1033, -0.0236] | 0.0016* |
| Advisory (exp8 run) vs Zero-shot LLM | 0.05737 | 0.15625 | 0.05541 | -0.0296 [-0.0654, 0.0] | 0.076 |
| Advisory (exp8 run) vs Hard veto (exp8 run) | 0.01921* | 0.01562* | 0.01775* | 0.0407 [0.0172, 0.069] | 0.0004* |
| Few-shot LLM vs Zero-shot LLM | 1.0 | 1.0 | 1.0 | 0.0037 [-0.0082, 0.0162] | 0.7544 |
| RAG + LLM vs Zero-shot LLM | 1.0 | 1.0 | 1.0 | 0.0 [-0.0236, 0.0175] | 1.0 |

`*` = significant at 0.05. Trial-cluster p is the primary test (the trial is the unit of generalization). A CI that excludes 0 agrees with a significant cluster p.
