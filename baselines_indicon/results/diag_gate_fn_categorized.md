# Symbolic-gate false-negatives on the held-out test set — linguistic root-cause analysis

READ-ONLY diagnostic. 17 pairs the Type-A gate wrongly rejected (all truly
Eligible). Full per-pair records (patient profile, verbatim inclusion/exclusion,
extracted fields, per-clause SQL evaluation) are in
`diag_gate_fn_testing_data.json`. No rule, parser, or prompt was changed.

**Meta-finding:** every failure is over-restriction. In each case the trial
genuinely permits the patient, but the parser converted a *qualified* natural-
language constraint into an *absolute* structural gate — it dropped a broadening
stage token, or read a quantified / conditional / temporal / inclusive clause as
a hard binary. The patient-side extraction was usually correct; the fault is in
trial-criteria parsing being too strict.

## Per-pair table

| Pair | Trial | Failing Type-A clause | The verbatim criterion (and why the patient actually qualifies) | Linguistic root cause |
|---|---|---|---|---|
| P0001 | NCT00266877 | stage (+ prior-chemo) | INCL "stage IIIB (with pleural effusion) **or IV**" — patient is Stage IV; parser extracted only `['IIIB']`, dropping "IV" | Staging notation not recognized |
| P0020 | NCT00266877 | stage | same trial; patient Stage IV; "IV" dropped from the list | Staging notation not recognized |
| P0009 | NCT02182232 | stage | INCL "Stage IIIB (including pleural effusion), **IV** or recurrent" — patient Stage IV; parser got only `['IIIB']` | Staging notation not recognized |
| P0013 | NCT02182232 | stage | same; patient Stage IV | Staging notation not recognized |
| P0033 | NCT02182232 | stage | same; patient Stage IV (squamous) | Staging notation not recognized |
| P0029 | NCT02182232 | iiib_requires_effusion | INCL "Stage IIIB (**including** pleural effusion)" is *inclusive* (IIIB counts, effusion or not); parser read it as *requires* effusion, and patient is IIIB without effusion | Inclusive parenthetical misread as restrictive |
| P0043 | NCT02182232 | iiib_requires_effusion | same; IIIB without effusion | Inclusive parenthetical misread as restrictive |
| P0007 | NCT02182102 | prior-chemo exclusion | INCL requires "progression following **one** prior platinum chemotherapy"; EXCL bars only "**more than one** prior chemotherapy regimen". Patient had one prior line → eligible; parser read "prior chemotherapy" as an absolute bar | Quantified exclusion read as absolute |
| P0010 | NCT02182102 | prior-chemo exclusion | same trial; patient had prior chemo (one line) | Quantified exclusion read as absolute |
| P0030 | NCT02182102 | prior-chemo exclusion | same | Quantified exclusion read as absolute |
| P0038 | NCT02182102 | prior-chemo exclusion | same | Quantified exclusion read as absolute |
| P0040 | NCT02182102 | prior-chemo exclusion | same | Quantified exclusion read as absolute |
| P0019 | NCT03360929 | prior-chemo exclusion | EXCL "cytotoxic chemotherapy … **within 14 days**" (a wash-out window); patient's chemo was earlier → eligible; the "within 14 days" qualifier sits too far from "chemotherapy" for the parser's timing window, so it read the bar as absolute | Temporal/wash-out qualifier out of scope |
| P0045 | NCT03360929 | prior-chemo exclusion | same trial; prior chemo outside the 14-day window | Temporal/wash-out qualifier out of scope |
| P0028 | NCT03141359 | prior-radiotherapy exclusion | EXCL "prior radiation … **that would result in overlap … and impede** the study" (conditional on field overlap); patient's prior radiotherapy does not overlap → eligible; parser read "prior radiation" as an absolute bar | Conditional exclusion scope read as absolute |
| P0005 | NCT01766739 | requires_prior_chemo | No prior-therapy requirement in the trial; INCL only says toxicities "must have resolved" and a stage-IV patient "must have **had** a brain scan". Parser's "must have had/received" pattern false-fired `requires_prior_chemo`; patient is chemo-naïve → wrongly rejected | Required-prior-therapy false-positive (phrasing) |
| P0035 | NCT01766739 | requires_prior_chemo | same trial; chemo-naïve patient | Required-prior-therapy false-positive (phrasing) |

## Summary count per category

| Linguistic root cause | Pairs | Trials |
|---|---|---|
| Staging notation not recognized ("IV" dropped from a parenthetical stage list) | 5 | NCT00266877, NCT02182232 |
| Quantified exclusion read as absolute ("more than one prior chemo regimen") | 5 | NCT02182102 |
| Inclusive parenthetical misread as restrictive ("IIIB including effusion" → requires effusion) | 2 | NCT02182232 |
| Temporal/wash-out qualifier out of scope ("within 14 days" far from the therapy term) | 2 | NCT03360929 |
| Required-prior-therapy false-positive (washout/tolerability phrasing "must have had/resolved") | 2 | NCT01766739 |
| Conditional exclusion scope read as absolute (radiation "that would overlap/impede") | 1 | NCT03141359 |
| **Total** | **17** | **6 trials** |

## Higher-level grouping (mapping to standard buckets)

| Bucket | Pairs |
|---|---|
| Staging notation not recognized | 5 |
| Nested / conditional exclusion (quantified + conditional-scope + inclusive-parenthetical) | 8 |
| Negation / qualifier scope (temporal wash-out qualifier too distant) | 2 |
| Prior-therapy phrasing false-positive (line-of-therapy) | 2 |

## Notes for the fix decision (not acted on)

- The failures concentrate in **6 trials** (2 trials, NCT02182102 & NCT02182232,
  account for 12 of 17), so a small number of parsing patterns drive most of it.
- Two failure classes are **over-broadening the gate would fix** (staging-list
  "IV", inclusive "including effusion"); three are **hardening qualifiers**
  (quantified "> N regimens", temporal wash-outs, conditional radiation) that a
  binary gate structurally cannot represent without becoming semantic.
- The patient-side extraction was correct in essentially all 17 — the fault is
  trial-criteria parsing, not attribute extraction.
