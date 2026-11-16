# Gate test false-negatives — Group A (mechanically fixable) vs Group B (structurally unrepresentable)

All 17 symbolic-gate false-negatives on the test set (from diag_gate_fn). Group A = a parser/matcher fix recovers it (gate under-broadened). Group B = a quantifier / timing / conditional a boolean Type-A gate cannot represent — needs semantic reasoning (advisory/LLM path).

| Pair | Trial | Group | Linguistic failure |
|---|---|---|---|
| P0001__NCT00266877 | NCT00266877 | A | staging-notation (missed 'IV' in list) |
| P0005__NCT01766739 | NCT01766739 | A | prior-therapy phrasing false-positive |
| P0007__NCT02182102 | NCT02182102 | B | quantified exclusion ('>1 prior regimen') |
| P0009__NCT02182232 | NCT02182232 | A | staging-notation |
| P0010__NCT02182102 | NCT02182102 | B | quantified exclusion |
| P0013__NCT02182232 | NCT02182232 | A | staging-notation |
| P0019__NCT03360929 | NCT03360929 | B | temporal washout ('within 14 days') |
| P0020__NCT00266877 | NCT00266877 | A | staging-notation |
| P0028__NCT03141359 | NCT03141359 | B | conditional exclusion ('radiation that would overlap') |
| P0029__NCT02182232 | NCT02182232 | A | inclusive-parenthetical ('including effusion') |
| P0030__NCT02182102 | NCT02182102 | B | quantified exclusion |
| P0033__NCT02182232 | NCT02182232 | A | staging-notation |
| P0035__NCT01766739 | NCT01766739 | A | prior-therapy phrasing false-positive |
| P0038__NCT02182102 | NCT02182102 | B | quantified exclusion |
| P0040__NCT02182102 | NCT02182102 | B | quantified exclusion |
| P0043__NCT02182232 | NCT02182232 | A | inclusive-parenthetical |
| P0045__NCT03360929 | NCT03360929 | B | temporal washout |

**Group A (mechanically fixable) = 9/17  |  Group B (structurally unrepresentable) = 8/17.**

Even fixing every Group-A parser gap leaves the Group-B cases, which a hard binary gate cannot represent — the core argument for the advisory (LLM-decides) redesign.
