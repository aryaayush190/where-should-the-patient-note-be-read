# DRAFT — Advisory-gate justification, reframed (architectural, not metric-selected)

> Not merged into results.md / methodology.md. Review first. Sources: Group A/B table
> (`gate_failure_groupAB_testing_data.md`), dev McNemar (`experiment9_significance_testing_data.md`).

## Paragraph for the paper (Methodology / Design Rationale section)

> A binary Type-A gate checks each constraint as a static boolean predicate over a single
> patient row. This representation is structurally closed under three constraint types —
> **counts** ("no more than 1 prior systemic regimen"), **relative timing** ("within 14 days
> of enrollment"), and **conditionals** ("radiation therapy that would overlap with protocol
> treatment") — none of which reduce to a per-row boolean check without either unbounded
> auxiliary state (counts across an unknown-length treatment history) or semantic
> interpretation of a hypothetical ("would overlap") that a SQL predicate cannot evaluate.
> This is a property of the constraint *type*, independent of which trials are observed at
> tuning time, and it predicts that a hard veto gate will under-generalize specifically on
> unseen trials carrying these constraint types — regardless of how well its parser is tuned
> on development trials.
>
> We verified this prediction on the development set by categorizing every gate false
> negative into Group A (a parser/matcher gap — mechanically fixable) or Group B (a
> count/timing/conditional constraint — not representable by a boolean gate by
> construction). [We then repeated the same categorization on the held-out test set as an
> observational check, not a selection criterion:] of the gate's 17 test false negatives,
> 8/17 (47%) are Group B, concentrated in exactly the predicted categories (quantified
> exclusion, temporal washout, conditional exclusion). This is consistent with, but not the
> basis for, the architectural argument above.
>
> On this architectural basis we designed an advisory variant in which the gate's Type-A
> verdict informs confidence rather than vetoing the ensemble's decision, so Group-B
> constraints are handled by the LLM ensemble's semantic reasoning instead of being forced
> through an unrepresentable boolean check.

## Explicit exploratory-finding disclosure (place near the test result)

> The advisory redesign was motivated by the architectural argument above, established
> without reference to test-set performance. On development data alone, hard-veto and
> advisory are statistically indistinguishable (F1 0.914 vs 0.892, McNemar exact p = 0.50,
> n = 130) — development data cannot distinguish them because the dev trial set does not
> stress Group-B constraints enough to separate the two configurations. The test-set result
> (F1 0.783 → 0.872, McNemar p = 0.019 vs. hard-veto) is reported as an **exploratory
> observation consistent with the architectural prediction**, not as a held-out confirmation
> of superiority — the test set was examined during the diagnosis that produced this design,
> so it cannot also serve as blind validation of it. A genuinely confirmatory test would
> require a fresh, never-inspected evaluation set (see Limitations).

## Where each number comes from (for your own audit trail)
- Group A/B split (9/17, 8/17) + category labels: `experiments/results/gate_failure_groupAB_testing_data.md`
- Dev hard-veto vs advisory (F1 0.914/0.892, McNemar p=0.50): `experiments/results/experiment9_significance_testing_data.md` §3
- Test hard-veto vs advisory (F1 0.783/0.872, McNemar p=0.019): same file §2

## Suggested Limitations addition
> The advisory redesign's test-set improvement is reported as an exploratory finding
> consistent with an architectural prediction made independently of test data, not as a
> blind confirmatory result, since the same test set informed the diagnosis that motivated
> the redesign. A held-out validation on a third, never-inspected trial set (e.g. the
> 11-trial development-expansion pool, blindly annotated) would be needed to confirm the
> effect size.
