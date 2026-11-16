| trial | atom | type | pol | downgraded | compiled | source line | audit (OK/WRONG) |
|---|---|---|---|---|---|---|---|
| NCT00065182 | c0A1 | CMP | inc | False | age at least 18 years | At least 18 years old | |
| NCT00065182 | c0A2 | IN | inc | False | cancer_type is one of nsclc | Confirmed advanced non-small cell lung carcinoma (NSCLC) | |
| NCT00065182 | c0A3 | IN | inc | False | stage_group is one of IIIB, IIIC, IV | Confirmed advanced non-small cell lung carcinoma (NSCLC) | |
| NCT00065182 | c0A4 | COUNT | inc | False | number of prior chemo lines/regimens is at least 1 | Received one prior chemotherapy for metastatic NSCLC excluding TAXOTERE or HYCAMTIN. In addition, su | |
| NCT00065182 | c0A5 | HAS | exc | False | patient has had prior taxotere/hycamtin chemo | Received one prior chemotherapy for metastatic NSCLC excluding TAXOTERE or HYCAMTIN. In addition, su | |
| NCT00065182 | c0A7 | SINCE | inc | True | at least 0.69 months have passed since prior chemo/radio/tki/targeted_other/othe | Full recovery and at least 21 days from prior treatment for NSCLC; 42 days from treatment with mitom | |
| NCT00065182 | c0A8 | SINCE | inc | True | at least 1.38 months have passed since prior mitomycin/nitrosureas | Full recovery and at least 21 days from prior treatment for NSCLC; 42 days from treatment with mitom | |
| NCT00065182 | c0A9 | SINCE | inc | True | at least 0.99 months have passed since prior egfr/angiogenesis | Full recovery and at least 21 days from prior treatment for NSCLC; 42 days from treatment with mitom | |
| NCT00065182 | c0A10 | SINCE | inc | False | at least 0.69 months have passed since prior surgery | At least 3 weeks since last major surgery (a lesser period is acceptable if deemed in the best inter | |
| NCT00065182 | c0A11 | SINCE | inc | False | at least 0.23 months have passed since prior radio | At least 7 days since prior radiotherapy. | |
| NCT00065182 | c0A12 | CMP | inc | False | life_expectancy_months at least 3 months | A probable life expectance of at least 3 months. | |
| NCT00065182 | c0A15 | IN | exc | True | brain_mets is one of untreated_or_symptomatic | Symptoms of brain metastases requiring treatment with steroids. | |
| NCT00065182 | c0A16 | IS | exc | False | active_infection is present | Active infection. | |
| NCT00065182 | c0A18 | HAS | exc | True | patient has had prior chemo/io/radio/other | Ongoing or planned chemotherapy (other than treatment during this study), immunotherapy, radiotherap | |
| NCT00065182 | c0A19 | WITHIN | exc | True | patient received prior other within the past 0.99 months | Use of investigational drug within 30 days or 5 half-lives prior to the first dose of study medicati | |
| NCT00065182 | c0A20 | IS | exc | False | pregnant is present | Women who are pregnant or lactating. | |
| NCT00065182 | c0A22 | HAS | exc | True | patient has had prior taxotere/hycamtin chemo | Prior treatment with or history of allergic reaction to either HYCAMTIN or TAXOTERE. | |
| NCT00065182 | c0A23 | IS | exc | True | steroids_systemic is absent | Subjects who cannot receive steroid premedication. | |
| NCT00408226 | c0A2 | ANY | inc | True | ((stage_group is one of IIIB AND malignant_effusion is present) OR (stage_group  | Phase 2 portion: Current diagnosis of Stage IIIb (due to malignant pleural effusion or supraclavicul | |
| NCT00408226 | c0A3 | HAS | inc | True | patient has had prior surgery/radio | (i) Patient has received maximally feasible surgical resection and/or radiotherapy for initial disea | |
| NCT00408226 | c0A5 | IS | inc | False | measurable_disease is present | (iii) Radiographic or physical examination evidence of at least one site of unidimensionally-measura | |
| NCT00408226 | c0A6 | CMP | inc | False | age at least 18 years | Age ≥ 18 years. | |
| NCT00408226 | c0A7 | CMP | inc | False | ecog at most 1 | ECOG performance status of 0 or 1. | |
| NCT00408226 | c0A10 | CMP | inc | False | hemoglobin_g_dl at least 9 g/dL | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A11 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A12 | CMP | inc | False | platelets_k_ul at least 75 10^3/uL | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A13 | CMP | inc | False | creatinine_xuln at most 1.5 | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A14 | CMP | inc | False | crcl_ml_min at least 45 mL/min | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A15 | CMP | inc | False | ast_xuln at most 2.5 xULN | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A16 | CMP | inc | False | albumin_g_dl at least 3.5 g/dL | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A17 | CMP | inc | False | bilirubin_xuln at most 1 | Hemoglobin ≥ 9 g/dL Absolute neutrophil count ≥ 1.5 x 109/L Platelet count ≥ 75 x 109/L Serum creati | |
| NCT00408226 | c0A21 | WITHIN | exc | False | patient received prior surgery within the past 0.92 months | Administration of cancer-specific therapy within the following periods prior to study drug initiatio | |
| NCT00408226 | c0A22 | WITHIN | exc | False | patient received prior radio within the past 0.69 months | Administration of cancer-specific therapy within the following periods prior to study drug initiatio | |
| NCT00408226 | c0A23 | WITHIN | exc | False | patient received prior chemo within the past 0.69 months | Administration of cancer-specific therapy within the following periods prior to study drug initiatio | |
| NCT00408226 | c0A24 | WITHIN | exc | True | patient received prior egfr tki within the past 0.46 months | Administration of cancer-specific therapy within the following periods prior to study drug initiatio | |
| NCT00408226 | c0A25 | IS | exc | False | pregnant is present | Pregnant or breast-feeding women. Female patients must be postmenopausal, surgically sterile or they | |
| NCT00408226 | c0A27 | IN | exc | True | brain_mets is one of untreated_or_symptomatic | Known CNS or leptomeningeal metastases unless treated, clinically stable and not requiring steroids. | |
| NCT00977470 | c0A0 | IN | inc | False | cancer_type is one of nsclc | Pathologically confirmed diagnosis of non-small cell lung cancer | |
| NCT00977470 | c0A1 | IN | inc | False | stage_group is one of IV | Stage IV disease by the American Joint Committee on Cancer/IASLC 7th edition proposed edition stagin | |
| NCT00977470 | c0A4 | CMP | inc | False | age at least 18 years | Age equal to or greater than 18 years | |
| NCT00977470 | c0A5 | IS | inc | False | measurable_disease is present | Measurable disease by RECIST criteria, defined as the presence of at least one lesion that can be ac | |
| NCT00977470 | c0A6 | CMP | inc | False | ecog at most 2 | ECOG Performance status of 0, 1 or 2 | |
| NCT00977470 | c0A7 | WITHIN | exc | True | patient received prior radio/surgery within the past 0.46 months | Since prior radiation or surgery, 14 days or more must have elapsed before starting protocol treatme | |
| NCT00977470 | c0A8 | HAS | exc | False | patient has had prior erlotinib/gefitinib tki | No prior treatment with erlotinib, gefitinib, or other small molecule EGFR-TKIs. Prior treatment in  | |
| NCT00977470 | c0A9 | SINCE | inc | False | at least 12.00 months have passed since prior erlotinib/gefitinib tki | No prior treatment with erlotinib, gefitinib, or other small molecule EGFR-TKIs. Prior treatment in  | |
| NCT00977470 | c0A13 | IN | exc | False | brain_mets is one of untreated_or_symptomatic | Symptomatic CNS metastases or newly diagnosed CNS metastases that have not yet been definitively tre | |
| NCT00977470 | c0A18 | IS | exc | False | pregnant is present | Patients who are pregnant or breastfeeding. Female subjects of childbearing potential and male subje | |
| NCT00977470 | c0A22 | WITHIN | exc | True | patient received prior other within the past 0.99 months | Use of any non-FDA approved or investigational agent in 30 days or less of enrolling onto the trial, | |
| NCT00977470 | c0A24 | CMP | exc | True | life_expectancy_months below 3 months | Life expectancy of less than 12 weeks | |
| NCT01542437 | c0A0 | IN | inc | False | cancer_type is one of nsclc | Diagnosis of lung cancer non-small cell (stage IIIB or IV) inoperable, locally advanced, recurrent o | |
| NCT01542437 | c0A1 | IN | inc | False | stage_group is one of IIIB, IV | Diagnosis of lung cancer non-small cell (stage IIIB or IV) inoperable, locally advanced, recurrent o | |
| NCT01542437 | c0A2 | IS | inc | False | measurable_disease is present | The patient must present evidence of measurable disease. | |
| NCT01542437 | c0A3 | CMP | inc | False | age at least 18 years | 18 years of age or older. | |
| NCT01542437 | c0A4 | CMP | inc | False | ecog at most 2 | ECOG performance status of 0-2 | |
| NCT01542437 | c0A5 | CMP | inc | False | life_expectancy_months at least 2.762 months | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A6 | COUNT | inc | True | number of prior platinum chemo lines/regimens is at least 1 | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A7 | SINCE | inc | False | at least 0.46 months have passed since prior chemo | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A8 | SINCE | inc | False | at least 0.92 months have passed since prior surgery | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A9 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A10 | CMP | inc | False | platelets_k_ul above 100 10^3/uL | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A11 | CMP | inc | False | bilirubin_xuln at most 1.5 | Life expectancy at least 12 weeks. lung cancer patients with advanced non-small cell, stage IIIB / I | |
| NCT01542437 | c0A12 | CMP | inc | False | ast_xuln at most 2 xULN | AST and / or ALT ≤ 2 ULN (or ≤ 5 x ULN when clearly attributable to the presence of liver metastases | |
| NCT01542437 | c0A13 | CMP | inc | False | alt_xuln at most 2 xULN | AST and / or ALT ≤ 2 ULN (or ≤ 5 x ULN when clearly attributable to the presence of liver metastases | |
| NCT01542437 | c0A14 | ANY | inc | False | (creatinine_xuln at most 1.5 OR crcl_ml_min at least 60 mL/min) | Serum creatinine ≤ 1.5 (ULN) or creatinine clearance ≥ 60ml/min | |
| NCT01542437 | c0A16 | IF | inc | True | IF (sex is one of female) THEN (pregnant is absent) | Of all women of childbearing potential should be obtained a negative pregnancy test within 72 hours  | |
| NCT01542437 | c0A19 | IS | exc | False | active_infection is present | Any unstable systemic disease (including active infection, grade 4 hypertension, unstable angina, co | |
| NCT01542437 | c0A20 | IS | exc | False | unstable_angina is present | Any unstable systemic disease (including active infection, grade 4 hypertension, unstable angina, co | |
| NCT01542437 | c0A21 | IS | exc | False | chf is present | Any unstable systemic disease (including active infection, grade 4 hypertension, unstable angina, co | |
| NCT01542437 | c0A22 | HAS | exc | False | patient has had prior egfr tki | Pre-treatment with systemic anti-tumor therapy with EGFR inhibitors (tyrosine kinase inhibitors). | |
| NCT01542437 | c0A23 | IF | exc | True | IF (mi_history is present) THEN (mi_months_ago at most 60 months) | Any other malignancy within the previous 5 years (except for carcinoma in situ of the cervix or skin | |
| NCT01542437 | c0A24 | IN | exc | False | brain_mets is one of untreated_or_symptomatic | Excluded patients with brain metastases or spinal cord compression of newly diagnosed and / or have  | |
| NCT01703091 | c0A0 | IN | inc | False | cancer_type is one of nsclc | Non-Small Cell Lung Cancer disease | |
| NCT01703091 | c0A1 | ANY | inc | False | (stage_group is one of IV OR disease_status is one of recurrent) | Clinical stage IV or recurrent disease | |
| NCT01703091 | c0A2 | COUNT | inc | True | number of prior platinum lines/regimens is at least 1 | One prior first-line platinum-based chemotherapy regimen with or without maintenance therapy | |
| NCT01703091 | c0A3 | IF | inc | False | IF (histology is not squamous) THEN (EGFR mutation status known) | For Non-Small Cell Lung Cancer (NSCLC) tumors other than squamous cell histology, the epidermal grow | |
| NCT01703091 | c0A4 | IF | inc | True | IF (egfr is one of positive) THEN (number of prior egfr tki lines/regimens is eq | For participants with activating epidermal growth factor receptor (EGFR) mutation only, prior epider | |
| NCT01703091 | c0A5 | CMP | inc | False | ecog at most 1 | Eastern Cooperative Oncology Group (ECOG) Performance Status (PS) 0 or 1 | |
| NCT01703091 | c0A6 | IS | inc | False | measurable_disease is present | Measurable disease as defined by Response Evaluation Criteria in Solid Tumors (RECIST) version RECIS | |
| NCT01703091 | c0A8 | CMP | inc | False | life_expectancy_months at least 3 months | Estimated life expectancy of at least 3 months. | |
| NCT01703091 | c0A9 | WITHIN | exc | True | patient received prior surgery within the past 0.92 months | Have undergone major surgery within 28 days prior to randomization or have planned major surgery dur | |
| NCT01703091 | c0A11 | HAS | exc | True | patient has had prior chemo/radio/tki/io/antiangiogenic/targeted_other/systemic/ | Receiving concurrent treatment with other anticancer therapy | |
| NCT01703091 | c0A19 | IS | exc | False | chf is present | Has clinically relevant congestive heart failure | |
| NCT02038699 | c0A0 | IN | inc | True | cancer_type is one of nsclc, other | Patients must have histologically confirmed glioblastoma multiforme, triple-negative breast cancer,  | |
| NCT02038699 | c0A1 | IN | inc | True | stage_group is one of IV | Patients must have histologically confirmed glioblastoma multiforme, triple-negative breast cancer,  | |
| NCT02038699 | c0A3 | IS | inc | False | measurable_disease is present | Patients must have measurable disease, defined as at least one lesion that can be accurately measure | |
| NCT02038699 | c0A5 | WITHIN | exc | True | patient received prior chemo within the past 0.92 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A6 | WITHIN | exc | True | patient received prior radio within the past 0.92 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A7 | WITHIN | exc | True | patient received prior systemic within the past 0.92 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A8 | WITHIN | exc | True | patient received prior other within the past 0.92 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A9 | WITHIN | exc | True | patient received prior alkylating chemo within the past 1.38 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A10 | WITHIN | exc | True | patient received prior surgery within the past 1.38 months | Patients are eligible for enrollment if they have not had prior chemotherapy, radiotherapy, anticanc | |
| NCT02038699 | c0A12 | CMP | inc | False | age at least 18 years | Age ≥18 years. | |
| NCT02038699 | c0A13 | CMP | inc | False | ecog at most 2 | ECOG performance status ≤ 2 (Karnofsky ≥ 60%, see Appendix A). | |
| NCT02038699 | c0A14 | CMP | inc | True | kps at least 60 | ECOG performance status ≤ 2 (Karnofsky ≥ 60%, see Appendix A). | |
| NCT02038699 | c0A15 | CMP | inc | False | life_expectancy_months above 2.301 months | Life expectancy of greater than 10 weeks. | |
| NCT02038699 | c0A16 | CMP | inc | False | wbc_k_ul at least 3 10^3/uL | Patients must have normal organ and marrow function as defined below: leukocytes ≥ 3,000/mcL absolut | |
| NCT02038699 | c0A17 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | Patients must have normal organ and marrow function as defined below: leukocytes ≥ 3,000/mcL absolut | |
| NCT02038699 | c0A18 | CMP | inc | False | platelets_k_ul at least 100 10^3/uL | Patients must have normal organ and marrow function as defined below: leukocytes ≥ 3,000/mcL absolut | |
| NCT02038699 | c0A19 | CMP | inc | False | hemoglobin_g_dl above 8 g/dL | Patients must have normal organ and marrow function as defined below: leukocytes ≥ 3,000/mcL absolut | |
| NCT02038699 | c0A20 | CMP | inc | False | bilirubin_xuln below 2 | Patients must have normal organ and marrow function as defined below: leukocytes ≥ 3,000/mcL absolut | |
| NCT02038699 | c0A21 | ANY | inc | False | ((ast_xuln at most 2.5 xULN AND alt_xuln at most 2.5 xULN) OR crcl_ml_min at lea | AST (SGOT)/ALT (SGPT) ≤2.5 × upper limit of normal creatinine OR creatinine clearance ≥60 mL/min/1.7 | |
| NCT02038699 | c0A25 | HAS | exc | False | patient has had prior bevacizumab antiangiogenic | Patients who have received bevacizumab therapy. | |
| NCT02038699 | c0A26 | IN | exc | True | brain_mets is one of untreated_or_symptomatic | Patients with known brain metastases will be excluded from the phase I portion of the study. In the  | |
| NCT02038699 | c0A27 | IF | exc | True | IF (brain_mets is one of treated_stable) THEN ((life_expectancy_months at least  | Patients with known brain metastases will be excluded from the phase I portion of the study. In the  | |
| NCT02038699 | c0A29 | IS | exc | True | active_infection is present | Uncontrolled intercurrent illness including, but not limited to, ongoing or active infection or psyc | |
| NCT02038699 | c0A31 | IS | exc | False | pregnant is present | Pregnant women are excluded from this study because ONC201 is novel agent with unknown potential for | |
| NCT02038699 | c0A34 | IN | exc | False | arrhythmia is one of uncontrolled | Patients with known history of cardiac arrhythmias including atrial fibrillation, tachyarrhythmias o | |
| NCT02038699 | c0A35 | IS | exc | False | chf is present | Patients with known history of cardiac arrhythmias including atrial fibrillation, tachyarrhythmias o | |
| NCT02357992 | c0A0 | IN | inc | False | cancer_type is one of nsclc | Histological confirmation of non-small cell cancer will be required by either biopsy or cytology. Th | |
| NCT02357992 | c0A1 | IN | inc | True | histology is one of squamous, adenocarcinoma, large_cell, nos | Histological confirmation of non-small cell cancer will be required by either biopsy or cytology. Th | |
| NCT02357992 | c0A7 | CMP | inc | True | fev1_pct above 40 % predicted | Patients must be considered a candidate for surgical resection of the primary tumor. Standard justif | |
| NCT02357992 | c0A9 | CMP | inc | False | age at least 18 years | Patients must be >/= 18 years of age. | |
| NCT02357992 | c0A10 | CMP | inc | False | ecog at most 2 | The patient's Zubrod performance status must be Zubrod 0-2. | |
| NCT02357992 | c0A19 | IN | exc | True | tnm_m is one of M1 | Direct evidence of regional or distant metastases after appropriate staging studies, or synchronous  | |
| NCT02357992 | c0A21 | HAS | exc | False | patient has had prior radio to the chest | Previous lung or mediastinal radiotherapy. | |
| NCT02357992 | c0A23 | IS | exc | False | pregnant is present | Pregnant or lactating women, as treatment involves unforeseeable risks to the embryo or fetus. | |
| NCT02357992 | c0A3+any | ANY | inc | True | (tnm_t is one of T1a, T1b OR tnm_n is one of N0 OR tnm_m is one of M0) | Eligible patients must have appropriate staging studies identifying them as specific subsets of the  | |
| NCT03022500 | c0A0 | CMP | inc | False | age at least 20 years | Age ≥ 20 years | |
| NCT03022500 | c0A1 | CMP | inc | False | ecog at most 1 | ECOG PS ≤1 | |
| NCT03022500 | c0A2 | IN | inc | False | cancer_type is one of nsclc | Patients with histologically confirmed NSCLC with the histology of sarcomatoid carcinoma (WHO criter | |
| NCT03022500 | c0A4 | ANY | inc | False | (stage_group is one of IV OR disease_status is one of recurrent) | Initial metastatic cases or recurrent cases after curative treatment (any chemotherapy line is allow | |
| NCT03022500 | c0A5 | IS | inc | False | measurable_disease is present | A patient with at least one measurable lesion of which the diameter is confirmed to be ≥ 10mm in spi | |
| NCT03022500 | c0A7 | IN | inc | True | brain_mets is one of none, treated_stable | If patients have brain metastasis with neurological symptom, they should be stabilized neurologicall | |
| NCT03022500 | c0A8 | IS | inc | True | steroids_systemic is absent | If patients have brain metastasis with neurological symptom, they should be stabilized neurologicall | |
| NCT03022500 | c0A9 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A10 | CMP | inc | False | platelets_k_ul at least 100 10^3/uL | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A11 | CMP | inc | False | ast_xuln at most 2.5 xULN | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A12 | CMP | inc | False | alt_xuln at most 2.5 xULN | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A13 | CMP | inc | False | bilirubin_xuln at most 1.5 | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A14 | CMP | inc | False | creatinine_xuln at most 1 | Adequate hematologic (neutrophil count ≥ 1,500 cells/mm3, platelets ≥ 100,000 cells/mm3), hepatic (t | |
| NCT03022500 | c0A17 | CMP | inc | False | life_expectancy_months at least 3 months | Expected survival ≥ 3 months | |
| NCT03022500 | c0A18 | IF | inc | True | IF (sex is one of female) THEN (((age at least 60 years AND No menses for ≥1 yea | Female subjects must either be of non-reproductive potential (ie, post-menopausal by history: ≥60 ye | |
| NCT03022500 | c0A19 | IS | exc | True | measurable_disease is absent | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A20 | IS | exc | True | steroids_systemic is present | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A23 | IN | exc | False | brain_mets is one of untreated_or_symptomatic | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A25 | IS | exc | True | autoimmune_active is present | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A26 | HAS | exc | False | patient has had prior pd-1/pd-l1/pd-l2/ctla4 io | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A27 | IS | exc | False | active_infection is present | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A33 | IS | exc | False | pregnant is present | A patient with no measurable disease chronic systemic steroid therapy or on any other form of immuno | |
| NCT03022500 | c0A38 | WITHIN | exc | True | patient received prior chemo/io/tki/antiangiogenic/targeted_other/systemic/radio | Receipt of the last dose of anti-cancer therapy (chemotherapy, immunotherapy, endocrine therapy, tar | |
| NCT03022500 | c0A40 | IS | exc | False | chf is present | Uncontrolled intercurrent illness including, but not limited to, ongoing or active infection, sympto | |
| NCT03022500 | c0A41 | IS | exc | False | unstable_angina is present | Uncontrolled intercurrent illness including, but not limited to, ongoing or active infection, sympto | |
| NCT03022500 | c0A42 | IN | exc | False | arrhythmia is one of uncontrolled | Uncontrolled intercurrent illness including, but not limited to, ongoing or active infection, sympto | |
| NCT03053804 | c0A0 | CMP | inc | False | age above 20 years | Age: > 20 years old. | |
| NCT03053804 | c0A1 | IN | inc | True | cancer_type is one of nsclc, sclc | Patients have confirmed lung cancer by histopathological methods (fiber, bronchoscopy, lung biopsy,  | |
| NCT03053804 | c0A7 | IS | exc | False | pregnant is present | Pregnancy. | |
| NCT03053804 | c0A8 | CMP | exc | False | age below 20 years | Age < 20 years old. | |
| NCT03087448 | c0A0 | CMP | inc | False | age at least 18 years | Age 18 years old or older. | |
| NCT03087448 | c0A2 | IF | inc | True | IF (sex is one of female) THEN (pregnant is absent) | Women of childbearing potential must have a negative serum pregnancy test within 3 days prior to Cyc | |
| NCT03087448 | c0A3 | IN | inc | False | cancer_type is one of nsclc | Patients must have histologically or cytological confirmed stage IIIB or IV non-small cell lung canc | |
| NCT03087448 | c0A4 | IN | inc | False | stage_group is one of IIIB, IV | Patients must have histologically or cytological confirmed stage IIIB or IV non-small cell lung canc | |
| NCT03087448 | c0A5 | ANY | inc | False | (alk is one of positive OR ros1 is one of positive) | Documented ALK-rearrangement (or ROS1 rearrangement for phase I only) break-apart fluorescence in si | |
| NCT03087448 | c0A6 | IS | inc | False | measurable_disease is present | Measurable disease defined by RECIST 1.1 criteria | |
| NCT03087448 | c0A7 | CMP | inc | False | ecog at most 2 | Eastern Cooperative Oncology Group (ECOG) Performance status of 0-2. | |
| NCT03087448 | c0A8 | CMP | inc | False | life_expectancy_months at least 3 months | Life expectancy of at least 3 months. | |
| NCT03087448 | c0A11 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | Absolute neutrophil count (ANC) ≥ 1.5 x 109/L | |
| NCT03087448 | c0A12 | CMP | inc | False | hemoglobin_g_dl at least 9 g/dL | Hemoglobin (Hgb) ≥ 9 g/dL | |
| NCT03087448 | c0A13 | CMP | inc | False | platelets_k_ul at least 75 10^3/uL | Platelets ≥ 75 x 109/L | |
| NCT03087448 | c0A15 | ANY | inc | False | (creatinine_mg_dl at most 1.5 mg/dL OR crcl_ml_min at least 30 mL/min) | Serum creatinine ≤ 1.5 mg/dL and /or calculated creatinine clearance (using Cockcroft-Gault formula) | |
| NCT03087448 | c0A16 | CMP | inc | False | albumin_g_dl at least 2.5 g/dL | Albumin 2.5 g/dL | |
| NCT03087448 | c0A17 | ANY | inc | False | (bilirubin_xuln at most 1.5 OR If the patient has Gilbert's syndrome, total bili | Total bilirubin ≤ 1.5 x ULN, except for patients with Gilbert's syndrome who may be included if tota | |
| NCT03087448 | c0A18 | ANY | inc | False | ((ast_xuln at most 2.5 xULN AND alt_xuln at most 2.5 xULN) OR If the patient has | Aspartate transaminase (AST) ≤ 2.5 x ULN; alanine transaminase (ALT) ≤ 2.5 x ULN, except for patient | |
| NCT03087448 | c1A8 | IN | inc | False | cancer_type is one of nsclc | Documented ALK-rearranged stage IIIB or IV NSCLC and: | |
| NCT03087448 | c1A9 | IN | inc | False | alk is one of positive | Documented ALK-rearranged stage IIIB or IV NSCLC and: | |
| NCT03087448 | c1A10 | IN | inc | False | stage_group is one of IIIB, IV | Documented ALK-rearranged stage IIIB or IV NSCLC and: | |
| NCT03087448 | c1A11 | HAS | exc | True | patient has had prior tki | Cohort A: No prior ALK inhibitor therapy (prior chemotherapy or immunotherapy is allowed). | |
| NCT03087448 | c1A12 | HAS | inc | False | patient has had prior crizotinib tki | Cohort B: Prior treatment with crizotinib and documented disease progression by RECIST 1.1 criteria. | |
| NCT03087448 | c1A13 | IN | inc | True | disease_status is one of progressed_after_prior | Cohort B: Prior treatment with crizotinib and documented disease progression by RECIST 1.1 criteria. | |
| NCT03087448 | c1A14 | HAS | inc | False | patient has had prior ceritinib/alectinib/loratinib/brigatinib tki | Cohort C: Prior treatment with 2nd generation ALKi (e.g. ceritinib, alectinib, loratinib, or brigati | |
| NCT03087448 | c1A15 | IN | inc | True | disease_status is one of progressed_after_prior | Cohort C: Prior treatment with 2nd generation ALKi (e.g. ceritinib, alectinib, loratinib, or brigati | |
| NCT03087448 | c1A16 | ANY | inc | True | ((cancer_type is one of nsclc AND alk is one of positive AND stage_group is one  | Specific inclusion criteria for the phase II dose expansion cohorts: / Documented ALK-rearranged sta | |
| NCT03087448 | c1A19 | WITHIN | exc | False | patient received prior radio to the chest within the past 0.92 months | Patient who has received thoracic radiotherapy to lung fields ≤4 weeks prior to starting the study t | |
| NCT03087448 | c1A20 | WITHIN | exc | False | patient received prior radio within the past 0.46 months | Patient who has received thoracic radiotherapy to lung fields ≤4 weeks prior to starting the study t | |
| NCT03087448 | c1A22 | WITHIN | exc | True | patient received prior systemic within the past 0.69 months | Prior systemic anti-cancer treatment (chemotherapy, immunotherapy, biologic therapy, vaccine therapy | |
| NCT03087448 | c1A23 | WITHIN | exc | False | patient received prior chemo within the past 0.46 months | Prior systemic anti-cancer treatment (chemotherapy, immunotherapy, biologic therapy, vaccine therapy | |
| NCT03087448 | c2A6 | IS | exc | False | pregnant is present | Pregnant or nursing (lactating) women, where pregnancy is defined as the state of a female after con | |
| NCT03087448 | c3A1 | IN | exc | True | brain_mets is one of untreated_or_symptomatic | Symptomatic brain metastases or leptomeningeal (LM) disease requiring corticosteroids for symptom ma | |
| NCT03602027 | c0A0 | CMP | inc | False | age at least 18 years | Be≥18 years of age on the day of signing informed consent and With good compliance and agree to acce | |
| NCT03602027 | c0A2 | IN | inc | False | cancer_type is one of nsclc | Patients with histologic or cytologic confirmation of advanced or metastatic NSCLC with stage III or | |
| NCT03602027 | c0A3 | IN | inc | False | stage_group is one of III, IV | Patients with histologic or cytologic confirmation of advanced or metastatic NSCLC with stage III or | |
| NCT03602027 | c0A4 | SINCE | inc | False | at least 6.00 months have passed since prior chemo (adjuvant/neoadjuvant setting | Patients with histologic or cytologic confirmation of advanced or metastatic NSCLC with stage III or | |
| NCT03602027 | c0A5 | IN | inc | False | egfr is one of positive | Epidermal Growth Factor Receptor(EGFR)mutations confirmed by molecular detection (including, but not | |
| NCT03602027 | c0A6 | HAS | exc | False | patient has had prior chemo | Patients have not been received systematic treatment，including chemotherapy and EGFR -TKIs（Tyrosine  | |
| NCT03602027 | c0A7 | HAS | exc | False | patient has had prior tki | Patients have not been received systematic treatment，including chemotherapy and EGFR -TKIs（Tyrosine  | |
| NCT03602027 | c0A8 | IS | inc | False | measurable_disease is present | There were at least one target lesions in the past three months has not yet accepted radiotherapy, a | |
| NCT03602027 | c0A9 | HAS | exc | False | patient has had prior radio | There were at least one target lesions in the past three months has not yet accepted radiotherapy, a | |
| NCT03602027 | c0A11 | CMP | inc | False | life_expectancy_months at least 3 months | Life expectancy ≥3 months. | |
| NCT03602027 | c0A12 | ANY | inc | True | (ecog equal to 0 OR ecog equal to 2) | Have a performance status of 0 or 2 on the Eastern Cooperative Oncology Group (ECOG) Performance Sta | |
| NCT03602027 | c0A15 | CMP | inc | False | hemoglobin_g_dl at least 9 g/dL | Hemoglobin（HB）≥90 g/L | |
| NCT03602027 | c0A16 | CMP | inc | False | anc_k_ul at least 1.5 10^3/uL | A Neutrophil count of （ANC）≥1.5×109/L | |
| NCT03602027 | c0A17 | CMP | inc | False | platelets_k_ul at least 80 10^3/uL | A Platelet count of （PLT）≥80×109/L | |
| NCT03602027 | c0A18 | CMP | inc | False | bilirubin_xuln at most 1.5 | A Total bilirubin (TBil) of ≤1.5 upper normal limitation (UNL) | |
| NCT03602027 | c0A20 | CMP | inc | False | creatinine_xuln at most 1.5 | A creatinine (Cr) of ≤1.5 UNL; a creatinine clearance rate ≥ 60ml/min (Cockcroft-Gault) | |
| NCT03602027 | c0A21 | CMP | inc | False | crcl_ml_min at least 60 mL/min | A creatinine (Cr) of ≤1.5 UNL; a creatinine clearance rate ≥ 60ml/min (Cockcroft-Gault) | |
| NCT03602027 | c0A24 | IN | exc | False | cancer_type is one of sclc | Small cell lung cancer (include Small cell lung cancer mixture of NSCLC). | |
| NCT03602027 | c0A26 | IS | exc | True | mi_history is present | Patients has a history of malignant tumors. Patients with basal cell carcinoma, superficial bladder  | |
| NCT03602027 | c1A0 | IN | exc | False | brain_mets is one of untreated_or_symptomatic | Patients with brain or central nervous system metastases, including leptomeningeal disease, or CT/MR | |
| NCT03602027 | c1A3 | CMP | exc | False | neuropathy_grade at least 2 | Patients with grade II or greater peripheral neuropathy, except due to trauma | |
| NCT03602027 | c1A9 | IS | exc | True | active_infection is present | Patients with severe infections , and need to receive systemic antibiotic treatment.（ the infection  | |
| NCT03602027 | c1A15 | ANY | exc | True | (Participation in another antitumor drug trial within 4 weeks before enrollment  | Patients have participated in other antitumor drug clinical trials Within 4 weeks before enrollment  | |