# Data

Synthetic non-small-cell lung cancer (NSCLC) patient–trial pairs with expert eligibility labels, and the real trial criteria they are paired with. Full construction details: [`DATASET_CREATION.md`](DATASET_CREATION.md).

| Path | Content |
|---|---|
| `pairs/testing_data.csv` | **Test set**: 270 pairs, 45 patients, 18 trials, 69 eligible. Used once for the frozen SPLIT-Match run |
| `pairs/dev_train.csv`, `pairs/dev_validation.csv` | Development set: 130 pairs, 26 patients, 22 trials (stratified 80/20 split of the same pairs) |
| `pairs/split_report.txt` | Split verification: no patient or trial overlap between development and test |
| `trials/trials_test.jsonl`, `trials/trials_development.jsonl` | Verbatim inclusion and exclusion criteria of the 18 test and 22 development trials |
| `trials/trials_development_expansion.jsonl` | 11 further trials used only for the fresh compiler audit |
| `trials/corpus.jsonl` | 236 lung-cancer trials from the TREC 2022 Clinical Trials corpus (as redistributed with TrialGPT), from which trials were drawn |
| `expansion_patients/` | 25 fresh synthetic patients used for the extraction check (`patients_expansion.jsonl`) and their generation key |
| `tooling/` | Trial extraction, patient generator (`generate_patients.py`, also used for the re-identification simulation) and expansion selection |

Each row of the pair files has `pair_id`, `patient_id`, `trial_id`, `patient_profile` (the note), `inclusion_criteria`, `exclusion_criteria` and `label_final` (Eligible / Not Eligible).

**Provenance and ethics.** Patient attributes were sampled without reference to any trial and rendered as short narratives (median 124 words). Two independent experts labelled every pair without seeing the generation details (agreement 98.0%, disagreements resolved by discussion). No real patient data were used. Trial criteria are public records from ClinicalTrials.gov, traceable by NCT identifier. The benchmark was introduced in our earlier study (Arya et al., IEEE INDICON 2026), which also evaluated systems on this test split.
