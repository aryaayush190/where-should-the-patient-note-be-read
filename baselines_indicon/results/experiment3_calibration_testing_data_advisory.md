# Experiment 3 — Confidence calibration

Source: `experiments/results/_cache/experiment_testing_data_advisory_adapter.jsonl` | scored pairs: 265 | **ECE = 0.2254**

## Reliability diagram (10 bins)

| Confidence bin | n | Mean confidence | Accuracy |
|---|---|---|---|
| [0.0,0.1) | 0 | None | None |
| [0.1,0.2) | 0 | None | None |
| [0.2,0.3) | 0 | None | None |
| [0.3,0.4) | 0 | None | None |
| [0.4,0.5) | 0 | None | None |
| [0.5,0.6) | 93 | 0.5882 | 0.9355 |
| [0.6,0.7) | 51 | 0.6081 | 0.9216 |
| [0.7,0.8) | 0 | None | None |
| [0.8,0.9) | 121 | 0.8476 | 0.9421 |
| [0.9,1.0) | 0 | None | None |

## Accuracy vs. coverage (refusal sweep)

| Coverage | n kept | Accuracy | Min confidence kept |
|---|---|---|---|
| 1.0 | 265 | 0.9358 | 0.542 |
| 0.9 | 238 | 0.9454 | 0.587 |
| 0.8 | 212 | 0.9387 | 0.593 |
| 0.7 | 186 | 0.9409 | 0.597 |
| 0.6 | 159 | 0.9371 | 0.606 |
| 0.5 | 132 | 0.9318 | 0.616 |
| 0.4 | 106 | 0.9434 | 0.837 |
| 0.3 | 80 | 0.9375 | 0.844 |
| 0.2 | 53 | 0.9245 | 0.848 |
| 0.1 | 26 | 1.0 | 0.856 |

If accuracy rises as coverage falls, the confidence score correctly ranks hard cases and the refuse-to-decide mechanism is validated.
