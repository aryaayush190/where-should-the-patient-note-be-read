# Compiler-fidelity audit — fresh expansion trials (12 trials, never used in development)

Procedure (`experiments/audit_compiler.py`):

1. An independent auditor model, `openai/gpt-oss-20b`, checked every typed atom against its verbatim criterion line. It is neither of the two compilers. It saw only public trial text.
2. The authors adjudicated every atom the auditor flagged among the **agreed** atoms. Agreed atoms are the ones that carry deterministic authority.
3. The authors also checked a random sample of 30 auditor-OK agreed atoms (seed 20260815).

Downgraded atoms are judged on their verbatim line at runtime, so their compiled form never decides. They are reported only through the auditor rate.

## Auditor verdicts

| Group | n | Auditor OK | Auditor flagged |
|---|---|---|---|
| All typed atoms | 200 | 140 | 60 |
| Agreed (deterministic authority) | 143 | 115 (80.4%) | 28 (19.6%) |
| Downgraded (compilers disagreed) | 57 | 25 (43.9%) | 32 (56.1%) |

- Fisher exact test, flagged-rate agreed vs downgraded: OR = 0.19, p = 9.2e-7.
- Dual-compiler agreement therefore concentrates compilation errors in the atoms that lose authority.

## Adjudication of the 28 flagged agreed atoms

**Real semantic errors (4):**

| Atom | Error |
|---|---|
| NCT02038699 c0A21 | Liver and renal clauses joined by OR. A patient with AST > 2.5×ULN passes if CrCl ≥ 60. Too permissive. |
| NCT02038699 c0A34 | Any arrhythmia history narrowed to "uncontrolled" arrhythmia. Too permissive. |
| NCT03087448 c0A17 | Gilbert's exception compiled as an OR'd conditional JUDGE child. A judge may read it as vacuously true for patients without Gilbert's. Too permissive. |
| NCT03087448 c0A18 | Same pattern for the liver-metastasis exception. Too permissive. |

**Minor narrowings (2).** Each drops an exception and over-excludes only in edge cases:

| Atom | Narrowing |
|---|---|
| NCT00065182 c0A10 | "Major surgery" became any surgery. |
| NCT03602027 c1A3 | The "except due to trauma" exception for neuropathy was dropped. |

**Not errors (22):**

- **Partial capture, other requirements on the same line covered by sibling atoms (12):** c0A0/c0A2/c0A3/c1A8 cancer_type, measurable_disease ×3, unstable_angina, chf, c0A4 COUNT, c0A9 SINCE.
- **Equivalent polarity (2):** inclusion "has not received X" is the same as exclusion "has X" (NCT03602027 c0A6, c0A7).
- **Covered by another atom (2):** NCT03087448 c1A20 (thoracic 4-week window is c1A19) and c1A23 (3-week systemic window is c1A22).
- **Trial-text typo (1):** hemoglobin "8.0 mg/dL" is a typo for g/dL in the trial text.
- **Rounding (1):** 10 weeks = 2.30 months.
- **Clinically conventional reading (4):**
  - "advanced NSCLC" read as stage IIIB–IV;
  - albumin ≥ LLN ≈ 3.5 g/dL;
  - brain-mets category "untreated or symptomatic" ×2.
- **Ambiguous parse (1):** "history of CHF, or MI or stroke in the last 3 months" (NCT02038699 c0A35). This is over-restrictive at worst, and is counted as not an error.

## Sample of 30 auditor-OK agreed atoms

All 30 are correct on author review. The auditor's miss rate is 0/30, with a 95% upper bound of 11.6% (Clopper–Pearson).

## Result

| Measure | Count | Rate | 95% Clopper–Pearson CI |
|---|---|---|---|
| Semantic errors among agreed atoms | 4 / 143 | 2.8% | 0.8–7.0% |
| Including minor narrowings | 6 / 143 | 4.2% | 1.6–8.9% |

All 4 semantic errors are *permissive* (they can only fail to exclude). None produces a false exclusion.

**Caveat.** Adjudication was done by the authors, with an LLM coding assistant. It is not independent clinical annotation.
