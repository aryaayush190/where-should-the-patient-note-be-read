# SPLIT-Match — Experimental Design

> **Terminology (2026-11-09).** "Pre-specified" means fixed in `docs/PREREGISTRATION.md` before the test run (plan created 2026-11-08 01:41; freeze 02:31:10; first test-side call 02:31:27). The plan was not lodged with an external registry, so it is not called "pre-registered". The filename is kept for continuity.

This summarises the design actually executed. The binding, time-stamped version is `docs/PREREGISTRATION.md`; every change is logged in §9 Deviations there. Where the two differ, the pre-specified analysis plan and its deviations log govern.

---

## 1. Data

| Set | Pairs | Patients | Trials | Eligible | Use |
|---|---|---|---|---|---|
| dev_train | 104 | 26 | 22 | 33 (31.7%) | Design and tuning |
| dev_validation | 26 | 18 | 14 | 8 (30.8%) | Over-fitting guard. Same patients/trials as dev_train, so not a generalisation test |
| **test** | **270** | **45** | **18** | **69 (25.6%)** | **Evaluated once after the freeze.** Disjoint from dev in both patients and trials |
| expansion (fresh) | 150 unlabelled | 25 (with generator truth records) | 11 + 1 | — | Compiler audit and extraction check only. Never used as gold labels |

- **Source:** the INDICON dataset (`data/DATASET_CREATION.md`).
  - Trial criteria are verbatim from ClinicalTrials.gov NSCLC trials.
  - Patient notes are synthetic narratives.
  - Labels are pair-level Eligible / Not Eligible.
- **Disclosure:** the test set was evaluated once before, for the authors' INDICON study, so INDICON's error categories were known. SPLIT-Match had never been run on it before the freeze.

## 2. Systems and conditions

| Condition | What it is | Patient data sent to cloud |
|---|---|---|
| **SPLIT-Match deploy** | Local Qwen3-4B edge (Ollama, CPU) + cloud compiler/L2 | Single minimal facts, on escalated pairs only |
| SPLIT-Match proxy | Same, with Groq `gpt-oss-20b` standing in for the edge model | Same (proxy carries the note, but stands for the device) |
| Cloud zero-shot (cached) | gpt-oss-120b, INDICON prompt, whole note + criteria | Full note, every pair |
| Few-shot, RAG (cached) | INDICON baselines | Full note |
| INDICON hard-veto / advisory (cached) | Authors' earlier hybrid | Full note |
| Cloud zero-shot rerun | Same prompt, re-run today | Full note. Measures Groq non-determinism |
| Edge zero-shot, Qwen3-4B | Same prompt, local model | None |
| *Exploratory:* cloud-on-record | gpt-oss-120b decides from the edge-extracted, de-identified FactSheet (age band, no narrative) | Structured record (~19 fields), every pair |

**Models.** Groq only offers `gpt-oss-120b`, `gpt-oss-20b` and `qwen3.8-27b`, so they are used as follows:

| Role | Model |
|---|---|
| Compiler primary, L2 judge | gpt-oss-120b |
| Compiler secondary | qwen3.8-27b |
| Edge proxy and independent compiler auditor | gpt-oss-20b |
| Real edge model | qwen3:4b-instruct (Ollama), run locally |

All calls use temperature 0.

## 3. Outputs and scoring

- **Forced mode** (primary comparison): always binary.
  - Unmentioned clinical requirements are resolved by L2 on "not stated" plus the relevant record fields.
  - Unknown resolves toward *not excluding*.
- **Selective mode** (deployment): `NEED_INFO` and `DEFER` are abstentions. We report coverage, accuracy on decided pairs, and accuracy with abstentions counted wrong.
- **Positive class** = Eligible. Metrics: accuracy, precision, recall, F1.
- **Missing-information conventions:** see PREREGISTRATION §3.1 and deviations, and `ARCHITECTURE.md` §4.

## 4. Hypotheses (pre-specified)

| ID | Claim | Decision rule |
|---|---|---|
| **H1** (primary) | SPLIT-Match forced (deploy) is non-inferior to cached cloud zero-shot on accuracy | Trial-cluster 95% CI lower bound of the accuracy difference > −0.05 |
| H2 | No raw narrative leaves the device | Narrative sentences in cloud payloads = 0 (post-hoc log audit). Disclosure, k-anonymity and offline share are descriptive |
| H3 | Deployable on the reference CPU | Structuring p95 ≤ 180 s per patient; evaluation ≤ 50 ms per pair |
| H4 | Asks instead of guessing; asking recovers accuracy | Redaction stress test: committed-wrong rate CI vs zero-shot, ask-targeting recall, closed-loop recovery |
| H5 | The uncertainty score ranks errors better | AURC of u vs zero-shot confidence and INDICON adv_conf; bootstrap CI of the difference |
| H6 | Invariant to irrelevant social cues | Flip rate over 4 cues × 270 pairs vs zero-shot; McNemar on flips; cluster CI |
| H7 | Typed atoms beat boolean-only atoms | F1 difference with CI; flagged INDICON 17-FN subset |
| H8 | Robust to noisy notes | ΔF1 (noisy − clean) vs zero-shot, with CIs (descriptive) |

**Pre-specified ablations** (test, frozen config): hard veto; −L1; −L2 (offline); boolean-only (H7); single-model compiler; −verification (single SLM reader); −compiler (edge model judges raw criteria per pair).

Implementation:
- Ablations run with the proxy edge and **reuse the TEST_proxy fact sheets**, so each changes exactly one component (`experiments/run_ablations.py`).
- −compiler is run twice: with gpt-oss-20b (proxy) and with local Qwen3-4B (the edge zero-shot condition).

## 5. Statistics (`splitmatch/stats.py`, ported from INDICON exp9/exp10)

- Trial-cluster percentile bootstrap: resample the 18 test trials, B = 5000, seed 20260815.
- Exact McNemar.
- Exact trial-level sign-flip permutation over 2^18 sign vectors.
- Two-sided α = 0.05. H1 is one-sided non-inferiority, via the 95% two-sided CI.
- AURC: rank by ascending uncertainty, ties in pair_id order.

## 6. Stress studies (pre-specified construction, `splitmatch/variants.py`)

- **Redaction (H4).**
  - Keyword sentence classifier with categories {PS, PRIOR_THERAPY, EFFUSION, BRAIN_METS, CARDIAC, LABS, FEV1, BIOMARKER}.
  - One variant per patient × category present, removing every sentence of that category (231 variants).
  - "Affected" pairs are those whose trial mentions the category (DATASET_CREATION checklist; effusion by keyword).
  - A deterministic simulated health worker answers a matching ASK with the removed sentences. One round.
- **Counterfactual cues (H6).** One of 4 fixed sentences is appended: rural distance, daily-wage labourer, interpreter / Bhojpuri, BPL ration card. 4 × 270 pairs.
- **Noisy notes (H8).** Abbreviation dictionary, telegraphic deletion, and 2% typos in alphabetic words of 5+ letters (seed 20261107).
- **Edge model:** all stress studies use the proxy edge. The local CPU cannot process 231 + 180 + 45 variant notes in the available time. They are labelled as such.

## 7. Procedure and freeze discipline

1. Development only on dev data, over 9 logged iterations (`results/DEV_LEDGER.md`). Every design change is logged with its reason in PREREGISTRATION §9 before any test-side run.
2. Freeze: the sha256 of 26 code files is recorded in `docs/FREEZE_MANIFEST_v1.json` (digest `fadc24c4…`). The user asked for no git commits before finalisation, so the freeze is a manifest rather than a git tag.
3. Test programs compiled after the freeze; then a single frozen test run (`TEST_proxy`, then `TEST_deploy`).
4. After the test run, **no frozen file was changed.** New analysis and ablation drivers were added as new files:
   - `run_ablations.py`, `analyze_extra.py`, `analyze_run.py`, `audit_compiler.py`, `run_record_cloud.py`.
   - They call only frozen code paths.
5. Post-hoc analyses are labelled **exploratory** wherever they appear. Main example: cloud-on-record decomposition.

## 8. Fresh-data checks (no test labels involved)

- **Compiler audit** (`audit_compiler.py`):
  - An independent third model (gpt-oss-20b) checks all 200 typed atoms of the 12 expansion trials against their verbatim lines.
  - The authors adjudicate every flagged agreed atom, plus a random sample of 30 auditor-OK atoms.
- **Extraction check** (`fresh_checks.py extraction`): the edge structurer's facts on 25 expansion patients are scored against the generator's truth records, with a negative control. Run with both the proxy and the local edge.

## 9. Threats to validity (to be stated in the paper)

- **Synthetic notes; small test set.** 18 trials give wide trial-cluster CIs.
- **Labels follow the dataset's own convention.** Forced mode is a comparison device, not a deployment mode.
- **Groq non-determinism.** The zero-shot rerun agrees with the cached run on 97.8% of pairs. Every result uses the stored replies, which are exactly replayable.
- **Proxy edge.** Most results use gpt-oss-20b in place of the local model. The proxy↔local fidelity is reported (`experiments/fidelity.py`).
- **Ollama version change.** It auto-updated from 0.34.2 to 0.40.15 mid-run: the TEST_deploy fact sheets were produced on 0.34.2, and its L1 calls from patient P0004 on used 0.40.15.
- **Self-adjudicated audit.** Compiler-audit adjudication is done by the authors with an LLM coding assistant, not by independent clinicians.


## Post-freeze exploratory additions (pre-submission review, 2026-11-09)

No frozen file changed. All of the following are exploratory and are reported in `results/RESULTS.md` §10 and `docs/REVIEW_RESPONSE.md`:
- clinical metrics (recall, missed eligible, unnecessary referrals per 100 patients);
- patient-cluster and two-way (trial × patient) bootstraps as sensitivity analyses (B = 2000, seed 20261109);
- noise floor: 5 cloud zero-shot runs and 4 gpt-oss-20b runs, run-averaged difference;
- capacity sweep with the same prompt: Qwen3-1.7B (local), Qwen3-4B (local), Qwen3.8-27B (hosted), gpt-oss-20b, gpt-oss-120b;
- local gpt-oss-20b on the 16 GB laptop (40 stratified pairs; weight repacking disabled);
- long cluttered notes (original note verbatim + filler screened by an independent model): cloud, 20B and 4B;
- cloud on the real-device fact sheet; equal-coverage comparison; bandwidth; outage simulation; population uniqueness.
