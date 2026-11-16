# Privacy-gateway regression suite

| Case | Expected | n | Blocked | Rate |
|---|---|---|---|---|
| A1 real fact queries (laptop run) | allow | 539 | 0 | 0.0% |
| A2 real public-criteria calls | allow | 745 | 0 | 0.0% |
| P1 exact note sentence | block | 368 | 368 | 100.0% |
| P2 case and spacing changed | block | 368 | 363 | 98.6% |
| P3 sentence embedded in a criterion query | block | 368 | 368 | 100.0% |
| P4 patient identifier | block | 368 | 368 | 100.0% |
| P5 pair identifier | block | 368 | 368 | 100.0% |
| P6 first half of a sentence | block | 339 | 1 | 0.3% |
| P7 one word deleted | block | 339 | 2 | 0.6% |
| P8 punctuation removed | block | 368 | 0 | 0.0% |
| P9 base64-encoded sentence | block | 368 | 0 | 0.0% |

Registered note sentences: 368; note sentences not protected because they are shorter than 25 characters: 31; because they also occur in public criteria: 0.
