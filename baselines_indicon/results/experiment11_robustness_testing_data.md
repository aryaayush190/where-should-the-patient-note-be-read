# Experiment 11 — Leave-one-trial-out robustness (TEST)
> Cache-only: no new API calls, no pipeline re-run, no test-set fitting. Drop each of the 18 held-out trials in turn; recompute ΔF1 / Δrecall (A−B) over the remaining 17 trials.

**Test set:** 270 pairs over 18 trials.

## Stability of each effect across trials

| Comparison (A vs B) | Full ΔF1 | Full Δrecall | LOTO ΔF1 range | Folds keeping sign |
| --- | --- | --- | --- | --- |
| Advisory vs Hard-veto | +0.1029 | +0.1970 | [+0.071, +0.131] | 18/18 |
| Advisory vs Zero-shot | -0.0292 | -0.0487 | [-0.047, -0.006] | 18/18 |
| Hard-veto vs Zero-shot | -0.1322 | -0.2457 | [-0.163, -0.105] | 18/18 |

If every leave-one-trial-out fold keeps the sign of the full-set ΔF1, the effect is a property of the 18-trial population, not an artifact of one or two trials. Source: `experiment11_robustness_testing_data.json`.
