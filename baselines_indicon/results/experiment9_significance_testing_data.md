# Experiment 9 — Paired significance, bootstrap CIs, clustering (TEST)
> **Separate, un-merged results.** Cache-only: no new API calls, no pipeline re-run, no test-set fitting. Bootstrap B=5000, seed 20260815.

**Test set:** 270 pairs = **45 patients x 18 trials** (~6.0 trials/patient). The 270 pairs are **not independent** — they are repeated measures clustered by patient and by trial. Pair-level CIs therefore *understate* uncertainty; the patient- and trial-cluster bootstraps below are the honest ones.

## 1. Per-system TEST metrics with 95% bootstrap CIs
Accuracy is over all 270 (refusal counted incorrect); precision/recall/F1 are for the **Eligible** (minority, clinically-critical) class over committed predictions.

| System | Acc(270) | F1(elig) | Recall | Precision | Coverage |
| --- | --- | --- | --- | --- | --- |
| Zero-shot LLM | 0.9481 | 0.9014 | 0.9275 | 0.8767 | 1.0 (0 ref) |
| Few-shot LLM | 0.9519 | 0.9091 | 0.942 | 0.8784 | 1.0 (0 ref) |
| RAG-only LLM | 0.9481 | 0.8971 | 0.8841 | 0.9104 | 1.0 (0 ref) |
| Symbolic-only gate | 0.5852 | 0.4815 | 0.7536 | 0.3537 | 1.0 (0 ref) |
| Full framework (hard-veto) | 0.8852 | 0.7826 | 0.6818 | 0.9184 | 0.9778 (6 ref) |
| Advisory variant | 0.9185 | 0.8722 | 0.8788 | 0.8657 | 0.9815 (5 ref) |

### F1 CIs — pair vs patient-cluster vs trial-cluster (note the widening)

| System | F1 | CI pair | CI patient-cluster | CI trial-cluster |
| --- | --- | --- | --- | --- |
| Zero-shot LLM | 0.9014 | [0.8444, 0.9487] | [0.8527, 0.9459] | [0.838, 0.963] |
| Few-shot LLM | 0.9091 | [0.8531, 0.9545] | [0.869, 0.9474] | [0.8571, 0.964] |
| RAG-only LLM | 0.8971 | [0.8361, 0.9466] | [0.8489, 0.9412] | [0.8421, 0.9459] |
| Symbolic-only gate | 0.4815 | [0.3963, 0.5603] | [0.4195, 0.5446] | [0.3019, 0.6245] |
| Full framework (hard-veto) | 0.7826 | [0.687, 0.8598] | [0.7027, 0.8504] | [0.6234, 0.8846] |
| Advisory variant | 0.8722 | [0.8033, 0.928] | [0.8034, 0.9296] | [0.8235, 0.9217] |

## 2. McNemar's exact paired test (TEST, identical 270 pairs)

| Comparison (A vs B) | A>B / B>A | discordant | p (exact) | sig p<.05 |
| --- | --- | --- | --- | --- |
| Full framework (hard-veto) vs Zero-shot LLM | 5/22 | 27 | 0.00151 | YES |
| Advisory variant vs Zero-shot LLM | 3/11 | 14 | 0.05737 | no |
| Advisory variant vs Hard-veto (exp8 run) | 15/4 | 19 | 0.01921 | YES |
| Full framework (hard-veto) vs Symbolic-only gate | 89/8 | 97 | 0.0 | YES |
| Zero-shot LLM vs Few-shot LLM | 3/4 | 7 | 1.0 | no |
| Zero-shot LLM vs RAG-only LLM | 4/4 | 8 | 1.0 | no |

*A>B / B>A* = pairs where only A / only B was correct. p is the two-sided exact binomial McNemar p-value.

## 3. Clean test protocol — advisory justified on DEV (not chosen on test)

To remove the researcher-degree-of-freedom of picking the method after seeing test results, the advisory variant is selected on the **development set only**; the test set is then a single confirmatory report.

| DEV (130 pairs) | Accuracy | F1(elig) | Recall | Precision | FN |
| --- | --- | --- | --- | --- | --- |
| Hard-veto | 0.9154 | 0.9136 | 0.9487 | 0.881 | 2 |
| Advisory | 0.9308 | 0.8916 | 0.9024 | 0.881 | 4 |

DEV McNemar advisory vs veto: advisory-only-correct 2, veto-only-correct 0, discordant 2, exact p = 0.5 (not significant). The direction of improvement (recall/FN) is established on dev; test is confirmatory.

## 4. Honest reading
- Report every headline number as **F1 [trial-cluster CI]**, not a bare point value.
- If the LLM-vs-hybrid McNemar is significant, say the hybrid is significantly *worse*; if advisory-vs-LLM is *not* significant, that is the honest basis for the “LLM-parity” claim.
- With only 18 trials, the trial-cluster CI is wide by construction; do not over-claim small gaps.
