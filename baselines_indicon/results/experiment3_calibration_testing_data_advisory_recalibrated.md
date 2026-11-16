# Experiment 3b — Confidence recalibration (advisory, dev-fit / test-transform)
**Fit set:** dev_train + dev_validation, 130 scored pairs (dev accuracy 0.9308). **Eval set:** cached test advisory predictions, 265 scored pairs (test accuracy 0.9358).  No pipeline re-run, no new API calls — test confidences were transformed through the dev-fitted calibrator.
## Fitted calibrators (dev only)
- **Platt (primary):** `p = sigmoid(-1.6296 * conf + 3.8055)`
- **Isotonic (sensitivity):** 16 unique-x levels, fitted range [0.333, 0.964]

## Before vs after (test set)
| Metric | Raw (before) | Platt (after) | Isotonic (after) |
| --- | --- | --- | --- |
| ECE | 0.2254 | 0.0031 | 0.2804 |
| Brier | 0.1243 | 0.0605 | 0.2072 |
| Mean confidence | 0.7105 | 0.9327 | 0.6699 |
| Accuracy (unchanged) | 0.9358 | 0.9358 | 0.9358 |

## Reliability — raw (before) (ECE 0.2254, Brier 0.1243)
| Confidence bin | n | Mean confidence | Accuracy |
| --- | --- | --- | --- |
| [0.5,0.6) | 93 | 0.5882 | 0.9355 |
| [0.6,0.7) | 51 | 0.6081 | 0.9216 |
| [0.8,0.9) | 121 | 0.8476 | 0.9421 |

## Reliability — Platt (dev-fit) (ECE 0.0031, Brier 0.0605)
| Confidence bin | n | Mean confidence | Accuracy |
| --- | --- | --- | --- |
| [0.9,1.0) | 265 | 0.9327 | 0.9358 |

## Accuracy vs. coverage (refusal sweep)
A monotonic calibrator cannot create discrimination that the raw signal lacks: an increasing map leaves the refusal ranking unchanged, a decreasing one reverses it. The dev-fitted Platt map here is decreasing (slope A<0), so refusal accuracy does not improve.

| Coverage | n kept | Acc raw | Acc Platt | min conf (Platt) |
| --- | --- | --- | --- | --- |
| 1.0 | 265 | 0.9358 | 0.9358 | 0.9156 |
| 0.9 | 238 | 0.9454 | 0.9286 | 0.9176 |
| 0.8 | 212 | 0.9387 | 0.9387 | 0.9186 |
| 0.7 | 186 | 0.9409 | 0.9355 | 0.9191 |
| 0.6 | 159 | 0.9371 | 0.9308 | 0.9202 |
| 0.5 | 132 | 0.9318 | 0.9394 | 0.9429 |
| 0.4 | 106 | 0.9434 | 0.934 | 0.9439 |
| 0.3 | 80 | 0.9375 | 0.925 | 0.9444 |
| 0.2 | 53 | 0.9245 | 0.9057 | 0.9448 |
| 0.1 | 26 | 1.0 | 0.8462 | 0.9453 |

## Interpretation (honest)
- **Calibration (magnitude) is fixed.** Platt scaling fit on dev cuts test **ECE 0.2254 -> 0.0031** and **Brier 0.1243 -> 0.0605**, lifting mean confidence 0.7105 -> 0.9327 to match accuracy 0.9358. The raw formula was badly **under-confident** (conf ~0.59 on cases that were ~0.93 accurate); calibration corrects that.
- **Resolution (discrimination) is NOT fixed, and cannot be by post-hoc calibration.** Raw accuracy is ~0.92-0.94 in *every* confidence cluster, so the signal barely separates right from wrong. The dev-fitted Platt slope is **A=-1.630 (negative)** — raw confidence is essentially uncorrelated (slightly inverted) with correctness on dev — so calibrated confidence collapses to a near-constant (~base accuracy). The accuracy-vs-coverage curve stays flat/non-monotonic: **refusing low-confidence cases does not raise accuracy**, before or after calibration.
- **Isotonic overfits at n=130.** Forcing a monotonic-increasing map on a flat/inverted dev relation gives test **ECE 0.2804 / Brier 0.2072** — *worse than raw*. This is why Platt (parametric, pre-committed) is the headline and isotonic is reported only as a sensitivity check.
- **Bottom line:** post-hoc calibration genuinely fixes the reported ECE/Brier problem, but the refuse-to-decide mechanism remains ineffective because the underlying confidence lacks resolution. That is a limitation of the confidence *formula* (near-binary on gate PASS/FAIL), not something a calibrator can repair; fixing it would need a more informative confidence signal (e.g. genuine ensemble vote dispersion), which is out of scope here and would require new runs.
