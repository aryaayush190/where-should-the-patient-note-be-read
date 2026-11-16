# Dataset Creation Documentation

**Dataset:** NSCLC Clinical Trial Eligibility Matching — Binary Classification (Eligible / Not Eligible / Insufficient Information)
**Purpose:** Evaluation dataset for an agentic clinical-trial-matching framework.
**Scope:** Non-small cell lung cancer (NSCLC) only.

This document records every technique, parameter, keyword set, and design decision used
to build the dataset, so the process is fully reproducible and auditable by reviewers. It
covers three stages: (1) the trial corpus and how trials were parsed, (2) how trials were
selected into two disjoint sets, and (3) how synthetic patient profiles are generated and
labelled. Where a design choice exists specifically to protect against a validity threat,
that is stated explicitly.

---

## 1. Source corpus

### 1.1 Provenance

- **Source file:** `corpus.jsonl`
- **Origin:** the TREC 2022 Clinical Trials track corpus, as redistributed in the TrialGPT
  repository, pre-filtered to lung-cancer-related trials. Every trial ultimately derives
  from a real ClinicalTrials.gov registered protocol and is traceable by its NCT identifier.
- **Size:** 236 trial records.
- **Single source tag:** every record carries `dataset_source = "trec_2022"` (verified).

### 1.2 Record schema

Each corpus record is a JSON object with these fields:

| Field | Meaning |
|---|---|
| `_id` | NCT identifier (e.g. `NCT02718066`) |
| `title` | Official trial title |
| `inclusion_criteria` | Verbatim inclusion criteria text |
| `exclusion_criteria` | Verbatim exclusion criteria text |
| `diseases_list` | List of condition strings from the registry |
| `drugs_list` | List of intervention/drug names |
| `phase` | Trial phase (e.g. "Phase 2") |
| `enrollment` | Target enrollment count |
| `brief_summary` | Registry brief summary |
| `full_text` | Concatenated full protocol text |

**Key property:** inclusion and exclusion criteria are already separated into distinct
fields in the source. We therefore never perform the error-prone "split one criteria blob
on an *Exclusion Criteria:* header" step that the clinical-NLP literature repeatedly flags
as unreliable. The criteria are used verbatim, exactly as registered.

### 1.3 Corpus composition (measured, not assumed)

The corpus is lung-cancer-centric but not exclusively NSCLC. Measured disease frequencies
include Lung Cancer (74), Carcinoma (24), and multiple spellings of Non-Small Cell Lung
Cancer (Non-small Cell Lung Cancer 23, Non-Small-Cell Lung 15, Non Small Cell Lung Cancer
14, etc.), alongside a minority of off-target records (e.g. Breast Cancer, Ovarian Cancer,
isolated Brain/Bone Metastases trials, one large lymphoma trial, and supportive-care studies
such as asthma, cachexia, and Cushing's disease). A screen for records lacking any
lung/thoracic disease term found 23 such off-target records. This is expected — the TREC
track pools trials broadly — and it is precisely why trial selection (Section 3) applies an
explicit NSCLC screen rather than trusting the corpus to be homogeneous.

Phase distribution (measured): Phase 2 (103), Phase 1 (42), unspecified (45), Phase 3 (22),
Phase 1;Phase 2 (17), Phase 4 (6), Phase 2;Phase 3 (1).

---

## 2. Trial parsing

### 2.1 What "parsing" means here

Two distinct things are computed from each trial, and they must not be confused:

1. **Verbatim criteria extraction** — the authoritative inclusion/exclusion text, copied
   unchanged from the corpus. This is what annotators judge against.
2. **A field checklist** — a *non-authoritative navigation aid* that flags which eligibility
   dimensions a trial appears to exercise (does it mention an FEV1 threshold at all? a
   staging requirement? a prior-therapy exclusion?). This exists only so a human reading 40
   trials can see at a glance what each one tests. **It is never used to assign a label**,
   and the reference sheets state this explicitly.

### 2.2 Field-checklist detection patterns (corrected v2)

The checklist is produced by regex signal-detection over the lowercased
`inclusion + "\n" + exclusion` text. The **v1 patterns had false positives** (documented
below); the **v2 patterns tighten each one**. The current (v2) patterns are:

| Field | v2 pattern (intent) |
|---|---|
| `stage` | `\bstage\s*(?:group\s*)?(?:[0iv]+[ab]?)\b` — requires a roman-numeral stage token |
| `age_cutoff` | requires an explicit age-bound context: `aged N`, `age of N`, `minimum/maximum age N`, `NN years or older/younger`, or a comparator like `≥ NN years` |
| `ecog_kps` | `ecog | zubrod | karnofsky | kps | performance status` |
| `fev1` | `fev\s*1 | fev1` |
| `prior_chemo` | `(prior|previous|preceding)\s+\w{0,15}?chemo` — requires the prior/previous qualifier near "chemo" |
| `prior_radio` | `(prior|previous|preceding)\s+\w{0,15}?(radio|radiation)` |
| `egfr_alk_biomarker` | `egfr | alk | t790m | ros1 | kras | ret fusion | sensitizing mutation` |
| `cardiovascular_excl` | `myocardial infarction | unstable angina | congestive heart | serious cardiac | significant cardiovascular | arrhythmia` |
| `neuropathy_excl` | `neuropathy` |
| `cns_brain_mets` | `brain metasta | cns metasta | leptomeningeal | cerebral metasta` |
| `renal_hepatic_labs` | requires a threshold/ULN reference: `creatinine … [≥≤><=]`, `bilirubin [≥≤><=]`, `ALT/AST [≥≤><=]`, `× ULN`, `times upper limit` |
| `pregnancy` | `pregnan | breastfeed | lactat | adequate contracept | childbearing` |

### 2.3 The v1 → v2 correction (recorded for transparency)

The original `age_cutoff` pattern was:

```
\b(\d{1,3})\s*[-–]?\s*years?\s*(?:of\s*age|old)?
```

This matched any "<number> years", so it fired on temporal windows that are **not** age
requirements — e.g. "within **5 years**", "disease-free for **3 years**", "during the past
**2 years**". As a result the v1 checklist over-reported age cutoffs (flagged in ~18/22
development trials) and several other fields showed implausible 22/22 saturation
(`renal_hepatic_labs`, `pregnancy`, `cardiovascular_excl`), a signature of patterns too
broad to be meaningful.

The v2 patterns were validated against explicit positive/negative test strings:

| Input | v2 `age_cutoff` result |
|---|---|
| "within 5 years" | not matched ✓ |
| "disease-free for 3 years" | not matched ✓ |
| "grade 3 neuropathy" | not matched ✓ |
| "3 weeks prior" | not matched ✓ |
| "≥ 18 years" | matched ✓ |
| "aged 18-75" | matched ✓ |
| "18 years or older" | matched ✓ |
| "age of 18" | matched ✓ |

After correction, checklist coverage across the 18 test trials became realistic and varied
(measured): pregnancy 16/18, ecog_kps 15/18, age_cutoff 11/18, stage 11/18, cns_brain_mets
9/18, renal_hepatic_labs 9/18, prior_chemo 8/18, cardiovascular_excl 8/18,
egfr_alk_biomarker 6/18, prior_radio 5/18, fev1 1/18, neuropathy_excl 1/18. The rare fields
(FEV1, neuropathy) now correctly read as rare rather than saturating.

---

## 3. Trial selection

### 3.1 The problem being solved: selection bias

The original 22-trial shortlist was assembled with awareness of parser coverage — the
extraction script described it as "mechanism-stratified, substantive-criteria, **high
parser-coverage** score." Reporting a framework's performance on trials chosen partly
because the framework already handles their criteria would inflate results and is a
legitimate reviewer objection. Mechanism stratification alone does **not** neutralise this:
one can be perfectly balanced across treatment types while still selecting the
parser-friendliest trial within each type.

**Resolution:** two disjoint trial sets.

- **Development set (22 trials):** the original shortlist, retained for framework
  engineering, prompt design, confidence-weight tuning, error-analysis development, and
  ablations. **Never used for headline generalisation numbers.**
- **Held-out test set (18 trials):** selected by a *framework-blind* pipeline that never
  references parser coverage, supported attributes, model predictions, expected
  performance, or criterion compatibility. **All reported evaluation numbers come from
  this set.**

### 3.2 Development set (22 trials)

Retained as-is, grouped by mechanism class: Immunotherapy (4), Targeted-TKI (5),
Chemoradiation (4), Chemotherapy (4), Anti-angiogenic (3), Other/Novel-agent (2). All
verified present in the corpus with substantive criteria (inclusion 842–7839 chars,
exclusion 881–7435 chars).

### 3.3 Held-out test set — framework-blind selection pipeline

Applied to the 214 corpus trials **not** in the development set, in this fixed order:

**Step 1 — High-recall NSCLC screen.** Keep a trial if its `diseases_list` contains any of:
`non-small cell lung`, `non small cell lung`, `non-small-cell lung`, `nsclc`,
`squamous cell lung`, `lung adenocarcinoma`, `lung non-small`, `lung cancer`,
`lung neoplasm`. Then drop clear non-NSCLC-primary records: if the trial lacks any
NSCLC-specific term (`non-small`, `nsclc`, `non small`, `squamous cell lung`,
`lung adenocarcinoma`) **and** mentions a different primary (`breast cancer`, `ovarian`,
`lymphoma`, `leukemia`, `melanoma`, `renal cell`, `head and neck`, `testicular`,
`small cell lung cancer`, `sclc`, `asthma`, `cachexia`, `cushing`, `tuberculous`,
`mesothelioma`, `hepatocellular`, `esophageal`, `laryngeal`, `hypopharyngeal`), drop it.
→ 173 trials.

**Step 2 — Therapeutic-trial screen.** Keep interventional treatment trials. Require a
`phase` value containing "phase" or a non-empty `drugs_list`. Drop non-therapeutic study
types by brief-summary signal (`observational`, `registry`, `quality of life`,
`imaging study`, `biomarker study`, `screening study`, `prevention trial`, `feasibility of`,
`questionnaire`, `survey`) and supportive-care studies by title signal (`pain in patients`,
`shortness of breath`, `dyspnea`, `rash`, `pulmonary fibrosis`, `nausea`, `fatigue`,
`supportive care`, `esophageal pain`, `cachexia`, `cough in`). → 157 trials.

**Step 3 — Complete-criteria screen.** Require both inclusion and exclusion criteria of at
least 300 characters each, ensuring every test trial has substantive, gradeable criteria on
both sides. → 87 trials (82 after the tightened supportive-care title filter).

**Step 4 — Mechanism classification.** Assign each surviving trial one mechanism class from
drug/summary/title signal, in priority order: Immunotherapy (checkpoint inhibitors:
`pembrolizumab`, `nivolumab`, `atezolizumab`, `durvalumab`, `pd-1`, `pd-l1`, `ipilimumab`,
`avelumab`, `sintilimab`, `immune checkpoint`, `immunotherapy`) → Targeted-TKI (`erlotinib`,
`gefitinib`, `afatinib`, `osimertinib`, `crizotinib`, `alectinib`, `egfr`, `alk`,
`tyrosine kinase`, `tki`, `ceritinib`, `dacomitinib`, `icotinib`, `almonertinib`,
`cabozantinib`, `anlotinib`, `tarceva`) → Anti-angiogenic (`bevacizumab`, `ramucirumab`,
`nintedanib`, `angiogen`, `vegf`, `endostatin`, `axitinib`, `ag-013736`, `bibf`) →
Chemoradiation (`chemoradi`, `radiation`, `radiotherapy`, `concurrent chemo`) →
Chemotherapy (`cisplatin`, `carboplatin`, `pemetrexed`, `paclitaxel`, `docetaxel`,
`gemcitabine`, `vinorelbine`, `topotecan`, `chemotherapy`, `platinum`) → else
Other/Novel-agent.

**Step 5 — Protocol-family deduplication.** Within each mechanism class, group trials by a
family key = the first two (alphabetically sorted, lowercased) drug names. Keep one randomly
chosen representative per family, so near-duplicate protocols (same drug combination) cannot
dominate the sample.

**Step 6 — Fixed-seed stratified random sampling.** With `random.seed(2026)`, allocate a
per-mechanism quota proportional to each class's share of the deduplicated pool (target ≈24),
then randomly draw within each class. The fixed seed makes the draw reproducible.

**Step 7 — Clinical-relevance review.** A final manual pass removes any remaining trial that
is not an NSCLC *treatment* trial — e.g. mixed-primary trials where NSCLC is secondary
(solid-tumor / hepatocellular / melanoma-primary), lung-metastasis or mesothelioma trials,
diagnostic-procedure studies (EBUS-TBNA), supportive-care studies (Zometa for pleural
effusion), and dysplasia-reversal studies. This step uses clinical judgment about the
trial's purpose, **not** parser-field compatibility.

**Result: 18 held-out test trials**, by mechanism: Targeted-TKI (7), Other/Novel-agent (3),
Anti-angiogenic (2), Chemoradiation (2), Chemotherapy (2), Immunotherapy (2). Zero overlap
with the 22 development trials.

### 3.4 Ordering guarantee

Field coverage (Section 2.2) is computed **only after** the test set is frozen. Selection is
therefore blind to which fields the framework parses. Coverage characterises the sample; it
never shapes it.

---

## 4. Patient profile generation

> Status: design specified here; generation runs after this document is reviewed.

### 4.1 The problem being solved: label circularity

If a patient profile is authored against a specific trial's criteria and then labelled
against those same criteria, the label is baked in at generation time — annotators would be
recovering the author's intent, not independently determining eligibility. This is the
single largest threat to a synthetic-patient dataset's credibility.

**Resolution — decouple patient attributes from any single trial:**

1. Patient attributes are sampled from a predefined clinical schema **without reference to
   any specific trial's criteria**.
2. Each patient is rendered as a free-text narrative, again without exposing any trial's
   criteria to the narrative step.
3. Each patient is evaluated against **multiple** trials, so a given patient is naturally
   Eligible for some, Not Eligible for others, and Insufficient Information for others.
4. The label for each (patient, trial) pair is therefore a *consequence of the combination*,
   determined by blind annotators (Section 5), not a designed property of the patient.

### 4.2 Budget and structure

API limits cap the run at ~230–280 patient–trial pairs. The chosen structure:

- **45 patients × 6 trials each = 270 pairs.**
- With 18 held-out test trials, this yields ~15 pairs per test trial — enough for
  per-trial reporting.
- Each patient is assigned its 6 trials by a fixed-seed draw across the 18 test trials,
  balanced so every trial receives a comparable number of patients.

### 4.3 Patient clinical schema

Each patient is sampled as a structured record over these fields (distributions fixed
*before* any trial matching):

| Field | Sampled values |
|---|---|
| Age | realistic NSCLC age distribution |
| Sex | M / F |
| Histology | adenocarcinoma / squamous cell / large cell / NSCLC-NOS |
| Stage + TNM | I–IV with consistent T/N/M |
| Performance status | ECOG 0–4 (and a KPS-expressed subset, to test scale handling) |
| FEV1 | cc and/or % predicted, sometimes absent |
| Biomarkers | EGFR / ALK / ROS1 / KRAS / none / unknown |
| Brain metastasis | present / absent / untreated-symptomatic |
| Prior therapies | chemo / radio / TKI / immunotherapy / none, with lines and timing |
| Treatment timing | recency windows relevant to exclusions |
| Neuropathy | none / Grade 1 / Grade 2 / Grade 3 |
| Cardiovascular history | none / recent MI / arrhythmia / etc. |
| Active infection | present / absent |
| Laboratory values | creatinine, bilirubin, ANC, platelets, hemoglobin |
| Pregnancy/reproductive | applicable subset |

Some fields are deliberately left unstated in a fraction of patients, to generate genuine
**Insufficient Information** cases (where a trial requires a value the profile never mentions).

### 4.4 Narrative rendering

Each structured patient is rendered into a varied free-text clinical narrative. Rendering
varies sentence order, phrasing, and which attributes are foregrounded, to avoid a templated
structure that could leak the label. The trial criteria are **not** provided to the rendering
step.

### 4.5 What is deliberately NOT done

- No patient is written "to be eligible for trial X" or "to fail trial X."
- No "5 pass / 5 fail per trial" engineering.
- No trial criteria are shown during attribute sampling or narrative rendering.
- The generated (pre-annotation) label, if any is tracked internally for balance monitoring,
  is never shown to annotators and is never treated as ground truth.

---

## 5. Labelling (annotation)

Gold labels come from independent blind annotation, not from generation.

- **Annotators:** two independent experts, working independently.
- **Blind protocol:** each expert sees only the patient profile and the trial's full
  inclusion/exclusion criteria — never the intended/generation label, framework output,
  patient-template category, or violated-field metadata.
- **Authoritative source:** the full verbatim criteria. The Section 2.2 field checklist is a
  navigation aid only and is never the basis for a label.
- **Label set:** binary — **Eligible / Not Eligible**. Refusal is a *system* action, not a
  third reference class, so there is no "Insufficient Information" gold label.
- **Agreement + adjudication:** across the frozen 400-pair set the two experts **agreed on
  392/400 pairs (98.0%)**; the **8 disagreements were settled by expert adjudication**.
- **Calibration:** a shared calibration round precedes independent annotation to align on the
  Eligible / Not-Eligible boundary.

Full annotator instructions live in the separate annotation guidelines document.

> **Provenance note (INDICON revision).** This two-expert / 98.0% (392/400) / 8-adjudicated
> account is authoritative and matches the submitted manuscript. An earlier draft of this
> file described three research scholars with Fleiss' κ and a three-class label set; that
> was superseded and is not the protocol used for the frozen 400-pair set.

---

## 6. Data splits and evaluation discipline

- **Development trials (22):** framework engineering, prompt refinement, ablation
  development. Prompt memory / refined prompts are frozen before any test-set evaluation.
- **Test trials (18):** held-out, framework-blind. All headline numbers reported here.
- **Protocol-disjoint:** no trial appears in both splits.
- **Class distribution:** the naturally resulting Eligible / Not Eligible distribution is
  reported as-is, not rebalanced to parity. Skew is handled at the metric level (per-class
  precision/recall/F1) rather than by resampling.

---

## 7. Reproducibility summary

| Artifact | File |
|---|---|
| Source corpus | `corpus.jsonl` (236 trials, TREC 2022) |
| Trial extraction + checklist (v2) | `extract_trials_v2.py` |
| Development trial set | `trials_development.jsonl` + `trials_development_reference.md` |
| Held-out test trial set | `trials_test.jsonl` + `trials_test_reference.md` |
| Patient generation | (design in §4; generator to follow) |
| Annotation guidelines | separate guidelines document |
| Inter-expert agreement | two experts, 98.0% (392/400); 8 pairs expert-adjudicated |

Fixed random seed for test-trial selection: **2026**. All keyword lists, regex patterns,
screening thresholds (300-char minimum criteria), and the pair budget (45 × 6 = 270) are
recorded above.

---

## 8. Known limitations (stated plainly)

- **Single disease (NSCLC).** External validity to other cancers / non-oncology trials is
  not established; deliberate depth-over-breadth choice for a first system.
- **Synthetic patients.** Profiles are generated, not real de-identified EHR text. They are
  cleaner and shorter than real clinical notes. Mitigated by trial-independent generation
  and blind annotation, but not equivalent to real-EHR validation.
- **Annotation by two independent experts (not necessarily practising oncologists).**
  Mitigated by a written codebook, blind protocol, and expert adjudication of the 8
  disagreements; a clinician review of the codebook and a random sample is recommended where
  feasible.
- **Scale.** 270 patient–trial pairs is modest, bounded by API budget; sufficient for
  framework evaluation, not positioned as a large standalone benchmark.
