# SPLIT-Match — Consolidated Results

*Last updated: 2026-11-09 (with pre-submission review additions, §10). Each number below is traceable to a file in `results/` (named per section).*

- Status markers: ✅ final · ⚠ caveat. All experiments are complete (last run 2026-11-09 19:30).
- Design: `docs/EXPERIMENTAL_DESIGN.md`. Binding rules: `docs/PREREGISTRATION.md`.

---

## 0. Status of every experiment

| Experiment | Status | Output |
|---|---|---|
| Development (9 iterations, dev ablations) | ✅ | `DEV_LEDGER.md` |
| Freeze (26 files, sha256; re-verified unchanged 2026-11-08) | ✅ | `docs/FREEZE_MANIFEST_v1.json` |
| Test compile (18 trials) | ✅ | `programs/test/`, `programs/test_summary.json` |
| **Frozen test run, proxy edge (TEST_proxy)** | ✅ | `ANALYSIS_TEST_proxy.json` |
| Frozen test run, local edge, deploy mode (TEST_deploy) | ✅ finished 2026-11-08 20:19 (L1 total 10.8 h on CPU) | `ANALYSIS_TEST_deploy.json` |
| Ablations: hard veto, −L1, −L2, boolean-only | ✅ | `ANALYSIS_EXTRA.json` |
| Ablations: single-model compiler, −verification, −compiler (gpt-oss-20b) | ✅ | `ANALYSIS_EXTRA.json` |
| Stress H4 redaction, H6 counterfactual (proxy edge) | ✅ (each resumed once after a Groq connection drop; cached replay) | `ANALYSIS_STRESS_TEST_proxy_proxy.json` |
| Stress H8 noisy notes (proxy edge) | ✅ 2026-11-09 01:34 | `ANALYSIS_EXTRA.json → H8` |
| H5 AURC with CIs, H7 CI | ✅ | `ANALYSIS_EXTRA.json` |
| Compiler audit on fresh trials | ✅ | `fresh/compiler_audit_adjudication.md` |
| Extraction check, proxy edge | ✅ | `fresh/extraction_proxy.json` |
| Proxy↔local fidelity | ✅ | `runtime/fidelity.log` (fidelity.py output) |
| *Exploratory:* dev replication, edge 20B full note (`AB_nocompiler_proxy20b_dev`) | ✅ 2026-11-09 01:36 | `PAPER_NUMBERS.json` |
| Edge zero-shot Qwen3-4B, full note, test (`ZS_edge_qwen4b_test`) | ✅ 2026-11-09 02:30 (one restart, cached replay) | `PAPER_NUMBERS.json` |
| Extraction check, local edge (25 fresh patients) | ✅ 2026-11-09 03:33 | `fresh/extraction_local.json` |
| *Exploratory:* dev replication, Qwen3-4B full note (`ZS_edge_qwen4b_dev`) | ✅ 2026-11-09 05:13 | `PAPER_NUMBERS.json` |
| *Review (exploratory):* hosted runs: record on real-device sheets, noise floor, Qwen3.8-27B, long notes | ✅ 2026-11-09 13:31 | `review/*.jsonl`, `REVIEW_ANALYSIS.json` |
| *Review (exploratory):* local gpt-oss-20b, 40 pairs (no-repack server) | ✅ 2026-11-09 15:12 | `review/LOC_gptoss20b_*.jsonl` |
| *Review (exploratory):* local Qwen3-1.7B, 270 pairs | ✅ 2026-11-09 16:15 | `review/CAP_qwen3_1p7b_local.jsonl` |
| *Review (exploratory):* local Qwen3-4B on long notes, 270 pairs | ✅ 2026-11-09 19:30 | `review/LONG_edge4b_local.jsonl` |
| dev_validation, local edge (`dev_val_LOCAL_v9`; dev data, descriptive only) | ✅ 2026-11-09 10:09 (resumed once after the session ended at ~07:02): forced acc 0.769 vs proxy 0.808 (one pair); forced agreement with proxy 25/26 | `DEV_LEDGER.md` |
| *Exploratory:* cloud decides from the de-identified record | ✅ | `baselines/REC_cloud_test_proxy.jsonl` |

---

## 1. Headline test results (270 pairs, 45 patients, 18 unseen trials) ✅

The positive class is Eligible. F1 CIs are trial-cluster bootstrap (B = 5000).

| System | Patient data to cloud | Acc | Precision | Recall | F1 [95% CI] |
|---|---|---|---|---|---|
| Cloud zero-shot, gpt-oss-120b (cached INDICON) | full note, every pair | **0.948** | 0.877 | 0.928 | **0.901** [0.839, 0.965] |
| Cloud few-shot (cached) | full note | 0.952 | 0.878 | 0.942 | 0.909 [0.855, 0.966] |
| Cloud RAG (cached) | full note | 0.948 | 0.910 | 0.884 | 0.897 [0.841, 0.947] |
| INDICON advisory hybrid (cached) | full note | 0.919 | 0.866 | 0.879 | 0.872 [0.824, 0.922] |
| INDICON hard-veto hybrid (cached) | full note | 0.885 | 0.918 | 0.682 | 0.783 [0.621, 0.887] |
| Cloud zero-shot, re-run today | full note | 0.933 | — | — | 0.870 [0.795, 0.936] |
| *Exploratory:* cloud decides from de-identified edge record | ~19 structured fields, every pair | 0.881 | — | 0.638 | 0.733 [0.613, 0.821] |
| **SPLIT-Match forced (proxy edge)** | single facts on 63% of pairs, no narrative | **0.774** | 0.557 | 0.565 | **0.561** [0.348, 0.726] |
| SPLIT-Match selective (proxy edge) | same | 0.863 on 83.7% decided | 0.833 | 0.490 | 0.617 [0.364, 0.788] |
| SPLIT-Match offline, −L2 (forced) | **none** | 0.785 | 0.550 | 0.884 | 0.678 [0.557, 0.782] |
| SPLIT-Match offline, −L2 (selective) | **none** | **0.931 on 69.3% decided** | 0.821 | 0.742 | 0.780 [0.583, 0.889] |
| **SPLIT-Match forced, real local edge (Qwen3-4B, deploy mode)** | single facts on 80.7% of pairs, no narrative | **0.770** | 0.547 | 0.594 | **0.569** [0.408, 0.701] |
| SPLIT-Match selective, real local edge | same | 0.863 on 81.1% decided | 0.880 | 0.449 | 0.595 [0.318, 0.794] |
| *Ablation:* edge zero-shot, gpt-oss-20b, full note, no compiler | none if run on device | **0.926** | 0.818 | 0.913 | 0.863 [0.790, 0.941] |
| *Exploratory:* edge zero-shot, **local Qwen3-4B on this CPU**, full note, no compiler | none | **0.867** | 0.699 | 0.841 | 0.763 [0.696, 0.850] |

Notes:
- **Groq non-determinism ⚠.** The re-run zero-shot agrees with the cached run on 97.8% of pairs; its accuracy is 0.933 against 0.948.
- **SPLIT-Match decision counts.** Forced: TP 39, FP 31, FN 30, TN 170. Selective decided 226 of 270 pairs.

---

## 2. Pre-specified hypotheses

| ID | Result | Verdict |
|---|---|---|
| **H1** non-inferiority vs zero-shot (margin −0.05) | **Deploy (local Qwen3-4B, primary):** accuracy diff **−0.178**, CI [−0.253, −0.108]; F1 diff −0.332, CI [−0.476, −0.204]; McNemar 7 vs 55, p = 2.4e-10; sign-flip p = 2.1e-4. Proxy: −0.174, CI [−0.271, −0.088] | ❌ **FAILS** in both deploy and proxy |
| H1 secondary vs INDICON | Deploy: vs hard veto −0.115, CI [−0.181, −0.056]; vs advisory −0.148, CI [−0.227, −0.082]. Proxy: −0.111 / −0.144 | ❌ worse than both |
| **H2** no raw narrative to cloud | **Deploy:** **0** narrative sentences in 568 CLOUD_FACT calls (539 distinct payloads), log complete (568 = 568). Offline share 19.3%; 2.10 L2 calls per pair; median 6 fields disclosed; k ≥ 2 for only 3.2% of payloads. Proxy: 0 in 327 calls, offline 37.0% | ✅ **HOLDS** (see §3 for limits) |
| H3 deployable on reference CPU | Local structuring: p50 278 s, **p95 333 s** (target ≤ 180 s). Local L1 per patient: median 841 s, p95 1173 s (not pre-specified; 10.8 h for 45 patients). Evaluation: mean 0.31 ms, max 4.4 ms per pair (target ≤ 50 ms) | ❌ structuring fails on this throttled laptop CPU; ✅ evaluation passes |
| H4 asks instead of guessing (redaction, proxy edge; 688 affected variant-pairs of 1386) | Committed-wrong: SPLIT selective **0.108** vs zero-shot 0.106; diff +0.001, CI [−0.048, +0.055]. Selective coverage 0.757, accuracy on decided 0.858; zero-shot accuracy 0.894. Ask recall of the removed category 0.39 (PS 0.97, biomarker 0.67, prior therapy 0.12; cardiac, FEV1 0 by design: missing exclusions are presumed absent, labs go to the site checklist). Closed loop: forced accuracy 0.744 redacted → **0.762** after one answer (full note 0.740) | ❌ not supported (no reduction in committed errors); ➖ one answer recovers +0.017 |
| H5 uncertainty ranks errors better | AURC: SPLIT u **0.152** (deploy 0.158); zero-shot confidence 0.0098; INDICON adv_conf 0.054. SPLIT − ZS = +0.142, CI [0.075, 0.217]. SPLIT − advisory = +0.097, CI [0.030, 0.177] | ❌ significantly **worse** |
| H6 invariance to social cues (4 cues × 270, proxy edge) | Flip rate SPLIT **4.9%** vs zero-shot 2.3% (per cue 4.4–5.2% vs 1.9–3.0%). ZS − SPLIT = −0.026, CI [−0.068, +0.013]. McNemar on flips 24 vs 52, p = 0.0018 (SPLIT flips more). Diagnostic: SPLIT flips are symmetric (28 E→NE, 25 NE→E), 42 of 53 move *toward* the gold label, and 14 come from one patient (P0012): perturbation instability on borderline pairs, not a cue-directed bias | ❌ fails (pair-level McNemar against SPLIT; trial-cluster CI includes 0) |
| H7 typed atoms vs boolean-only | F1 full − boolean = **+0.050**, CI [−0.088, +0.240]. Flagged INDICON 17-FN subset: full 8/17 (deploy 7/17), boolean 7/17 | ➖ direction as predicted; not significant |
| *Proxy↔local fidelity* (descriptive) | Field agreement 0.776 overall, **0.940 on verified fields**. Forced decision agreement **0.893**, selective 0.796. Forced accuracy 0.770 local vs 0.774 proxy | ✅ the proxy is a faithful stand-in at the decision level |
| H8 noisy notes (proxy edge, 270 pairs) | ΔF1 (noisy − clean): SPLIT **+0.037**, CI [−0.001, +0.085]; zero-shot −0.006, CI [−0.042, +0.031]; difference +0.043, CI [−0.012, +0.103]. Forced accuracy on noisy notes: SPLIT 0.796, zero-shot 0.933 | ➖ neither system degrades; H8 does not separate them |

---

## 3. Privacy (H2) in detail — TEST_proxy ✅

Source: `ANALYSIS_TEST_proxy.json → H2_privacy`.

**Calls and egress**

| Measure | Value |
|---|---|
| Edge calls (stand-in) | 441 |
| CLOUD_FACT calls | 327 logged |
| Narrative sentences in cloud payloads | **0** |
| Pairs decided with no cloud call | **37.0%** |
| Pairs with ≥1 cloud fact query | 63.0% |
| Mean L2 calls per pair | 1.21 |
| Disclosed fields per escalated pair | median **5**, max 21 |
| Full-note baseline, for comparison | the whole note goes to the cloud for every pair |

**Limits, stated honestly:**
- **k-anonymity is low.** Median 1; only 7.8% of fact payloads are shared by ≥2 patients. Each L2 query carries the structured record values relevant to that criterion. That is what makes the combination near-unique. "No narrative leaves" is therefore *not* "nothing identifying leaves".
- **Audit completeness ⚠.** 327 CLOUD_FACT log records against 328 L2 calls counted by the run. One record was lost to a concurrent-append race in the shared log. The log has 1 unparseable line in total. It is the tail of a full-note zero-shot prompt (note followed by criteria), i.e. a baseline or edge call, not a SPLIT-Match cloud-channel call. The runtime guard runs before every call regardless of logging. Checked by `experiments/analyze_run.py`.
- **Most offline privacy at no forced-accuracy cost.** The −L2 offline variant sends no patient data at all, and its forced accuracy is equal (0.785 vs 0.774, CI of diff [−0.057, +0.084]).

---

## 4. Ablations (test, frozen config, each reusing TEST_proxy fact sheets) ✅

Differences are relative to the full system; CIs are trial-cluster bootstrap.

| Variant | Forced acc | Forced F1 | ΔF1 vs full [95% CI] | McNemar (variant-only vs full-only correct), p | Sel. coverage | Sel. acc (decided) | L2/pair | Offline decided |
|---|---|---|---|---|---|---|---|---|
| **Full SPLIT-Match** | 0.774 | 0.561 | — | — | 0.837 | 0.863 | 1.21 | 0.370 |
| Hard veto (one key excludes) | **0.800** | 0.571 | +0.010 [−0.067, +0.087] | 13 vs 6, p = 0.17 | 0.881 | 0.853 | 0.76 | 0.489 |
| −L1 (no edge judge) | 0.733 | 0.556 | −0.006 [−0.070, +0.087] | 7 vs 18, **p = 0.043** | 0.678 | 0.907 | 1.43 | 0.230 |
| **−L2 (offline, no cloud)** | 0.785 | **0.678** | **+0.117** [−0.028, +0.324] | 22 vs 19, p = 0.76 | 0.693 | **0.931** | 0 | 0.693 |
| Boolean-only atoms (H7) | 0.767 | 0.512 | −0.050 [−0.240, +0.088] | 10 vs 12, p = 0.83 | 0.815 | 0.850 | 1.51 | 0.263 |
| **Single-model compiler** (no dual agreement) | **0.811** | **0.617** | **+0.055** [+0.012, +0.130] | 13 vs 3, **p = 0.021** (sign-flip p = 0.016) | 0.863 | 0.867 | 1.02 | 0.426 |
| −verification (single reader) | 0.785 | 0.580 | +0.019 [−0.038, +0.096] | 7 vs 4, p = 0.55 | 0.848 | 0.869 | 1.04 | 0.415 |
| **−compiler** (edge model judges raw criteria, gpt-oss-20b) | **0.926** | **0.863** | **+0.302** [+0.141, +0.504] | 54 vs 13, p < 1e-6 | 1.0 | 0.926 | 0 | 1.0 |
| −compiler, deployable (local Qwen3-4B reads the full note) | 0.867 | 0.763 | vs full SPLIT deploy: acc **+0.096** [+0.025, +0.188] | 50 vs 24, **p = 0.0034** (sign-flip p = 0.028) | 1.0 | 0.867 | 0 | 1.0 |

**Readings:**
- **The L2 cloud judge does not help on test.** Removing it raises F1 from 0.561 to 0.678 and selective accuracy from 0.863 to 0.931, and makes the system fully offline.
- The largest false-exclusion cluster comes from L2. Trial NCT03141359 has 11 false negatives with L2 and 1 without.
- **The L1 edge judge helps.** Removing it costs 0.04 accuracy, and McNemar p = 0.043.
- **The two-key rule did not pay off on test.** Hard veto is +0.026 accuracy (not significant). On dev it cost 0.03 accuracy and 6 more false negatives.
- **Dual-model agreement costs accuracy ⚠.** The single-model compiler is significantly *better* (+0.037 accuracy, CI [+0.013, +0.071]; +0.055 F1). Downgraded atoms go to the judges, and the judges are less accurate than the primary compiler's atoms. The fresh-trial audit shows downgrading does catch more wrong atoms (§6), so this is a safety-vs-accuracy trade-off, not a free gain.
- **Verification has no measurable effect** on the decision (+0.011 accuracy, n.s.).
- **The compiler pipeline itself is the bottleneck.** A 20B edge-class model reading the full note and the raw criteria (no compiler, no evaluator) reaches 0.926 accuracy / 0.863 F1, +0.152 accuracy over full SPLIT-Match, and sends nothing to the cloud. Whether this holds for a deployable 4B model is the held Qwen3-4B zero-shot run.

---

## 5. Where the accuracy goes ✅ (exploratory decomposition; not pre-specified)

| Step | Acc | Loss |
|---|---|---|
| Cloud reads the full note | 0.948 | — |
| Cloud reads only the edge-extracted, de-identified record | 0.881 | **≈ 6–7 points: extraction / representation** |
| SPLIT-Match compiled decision layer on that same record | 0.774 | **≈ 11 points: decision layer** |

Record-to-cloud vs zero-shot: diff −0.067, CI [−0.108, −0.035], McNemar p = 0.0003, sign-flip p = 0.002. Recall drops to 0.638.

**Error concentration (TEST_proxy, forced):**
- **False negatives (30 total):**
  - NCT03141359: 11 FN. A long conditional stage criterion was compiled to JUDGE and misjudged by L1/L2. Not a code defect.
  - NCT02182232: 6 FN.
- **False positives (31 total):**
  - NCT01766739: 10 FP. NCT00465907: 7 FP.
  - By selective outcome: 23 of the 31 forced false inclusions were `NEED_INFO` pairs (and 3 were `DEFER`). The system knew information was missing, and forced mode turned "unknown" into "not excluding" by design.

---

## 6. Compiler fidelity on fresh trials (never used in development) ✅

Source: `fresh/compiler_audit_adjudication.md`.

**Agreement:**

| Trial set | Typed-atom agreement |
|---|---|
| Development | 72.2% |
| Fresh expansion | 71.5% |
| Test | 76.7% (221/288) |

**Independent auditor** (gpt-oss-20b, neither compiler), applied to all 200 typed atoms of the 12 fresh trials:

| Group | Flagged by auditor |
|---|---|
| Agreed atoms | 19.6% (28/143) |
| Downgraded atoms | 56.1% (32/57) |

Fisher exact test: OR 0.19, p = 9.2e-7. **Dual-compiler agreement concentrates errors in the atoms that lose authority.**

**Author adjudication** of the 28 flagged agreed atoms:
- **4 real semantic errors** = 2.8% of agreed atoms (95% CI 0.8–7.0%). All 4 are *permissive*: they can only fail to exclude.
- 2 minor narrowings (4.2% including them).
- The rest were partial captures, or clauses covered by sibling atoms.
- A random sample of 30 auditor-OK atoms: all correct (auditor miss rate upper bound 11.6%).

⚠ Adjudication is by the authors with an LLM assistant, not by clinicians.

## 7. Edge extraction on fresh patients ✅ (proxy and local)

Source: `fresh/extraction_proxy.json`. 25 expansion patients, scored against the generator's truth records.

- Stated facts extracted correctly: 100%. Precision of extracted facts: 100%.
- 84% of facts verified by the two-reader rule.
- Therapy classes exactly right for 96% of patients.
- 2 hallucinated `mi_history = true`.
- A negative control confirmed the scorer can fail.

So on fresh notes the extraction itself is accurate. The record-level loss in §5 comes from what the 47-field schema *cannot represent*, not from misreading. ⚠ This inference is to be confirmed with the local-model check.

**Local edge (Qwen3-4B), `fresh/extraction_local.json`:** field recall **0.877** (proxy 1.000); verified facts 323 (72.4%), **precision 1.000**; unverified facts 123, precision 0.553, so **all 55 wrong values are unverified**, and the authority policy never lets an unverified fact exclude. Errors are concentrated in biomarker status (ALK 6/16, EGFR 8/19, KRAS 5/15, RET 6/16, ROS1 5/15 correct); therapy class exact 0.60 (proxy 0.96); one hallucinated MI (proxy: two).

## 8. Development history (dev data only) ✅

Source: `DEV_LEDGER.md`.

- Forced accuracy on dev_train went from 0.750 (v2) to 0.856 (v8/v9). F1 0.795; selective coverage 0.769 at 0.912 accuracy.
- Reference: zero-shot 0.913 on dev_train.
- dev_validation: SPLIT 0.808 = zero-shot 0.808.
- The dev-to-test drop (−0.057 → −0.174 vs zero-shot) shows that the design tuned on 22 trials generalises poorly to 18 new trials. The INDICON rule gate showed the same pattern.

---

## 8b. Exploratory dev replication (130 pairs, disjoint trials and patients) — `PAPER_NUMBERS.json → dev`

| System | Dev acc [95% CI] | Δ vs cloud ZS [95% CI] | McNemar p | Test Δ |
|---|---|---|---|---|
| Cloud zero-shot, gpt-oss-120b (`ZS_cloud_dev`) | 0.892 [0.824, 0.948] | — | — | — |
| SPLIT-Match, proxy (dev_train + dev_val v9; **tuned on dev**) | 0.846 [0.766, 0.910] | −0.046 [−0.137, +0.037] | 0.34 | −0.174 |
| Edge 20B, full note (gpt-oss-20b stand-in) | 0.869 [0.776, 0.945] | **−0.023** [−0.081, +0.031] | 0.61 | −0.022 |
| Edge Qwen3-4B, full note (local) | 0.808 [0.718, 0.882] | **−0.085** [−0.149, −0.031] | 0.013 | −0.081 |

**Reading:** both edge-model gaps replicate: 20B −0.023 (test −0.022), 4B −0.085 (test −0.081). The edge-20B gap is the same on dev and test, but dev alone has too few trial clusters for non-inferiority (lower bound −0.081). SPLIT-Match's gap grows from −0.046 on the split it was tuned on to −0.174 on unseen trials: the compiled pipeline overfits its development trials, and reading the note transfers.

## 9. What the results support (all runs complete as of 2026-11-09 10:09)

> **Post-review update (2026-11-09 19:30).** §10 refines two statements below. (a) The edge-20B gap is about 2–3 points: run-averaged −0.024 [−0.046, −0.002]; non-inferiority at −0.05 holds only under trial clustering (patient −0.052, two-way −0.066). (b) Capacity is model-dependent, not monotone in size: Qwen3-1.7B 0.533, Qwen3.8-27B 0.885 (recall 0.580). The paper's record row uses the real-device sheet (0.896). **2026-11-10:** (a) is superseded for the device by the full laptop run (§10b): on-device gpt-oss-20b is 0.900, Δ −0.048, not non-inferior under any clustering.

1. **Supported:**
   - Strict data minimisation is achievable: zero narrative egress (proxy and real local edge); 37% (proxy) / 19% (local) of pairs fully offline with L2, 69% offline without.
   - Fully offline selective mode decides 69% of pairs at 93% accuracy.
   - The gpt-oss-20b proxy is a faithful stand-in for the local 4B edge at the decision level (89% forced agreement; equal accuracy 0.774 vs 0.770).
   - Dual-model compiler agreement filters wrong atoms on fresh trials (audit), but costs test accuracy (single-model ablation +0.037).
   - One health-worker answer recovers some accuracy after redaction (0.744 → 0.762).
   - The edge-20B full-note gap to the cloud replicates on dev (−0.023 vs −0.022 on test; exploratory).
   - With the edge model held fixed (local Qwen3-4B), reading the full note beats the compiled SPLIT-Match pipeline: 0.867 vs 0.770, +0.096 [+0.025, +0.188], McNemar 50 vs 24, p = 0.0034 (exploratory). It is also 5.2× cheaper in CPU time per patient (217 s vs 1119 s for 6 trials; median 37 s per pair, p95 94 s).
2. **Not supported:**
   - Non-inferiority to full-note cloud LLMs (H1), in both deploy and proxy.
   - Fewer committed errors when information is missing (H4).
   - Better uncertainty ranking (H5).
   - Invariance to irrelevant social cues (H6): SPLIT flips more than zero-shot, although the flips look like perturbation instability, not cue-directed bias.
   - CPU structuring within 180 s on this laptop (H3).
   - Benefit of the cloud fact-judge (L2) and of the two-key rule on test.
   - Differential robustness to noisy notes (H8): neither system degrades.
   - Non-inferiority of a **dense 4B** edge model reading the full note: 0.867, −0.081 [−0.127, −0.036], McNemar 2 vs 24, p = 1.0e-5. Edge model capacity sets the ceiling.
3. **The decisive ablation:** an edge-class 20B model reading the full note directly (no compiler) reaches 0.926 accuracy with no cloud egress. The compiler/evaluator pipeline is the main source of accuracy loss, not the privacy split as such.
4. **The privacy–accuracy price.** Accuracy as less patient information goes to the cloud:

   | Information sent to the cloud | Accuracy |
   |---|---|
   | Full note (cloud zero-shot) | 0.948 |
   | Structured record (proxy sheet / real-device sheet) | 0.881 / 0.896 |
   | Single facts (SPLIT, proxy / local) | 0.774 / 0.770 |
   | None, compiler pipeline (forced) | 0.785 |
   | None, compiler pipeline (selective, on the 69% it decides) | 0.931 |
   | None, 20B edge model on full note (no compiler) | 0.926 |
   | None, local Qwen3-4B on full note (no compiler, real CPU) | 0.867 |
   | None, local Qwen3-1.7B on full note (real CPU) | 0.533 |

---

## 10. Pre-submission review additions (2026-11-09; all EXPLORATORY) — `REVIEW_ANALYSIS.json`

Point-by-point triage: `docs/REVIEW_RESPONSE.md`. Runs: `experiments/review_runs.py`. Analyses: `experiments/review_analysis.py`. No frozen file changed.

**Clinical metrics** (test; abstentions counted as not referred; per 100 patients × 6 trials).

| System | Acc | Recall | Precision | Missed eligible (/100) | Unnecessary referrals (/100) |
|---|---|---|---|---|---|
| Cloud zero-shot (cached) | 0.948 | 0.928 | 0.877 | 5 (11.1) | 9 (20.0) |
| Cloud on real-device record | 0.896 | 0.667 | 0.902 | 23 (51.1) | 5 (11.1) |
| SPLIT-Match deploy | 0.770 | 0.594 | 0.547 | 28 (62.2) | 34 (75.6) |
| SPLIT-Match offline (forced) | 0.785 | 0.884 | 0.550 | 8 (17.8) | 50 (111.1) |
| gpt-oss-20b full note (hosted) | 0.926 | 0.913 | 0.818 | 6 (13.3) | 14 (31.1) |
| Qwen3-4B full note (CPU) | 0.867 | 0.841 | 0.699 | 11 (24.4) | 25 (55.6) |
| Qwen3.8-27B full note (hosted) | 0.885 | 0.580 | 0.952 | 29 (64.4) | 2 (4.4) |

**Clustering sensitivity** (vs cached cloud ZS). gpt-oss-20b: accuracy Δ −0.022, CI trial [−0.043, 0.000], patient [−0.052, +0.004], two-way [−0.066, +0.012] → non-inferiority at −0.05 holds only under trial clustering; recall Δ −0.014, two-way CI [−0.095, +0.078] (within −0.10). Qwen3-4B: accuracy two-way [−0.155, −0.023]. SPLIT deploy: two-way [−0.283, −0.075].

**Noise floor.** Cloud 5 runs: 0.948, 0.933, 0.937, 0.937, 0.937 (mean 0.939, SD 0.005; pairwise agreement 97.4–98.9%). gpt-oss-20b 4 runs: 0.926, 0.911, 0.915, 0.907 (mean 0.915, SD 0.007). Run-averaged gap −0.024, CI [−0.046, −0.002]: small, real, inside the margin.

**Capacity sweep** (same prompt): Qwen3-1.7B CPU 0.533 (recall 0.870, 117 unnecessary referrals; median 13 s/pair); Qwen3-4B 0.867; Qwen3.8-27B (dense, hosted) 0.885 / recall 0.580; gpt-oss-20b 0.926; gpt-oss-120b 0.948. Monotone within the Qwen family (1.7B < 4B < 27B), not across families (dense 27B < MoE 20B) → claim softened to "model-dependent".

**Local gpt-oss-20b on the i5/16 GB laptop.** Default load failed (llama.cpp tried to allocate a 10.2 GB CPU_REPACK buffer next to the 13 GB weights). With `LLAMA_ARG_NO_REPACK=1` (memory-mapped weights) it runs: 40 stratified pairs (all 18 trials, 17 eligible): median 155 s per pair (p95 235 s; ≈15 min per patient for 6 trials), 11.9 prompt / 1.9 generated tokens/s, peak resident 9.7 GB; accuracy 0.90 vs 0.95 hosted on the same pairs; agreement with all four hosted runs 38/40 (the two differing pairs: one false inclusion, one false exclusion).

**Long cluttered notes** (45 notes embedded verbatim, 471–1,279 words, median 755; 67 of 1,388 filler sentences dropped by an independent relevance screen). Cloud 0.937 → 0.937 (Δ 0.000, CI [−0.019, +0.022]); gpt-oss-20b 0.926 → 0.907 (Δ −0.019, CI [−0.042, +0.003]); Qwen3-4B (local CPU) 0.867 → 0.856 (Δ −0.011, CI [−0.048, +0.021]; recall 0.841 → 0.928; median 38 s/pair, peak 3.8 GB).

**Record on the real-device fact sheet:** 0.896 (vs 0.881 on the proxy sheet); decomposition on the real device: −5 (record) then −13 (compiled layer).

**Equal coverage (69.3%).** Offline SPLIT selective 0.930; cloud with confidence abstention 0.984 (SPLIT − cloud −0.054 [−0.082, −0.028]); gpt-oss-20b 0.930 (+0.001 [−0.044, +0.041]); Qwen3-4B 0.888 (+0.043 [−0.005, +0.089]). Expected accuracy over confidence ties.

**Bandwidth** (patient-derived chars per patient, 6 trials): full note 5,142; record 2,508; facts 1,554; on device 0. **Outage simulation** (link up 50%, 30-min window): cloud full note 80.0% complete, SPLIT-Match 60.3%, on-device 4B 100%.

**Population uniqueness** (10⁵ generator patients): records 99.8% unique; single fact payload 4.6%; linked session of fact queries 24.5% (structured values only; lower bound).


### 10b. Round-2 review additions (2026-11-09 night; exploratory) — `REVIEW_ANALYSIS.json → same_model, local20b_full`

**Same device model, read vs compiled (Qwen3-4B).** Accuracy +0.096 (0.867 vs 0.770), McNemar 50 vs 24, p = 0.0034. CIs: trial [+0.025, +0.188] (B = 5000, paper); trial [+0.022, +0.183], patient [+0.033, +0.159], **two-way [−0.018, +0.213]** (B = 2000). Recall +0.246: patient [+0.097, +0.389], two-way [−0.066, +0.563]. ⚠ The two-way interval touches zero, so the claim is scoped to our instantiation.

**Timing reconciliation.** 4B reading the note: 217 s CPU per patient (median over patients of summed pair latencies); the outage simulator now uses this measured value instead of 6 × 37 s = 222 s. SPLIT-Match: 1,119 s CPU per patient; its simulated time to decision, 1,197 s, adds 13 cloud calls.

**Qwen3.8-27B** verified as the official name (Alibaba open weights, August 2026; Groq id `qwen/qwen3.8-27b`).

**gpt-oss-20b on the laptop, all 270 pairs** (`review/LOC_gptoss20b_test.jsonl`; 2026-11-09 23:11 → 2026-11-10 08:21, `scripts/queue_local20b_full.sh`; 40 pairs replayed from the 40-pair run, 1 load-time error retried; 0 unparsed; longest reply 330 of 1,500 tokens).

| Measure | Value |
|---|---|
| Accuracy [trial CI] | **0.900** [0.858, 0.950] |
| Δ vs cloud ZS (0.948): trial / patient / two-way CI | **−0.048**: [−0.076, −0.020] / [−0.085, −0.015] / [−0.107, −0.006]; McNemar 2 vs 15, p = 0.0023 |
| Δ vs mean of 5 cloud runs | −0.038, trial CI [−0.069, −0.011] |
| Non-inferior at −0.05? | **No**, under any clustering scheme |
| Recall (Δ; two-way CI) | 0.855 (−0.072; [−0.200, +0.046]); precision 0.776 |
| Missed eligible / unnecessary referrals | 10 / 17 (per 100 patients: 22.2 / 37.8) |
| Cloud runs (5): missed / unnecessary | 5, 9, 9, 10, 8 / 9, 9, 8, 7, 9 |
| Hosted 20B runs (4): accuracy; missed / unnecessary | 0.926, 0.911, 0.915, 0.907 (mean 0.915); 6, 10, 9, 8 / 14, 14, 14, 17 |
| Agreement with hosted runs | 95.9–97.0% |
| vs first hosted run | −0.026, trial CI [−0.040, −0.013], McNemar 2 vs 9, p = 0.065 |
| vs Qwen3-4B on the laptop | +0.033, trial CI [−0.004, +0.069], McNemar 16 vs 7, p = 0.093; eligible caught only by 20B 4, only by 4B 3 |
| Latency per pair | median 138 s, p95 217 s, mean 145 s; per patient (6 trials) 831 s ≈ 14 min; 10.8 CPU h total |
| Throughput / memory | 13.0 prompt tok/s, 1.75 generated tok/s; peak RSS 9.7 GB |
| Offline coverage (69.3%) | 0.927 at equal coverage (SPLIT offline 0.930; diff +0.004 [−0.038, +0.042]) |
| Outage simulation | 100% of screenings finish within a 30-min visit at every link availability |

**Interpretation.** On the device, the 20B model misses about as many eligible pairs as the cloud's worst run; its accuracy gap (≈ 4–5 points) is mostly unnecessary referrals. The hosted runs overstate on-device accuracy by about 1–2 points. Paper wording updated accordingly (abstract, contribution 3, Sec. V-C, robustness, discussion, conclusion).


### 10c. Second device model for "reading beats compiling" (2026-11-10, exploratory analysis of a pre-specified ablation) — `REVIEW_ANALYSIS.json → same_model.gptoss20b_hosted`

Hosted gpt-oss-20b reading note + criteria (pre-specified −compiler ablation, `AB_nocompiler_proxy20b`) vs SPLIT-Match
with the same hosted gpt-oss-20b as edge tier (`TEST_proxy`, forced):

| | Read | Rules | Δ | Trial CI | Patient CI | Two-way CI |
|---|---|---|---|---|---|---|
| Accuracy | 0.926 | 0.774 | +0.152 | [+0.063, +0.255] | [+0.093, +0.211] | [+0.034, +0.280] |
| Recall | 0.913 | 0.565 | +0.348 | [+0.120, +0.562] | [+0.227, +0.474] | [+0.069, +0.633] |
| Missed eligible | 6 | 30 | | | | |

McNemar 54 vs 13, p = 4×10⁻⁷ (B = 2000 for all three schemes; the pre-specified B = 5000 trial CI in
`ANALYSIS_EXTRA.json` is [+0.065, +0.258]). Qwen3-4B (laptop) for comparison: missed 11 vs 28; recall +0.246
(trial [0.000, +0.478], patient [+0.097, +0.389], two-way [−0.066, +0.563]).


### 10d. Round-5 review additions (2026-11-11; exploratory) — `REVIEW_ANALYSIS.json → missed, decomposition, local_repeats, outage_sensitivity`; `review/GATEWAY_SUITE.json`

**Fixed model, three inputs** (fact sheet = the model decides from its own SPLIT-Match fact sheet, zero-shot prompt):

| Model | Note | Fact sheet | Rules | Missed (note / sheet / rules) | Unnecessary |
|---|---|---|---|---|---|
| Qwen3-4B (laptop, `REC_edge4b_test_deploy`) | 0.867 | 0.852 | 0.770 | 11 / 11 / 28 | 25 / 29 / 34 |
| gpt-oss-20b (hosted, `REC_edge20b_test_proxy`) | 0.926 | 0.878 | 0.774 | 6 / 20 / 30 | 14 / 13 / 31 |

**Missed patients vs cloud (69 eligible pairs, exact McNemar on eligible pairs):** SPLIT-Match recall −0.333 (two-way
[−0.595, −0.059], 25 vs 2, p = 6×10⁻⁶); record −0.261; Qwen3-4B −0.087 (p = 0.11; two-way [−0.268, +0.060]);
gpt-oss-20b laptop −0.072 (p = 0.12; two-way [−0.200, +0.046]); SPLIT offline −0.043 (p = 0.55).

**Laptop repeats (uncached):** Qwen3-4B 270 pairs: 99.3% agreement, accuracy 0.867 both runs, median 31 s, p95 56 s,
2.8 GB. gpt-oss-20b 40 pairs: 92.5% agreement, 0.975 vs 0.900, median 230 s, p95 322 s, cold start 95 s, 7.6 GB.

**Gateway suite:** exact 100%, embedded 100%, case/spacing 98.6%, IDs 100%; half-sentence 0.3%, word dropped 0.6%,
punctuation removed 0%, base64 0%; false blocks 0/539 real fact queries, 0/745 public calls; 31 short note lines
unregistered. Real traffic: 24/539 (4.5%) fact queries reuse ≥ 5 consecutive note words (max 11).

**Outage sensitivity (50% availability):** cloud 99.6 / 80.0 / 59.7%, SPLIT-Match 87.6 / 60.3 / 53.0% for mean
up-periods of 5 / 30 / 120 min; on-device 100%.
