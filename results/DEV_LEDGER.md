# Development ledger (dev data only; Groq edge proxy unless noted)

Reference: cloud zero-shot gpt-oss-120b (INDICON prompt) on dev_train = acc 0.913 / F1 0.870; on dev_validation = acc 0.808.

| run | forced acc | forced F1 | FP | FN | selective coverage | selective acc (decided) | L2/pair | offline decided | change |
|---|---|---|---|---|---|---|---|---|---|
| dev_train_proxy_v2 | 0.750 | 0.594 | 12 | 14 | 0.702 | 0.808 | 1.32 | 0.260 | first working end-to-end (L1 JSON fix); compiler v1.1 |
| dev_train_proxy_v3 | 0.837 | 0.785 | 15 | 2 | 0.558 | 0.966 | 1.25 | 0.202 | compiler v1.2 (alternatives->ANY, permissions, fragment merge, stage-merge), regex bounds, L2 gets structured record |
| dev_train_proxy_v4 | 0.721 | 0.216 | 0 | 29 | 0.635 | 0.924 | 1.37 | 0.192 | verbatim judging of contested atoms; site-verifiable class; forced label-convention (later withdrawn) |
| dev_train_proxy_v5 | 0.779 | 0.582 | 6 | 17 | 0.779 | 0.901 | 1.37 | 0.327 | not-mentioned routing: exclusion->presumed absent, clinical inclusion->ask, other->site |
| dev_train_proxy_v6 | 0.856 | 0.795 | 11 | 4 | 0.779 | 0.901 | 1.60 | 0.337 | label-convention withdrawn -> registered forced rule (L2 on 'not stated'+record); permission guard; regex  repair |
| dev_train_proxy_v7 | 0.808 | 0.667 | 7 | 13 | 0.769 | 0.912 | 1.44 | 0.317 | + systemic filter fix + forced L2 rubric (rubric later withdrawn) |
| dev_train_proxy_v8 | 0.856 | 0.795 | 11 | 4 | 0.769 | 0.912 | 1.62 | 0.317 | rubric withdrawn (candidate freeze) |
| dev_val_proxy_v8 | 0.808 | 0.667 | 2 | 3 | 0.808 | 0.857 | 1.35 | 0.346 | guard fold, candidate freeze |
| dev_val_LOCAL_v9 | 0.769 | 0.625 | 3 | 3 | 0.885 | 0.826 | 1.81 | 0.231 | post-freeze characterisation (T3.4): frozen v9 with the local Qwen3-4B edge; forced-decision agreement with dev_val_proxy_v9 0.962 (25/26) |
| dev_train_ab_hardveto | 0.827 | 0.719 | 8 | 10 | 0.856 | 0.854 | 1.05 | 0.548 | ablation: hard veto |
| dev_train_ab_offline | 0.788 | 0.744 | 21 | 1 | 0.644 | 0.940 | 0.00 | 0.644 | ablation: no L2 (offline) |
| dev_train_ab_boolean | 0.827 | 0.763 | 14 | 4 | 0.692 | 0.903 | 2.08 | 0.212 | ablation: boolean-only atoms |

Every change is logged with its reason in docs/PREREGISTRATION.md §9.
