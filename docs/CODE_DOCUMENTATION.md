# Code Documentation — TELEMED_PERCOM (SPLIT-Match)

This file explains every file and folder in the project: **what it does** and **why it exists**.

- For the system design, read `docs/ARCHITECTURE.md`.
- For the study design, read `docs/EXPERIMENTAL_DESIGN.md`.
- For the numbers, read `results/RESULTS.md`.

```
TELEMED_PERCOM/
├── splitmatch/          the system (library)            — frozen after development
├── experiments/         runnable experiment & analysis scripts
├── scripts/             detached job queues (survive a closed session)
├── tests/               unit tests (89)
├── data/                copied INDICON dataset (pairs, trials, expansion set, tooling)
├── baselines_indicon/   copied INDICON cached predictions, results and code (comparators)
├── legacy_indicon_src/  read-only reference copy of INDICON source
├── docs/                plan, pre-specified analysis plan, freeze manifest, architecture, design
├── paper/               LaTeX draft + bibliography
├── results/             every output (programs, runs, baselines, stress, audits, analyses)
├── runtime/             raw LLM call log, response cache, job logs (gitignored)
├── .venv/               pinned Python environment (gitignored)
├── README.md            setup & run instructions
├── CODE_DOCUMENTATION.md  this file
├── requirements.txt     pinned dependencies
├── .gitignore           keeps keys, env, caches, runtime out of git
└── groq_keys.txt        Groq API keys, one per line (SECRET, gitignored)
```

**Frozen files.** The 26 files listed in `docs/FREEZE_MANIFEST_v1.json` were fixed before any test-set run. Their hashes were re-verified on 2026-11-08 and none has changed. Every file added after the freeze is marked **[post-freeze]** below; these files only *call* frozen code.

---

## 1. `splitmatch/` — the system

| File | What it does | Why it exists |
|---|---|---|
| `__init__.py` | Package marker | — |
| `paths.py` | Every project path (data, results, runtime, log, cache, pair and trial files); creates output folders | One source of truth, so the folder stays self-contained and relocatable |
| `schema.py` | The two typed interfaces. **FactSheet** is the edge output: 47 fields, each a `Fact` (status, interval value, evidence quote, readers, verified), plus `TherapyEvent`s. **TrialProgram** is the cloud output: a list of `Atom`s with type, polarity, source line, section, downgraded flag. Also holds the field registry `FIELDS`, the therapy classes, and the type checker `type_errors` / `program_errors` used for compiler repair | A strict contract between the public and private sides. Intervals keep coarse statements exact. The type checker turns LLM output errors into a repairable error list |
| `llm.py` | **Privacy gateway.** `call(channel, messages, …)` is the only way any model is called. Contents: channels (`CLOUD_PUBLIC`, `CLOUD_FACT`, `EDGE_LOCAL`, `EDGE_PROXY`, `BASELINE_CLOUD`); the narrative registry and fail-closed `guard` (raises before I/O on a narrative sentence or an ID); deploy mode (forbids `EDGE_PROXY`); Groq and Ollama backends; a JSONL call log; a disk response cache keyed by a hash of model + messages + parameters; model constants | Privacy claims are *measured from the log*, not asserted. The cache makes every run replayable and lets interrupted jobs resume free |
| `groq_pool.py` | Round-robin pool over the Groq keys, with cooldown on 429. It remembers (key, model) pairs whose organisation blocks the model (403) or caps tokens per minute (413) | Copied from INDICON and extended. Spreads load over 34 keys and survives per-org limits |
| `data.py` | Loaders: `load_pairs(split)`, `patients`, `trials(set)`, `all_trials`, `expansion_patients`. Labels are normalised to 0/1. Every loaded note is registered with the privacy guard | Every system sees the *identical* note text that INDICON saw. Registration lets the guard recognise any leaked sentence |
| `compiler.py` | **Cloud tier.** Deterministic line splitting and numbering (cohort-header-aware fragment merge). Prompt v1.2 with the field catalogue. Chunked compilation, normalisation (polarity casing, field aliases), type check plus one repair round, stage-alternative merge. Equivalence tests: `atom_agreed` / `_leaf_equiv`. `compile_trial`: two models, and every unmatched typed atom is downgraded. `single_model=True` gives the ablation | Turns public criteria into checkable logic once per trial. Dual-model agreement decides which atoms are trusted |
| `regex_reader.py` | Deterministic second reader. Conservative patterns for ECOG/KPS, stage/TNM, biomarkers, labs (bound-aware: `<480` is a bound, not a value), FEV1, life expectancy, therapy events with timing intervals, and "no prior therapy" | An independent reader, so a fact can be *verified* without trusting one model |
| `structurer.py` | **Edge tier.** SLM prompt (`{"v","q"}` per field, worked example). `build_factsheet`: grounding (quote must appear in the note), relevance lexicon (quote must be about the field), two-reader agreement gives `verified`; drops nulls and ungrounded negations; regex fallback for therapy events. `structure(patient_id, note, channel)` is the entry point | Produces the private FactSheet on the device, with an explicit trust level per fact |
| `evaluator.py` | Deterministic three-valued evaluator. Kleene operators, interval comparison, ECOG↔KPS and ×ULN conversion with a ±10% "near threshold" rule, closed-world defaults for pertinent negatives, stage subsumption, therapy matching (`systemic` covers all systemic classes), WITHIN/SINCE/COUNT. `evaluate_program` returns one `AtomResult` (value, verified, assumed, …) per atom | The local matching core: no model, no network, ~1 ms per pair, unit-tested |
| `render.py` | Human-readable atoms (`render`), the polarity a judge must use (`judge_polarity`), and the judge statement (`statement`; downgraded atoms use the verbatim line) | One wording shared by L1, L2, ASK questions and the audit trail |
| `ladder.py` | `l1_batch`: edge judge, one call per patient over all residual statements (chunks of 12, split on failure, missing items "unavailable"). `l2_judge`: cloud judge on one statement + minimal fact + record (channel `CLOUD_FACT`, guarded) | Resolves what the deterministic layer leaves at U, at minimal privacy cost |
| `policy.py` | **Evidence-conditioned authority.** `Config` (hard_veto, use_l1, use_l2), `Decision`, and `decide`: two-key exclusion; permission guard; missing-information routing (presume absent / ASK / site checklist); forced-mode resolution via L2 on "not stated" plus record; `uncertainty()` | Encodes the cost asymmetry: one error can never exclude a patient |
| `pipeline.py` | `run(pairs, programs, edge, run_name, cfg, factsheets, notes, transform)`: structure each patient once, batch L1 per patient, decide per pair. Writes fact sheets, L1 files, per-pair trace JSON, `predictions.jsonl` and `timing.json`; resumes from saved files. Also `metrics`, `load_programs`, `boolean_only` (H7 transform) and `residual_statements` | The end-to-end runner, with the O(T + P) cost structure made explicit |
| `variants.py` | Stress-variant generators: sentence `categorise`, `redaction_variants`, the 4 social `CUES` with `counterfactual`, and `noisy` (abbreviations, telegraphic style, typos) | Builds the H4/H6/H8 stress studies. Frozen before the test run so the variants are not tuned |
| `stats.py` | Pre-specified statistics: `confusion`, exact `mcnemar`, exact trial `sign_flip` (2^18), `cluster_boot` (B = 5000, seed 20260815), `acc_diff`, `f1_diff`, `non_inferiority` (margin −0.05), `aurc` | Ported from INDICON exp9/exp10, so both studies use identical, validated tests |
| `baseline.py` | Exact INDICON zero-shot prompt (`BASELINE_SYSTEM`, 4000-char truncation), `user_block`, `parse_vote` (conservative default), `zero_shot(note, inc, exc, channel)` for cloud or local | Re-runs the baseline on stress variants and on the local edge model under identical conditions |
| `privacy.py` | `load_log`, `audit`: re-scans every cloud payload for narrative sentences; reports disclosed fields per escalated pair, k-anonymity of fact payloads, and baseline egress characters | The H2 numbers, computed independently of the runtime guard |

## 2. `experiments/` — runnable scripts

| File | Command | What / why |
|---|---|---|
| `compile_trials.py` | `python experiments/compile_trials.py development expansion` (test only after the freeze) | Compiles trial sets into `results/programs/<set>/` plus an agreement summary |
| `run_splitmatch.py` | `--split {dev_train,dev_validation,test} --edge {proxy,local} --name X [--hard-veto --no-l1 --no-l2 --boolean-only --programs-variant _single --factsheets-from RUN]` | Main runner. A test run with `--edge local` automatically sets deploy mode |
| `run_zero_shot.py` | `--split test --where {cloud,local} [--variant cueN\|noisy] --name X` | INDICON zero-shot baseline, re-run (cloud rerun; local Qwen3-4B edge baseline) |
| `run_stress.py` | `{redaction,counterfactual,noisy} --edge proxy` | H4/H6/H8 variants: SPLIT-Match and cloud zero-shot on identical variant notes. The redaction study includes the simulated health worker's one-round answer loop. Output: `results/stress/` |
| `analyze.py` | `--run TEST_proxy` / `--run X --stress-edge proxy` | Pre-specified H1, H2, H3, H5 (point) and H7 subset; with `--stress-edge`, H4, H6, H8. Writes `results/ANALYSIS_<run>.json` |
| `fidelity.py` | `--local TEST_deploy --proxy TEST_proxy` | Field-level and decision-level agreement between the real edge model and its proxy. Qualifies every proxy-edge result |
| `fresh_checks.py` | `extraction --edge {proxy,local}` / `compiler` | Extraction accuracy on 25 fresh expansion patients vs the generator's truth records; compiler agreement summary and audit sheet |
| `run_record_cloud.py` **[post-freeze, exploratory]** | `--split test --factsheets-from TEST_proxy --name REC_cloud_test_proxy` | The cloud model decides from the de-identified FactSheet only. Separates extraction loss from decision-layer loss |
| `audit_compiler.py` **[post-freeze]** | `python experiments/audit_compiler.py` | Independent third-model (gpt-oss-20b) audit of every typed atom on the fresh trials. Authors' adjudication is in `results/fresh/compiler_audit_adjudication.md` |
| `run_ablations.py` **[post-freeze driver, pre-specified ablations]** | `[--only AB_…]` | Hard veto, −L1, −L2, boolean-only, single-model compiler, −verification, −compiler. Each reuses the TEST_proxy fact sheets, so exactly one component changes |
| `analyze_run.py` **[post-freeze]** | `--run TEST_deploy` | Runs the frozen `analyze.py` with a corruption-tolerant call-log loader. The shared log can get a broken line when two processes append at once on Windows. Adds an audit-completeness check: CLOUD_FACT log records vs L2 calls counted by the run. Use this instead of calling `analyze.py` directly |
| `analyze_extra.py` **[post-freeze]** | `python experiments/analyze_extra.py` | H5 AURC-difference CIs, ablation table with CIs, H7 CI, H8 ΔF1 CIs, and the privacy–accuracy frontier table. Writes `results/ANALYSIS_EXTRA.json` |
| `run_replication_dev.py` **[post-freeze, exploratory]** | `python experiments/run_replication_dev.py` | Re-measures the frontier on the 130 development pairs (disjoint trials): runs the edge-class full-note condition (gpt-oss-20b, unchanged `edge_zero_shot`) on dev. With the cached cloud zero-shot on dev and the local Qwen3-4B dev run, it shows whether the test ordering replicates |
| `paper_numbers.py` **[post-freeze, analysis only]** | `python experiments/paper_numbers.py` | Computes every number used in the paper (accuracy with trial-cluster CIs, differences vs cloud zero-shot with McNemar and sign-flip, privacy, latency, stress, ablations, extraction). Writes `results/PAPER_NUMBERS.json`, `paper/generated/numbers.tex` (LaTeX macros) and `paper/generated/frontier.dat` (figure data). A missing result renders as a red [pending] in the PDF, so no number is ever typed by hand |

## 3. `scripts/` — job queues [post-freeze]

| File | What / why |
|---|---|
| `queue_groq.sh` | Groq-only queue: remaining ablations, then the three stress studies. Status goes to `runtime/queue_groq.status` |
| `queue_local.sh` | Starts its own Ollama server with `LLAMA_ARG_CACHE_RAM=0` (llama-server's prompt cache otherwise fills 12 GB of RAM). Then runs TEST_deploy, the local extraction check, the local edge zero-shot baseline and dev_validation with the local edge |

| `retry_redaction.sh`, `retry_counterfactual.sh` | Resume one stress study after a Groq connection drop. Completed calls replay from the cache; each writes its own `*_retry1.log` so the failed log is kept |
| `queue_final.sh` | The remaining runs, started 45 min after launch (user instruction of 2026-11-09). Groq sub-queue: H8 noisy stress, dev replication with the 20B edge model. Local sub-queue: Qwen3-4B full-note zero-shot on test, local extraction check, Qwen3-4B zero-shot on dev, local dev_validation. Each job is retried up to 3 times. Status goes to `runtime/queue_final.status` |
| `resume_devval_local.sh` | Resumes the last `queue_final.sh` job (local dev_validation) after the session ended mid-run. Starts the cache-fixed Ollama server on 127.0.0.1 if none answers and sets `OLLAMA_URL=http://127.0.0.1:11434`, because `localhost` resolves to IPv6 first and may reach the tray app's server, which lacks the fix |

Both are launched with PowerShell `Start-Process` so they survive the end of a Claude session, which killed earlier background jobs. All steps are resumable. On 2026-11-08 the launchers of `queue_groq.sh` and `queue_local.sh` were stopped after their running jobs, on the user's request, so that no new run started without approval.

## 4. `tests/` — 89 unit tests (`.venv/Scripts/python -m pytest -q tests`)

| File | Covers |
|---|---|
| `test_evaluator.py` | Kleene logic, interval comparisons, ECOG/KPS and ×ULN conversion, stage/TNM, closed-world defaults, therapy WITHIN/SINCE/COUNT/filters, conditionals, downgraded atoms never verified, type checker. Generic constraints only; no test-set content |
| `test_policy.py` | A single key never excludes; L1/L2 key combinations; ASK vs site routing; forced-mode resolution; permission guard; verbatim judging of contested atoms; hard-veto and offline ablation behaviour |
| `test_privacy.py` | Guard blocks narrative sentences and IDs on cloud channels and allows minimal facts; deploy mode forbids the proxy; the guard raises before any network I/O; the audit counts leaks and k-anonymity; the structurer drops negations with irrelevant quotes |

## 5. `data/` — copied INDICON dataset (read-only)

| Path | Content |
|---|---|
| `pairs/dev_train.csv`, `dev_validation.csv`, `testing_data.csv` | Labelled (patient, trial) pairs: 104 / 26 / 270 |
| `pairs/split_report.txt` | Verified split statistics (disjointness, balance) |
| `trials/trials_development.jsonl`, `trials_test.jsonl`, `trials_development_expansion.jsonl` | Verbatim criteria per trial, with the `field_checklist` |
| `trials/corpus.jsonl`, `expansion_constraint_coverage.json` | Source corpus and coverage notes for the expansion selection |
| `expansion_patients/` | 25 fresh synthetic patients with generator truth records, plus annotation sheets (annotation skipped by decision) |
| `tooling/extract_trials_v2.py`, `generate_patients.py`, `select_expansion.py` | How the dataset was built (framework-blind trial selection; criteria-blind patient generation) |
| `DATASET_CREATION.md` | Full dataset protocol |

## 6. `baselines_indicon/` — comparators (read-only copies)

- `cache/*.jsonl`: frozen INDICON predictions on test and dev. These are the zero-shot, few-shot, RAG, hard-veto and advisory comparators. They are **not re-run**, so the comparison is against exactly what INDICON reported.
- `results/`: INDICON result files (gate safety, significance, calibration, …). `experiment5_gate_safety_testing_data.json` supplies the flagged 17-FN subset for H7.
- `code/`: the INDICON experiment code that produced them, kept for provenance. `stats.py` is ported from `exp9` / `exp10`.

## 7. `legacy_indicon_src/` — reference only

INDICON's agents, patient extractor, app and Groq pool, copied for reference. Nothing imports them.

## 8. `docs/`

| File | Content |
|---|---|
| `TELMED2027_BRIEF.md`, `TELMED2027_PLAN.md` | Venue facts; research plan, novelty and hypotheses |
| `PREREGISTRATION.md` | **Binding** hypotheses, tests and missing-information conventions; §9 deviations log |
| `DEVELOPMENT_PLAN.md` | Task list and status, model-usage policy, freeze log |
| `FREEZE_MANIFEST_v1.json` | sha256 of the 26 frozen files (`FREEZE_MANIFEST_candidate.json` is the earlier candidate) |
| `ARCHITECTURE.md` | System architecture |
| `EXPERIMENTAL_DESIGN.md` | What was run, how, and why |
| `reference_indicon/` | Copies of INDICON's paper, revision, methodology and results docs |

## 9. `paper/`

- `main.tex`: the TELMED paper, framed as the privacy–accuracy frontier study. Every result is a macro from `generated/numbers.tex`.
- `generated/`: produced by `experiments/paper_numbers.py`; upload it together with `main.tex` (e.g. to Overleaf). There is no LaTeX toolchain on this machine.
- `references.bib` (TELMED), `references_indicon.bib` (earlier paper).
- `docs/WORKSHOP_REVIEW.md` lists the reviewer-level weaknesses and how each was addressed.

## 10. `results/` — all outputs

| Path | Content |
|---|---|
| `programs/{development,expansion,test,test_single}/` + `*_summary.json` | Compiled TrialPrograms and agreement statistics |
| `runs/<run>/` | `factsheets/` (FactSheet and `.l1.json` per patient), `pairs/` (per-pair trace), `predictions.jsonl`, `timing.json`, `metrics.json` |
| `runs/dev_train_proxy_v1…v9`, `dev_val_*`, `dev_train_ab_*` | Development iterations and dev ablations (see `DEV_LEDGER.md`) |
| `runs/TEST_proxy` | Frozen test run, proxy edge |
| `runs/TEST_deploy` | Frozen test run, local edge (deploy mode) |
| `runs/AB_*` | Test ablations |
| `runs/STRESS_*`, `stress/*.jsonl` | Stress-study runs and per-variant outcomes |
| `baselines/*.jsonl` | Re-run baselines (cloud zero-shot rerun and dev, record-to-cloud, edge zero-shot, −compiler) |
| `fresh/` | Extraction checks; compiler audit (`compiler_audit_auto.jsonl`, `compiler_audit_adjudication.md`, `compiler_audit_expansion.md`) |
| `ANALYSIS_*.json` | Analysis outputs |
| `DEV_LEDGER.md` | Development history |
| `RESULTS.md` | **All results, consolidated** |

## 11. `runtime/` (gitignored)

| Path | Content |
|---|---|
| `llm_calls.jsonl` | Every model call: channel, model, run, tag, disclosed fields; payload for non-local channels |
| `llm_cache/` | Response cache |
| `*.log`, `*.status` | Job logs and queue status |
| `ollama_serve*.log` | Ollama server logs |

## Pre-submission review additions (2026-11-09; exploratory)

| File | Purpose |
|---|---|
| `experiments/review_runs.py` | `zs-groq` (hosted zero-shot, optional cache-bypassing repetitions for the noise floor), `zs-local` (direct Ollama zero-shot with latency, tokens/s and peak RAM; own cache `runtime/review_cache/`), `render-long` / `screen-long` (long cluttered notes: verbatim note + filler screened by an independent model), `subset` (stratified pilot20 / sub40). Outputs `results/review/*.jsonl` |
| `experiments/review_analysis.py` | Clinical metrics, trial/patient/two-way bootstraps, noise floor, capacity sweep, long notes, equal-coverage comparison, bandwidth, outage simulation, population uniqueness (uses `data/tooling/generate_patients.py`), local 20B feasibility → `results/REVIEW_ANALYSIS.json` |
| `experiments/make_clinician_packet.py` | Builds `docs/clinician_review/` (20 notes + realism form; all edge-model false exclusions + severity form) |
| `scripts/queue_review_groq.sh` | Hosted review runs (record on real-device sheets, noise floor, Qwen3.8-27B, long notes) |
| `scripts/queue_review_local2.sh` | Local review runs: gpt-oss-20b pilot on a server with `LLAMA_ARG_NO_REPACK=1` (the default load needs a 10.2 GB repack buffer that does not fit in 16 GB), then Qwen3-1.7B, then Qwen3-4B on long notes (all finished 2026-11-09 19:30). `queue_review_local.sh` is the superseded first version |
| `docs/REVIEW_RESPONSE.md` | Point-by-point response to the review |

`experiments/paper_numbers.py` also reads `REVIEW_ANALYSIS.json` and emits the review macros (rec*, miss*, nf*, cap*, long*, cov*, bw*, out*, uniq*, loc*).

### Round-2 review additions (2026-11-09 night)

| File | Purpose |
|---|---|
| `scripts/queue_local20b_full.sh` | gpt-oss-20b on the laptop for all 270 test pairs (no-repack server; same settings as the hosted runs; up to 3 resumable passes). Output `results/review/LOC_gptoss20b_test.jsonl` |
| `scripts/keep_awake_until_done.ps1` | Holds an idle-sleep exemption (`SetThreadExecutionState`) until the status file shows `full20b_done`; changes no power settings |
| `experiments/review_analysis.py` | New sections `same_model` (read vs compiled with trial/patient/two-way CIs) and `local20b_full` (laptop 20B vs cloud, vs cloud run mean, vs hosted runs, vs laptop 4B; run-to-run spread of missed/unnecessary per run; cost); laptop 20B added to the equal-coverage comparison; outage simulation uses measured per-patient CPU times |
| `experiments/tex_to_md.py` | Renders `paper/main.tex` as `paper/PAPER_6PAGE.md`: numbers from `generated/numbers.tex`, Fig. 1 as its data table, Fig. 2 as a structural description, citations numbered in order of first use from `references.bib`. Rerun after editing main.tex |
| `experiments/paper_numbers.py` | Macros `locFull*`, `locVsFour*`, `cloudRunsMiss*`/`cloudRunsUnn*`, `hostedTwentyRunsMiss*`, `covTwentyBLocal*`; `generated/missed.dat` uses the laptop 20B row once the run is complete (done 2026-11-10) |
| `experiments/paper_numbers.py` | New macros `fourBvsSplit{Lo,Hi}{Tr,Pa,Tw}`, `locFull*`, `cap{OneSeven,Four}Lat`; writes `paper/generated/missed.dat` for Fig. 1 |


### Submission build (2026-11-10, Round 3)

| File | Purpose |
|---|---|
| `paper/build_ieee_docx.py` | Writes `paper/TELMED2027_submission.docx` from the official IEEE US Letter template: title, author table, abstract, numbered headings, tables, figures, acknowledgment and 15 references (numbered by first use). All numbers come from `paper/generated/numbers.tex`; markup `{m:macro}`, `{c:key}`. Run with the system Python 3.13 (has python-docx) |
| `paper/figures/make_figures.py` | Fig. 1–3 as vector PDF and 600-dpi PNG (matplotlib, Times New Roman); numbers from `numbers.tex` |
| `paper/docx_to_pdf.ps1` | Converts the .docx to PDF with its own hidden Word instance, prints the page count, and stops only that instance if it hangs (150 s) |
| `paper/ieee_template_src/` | `conference-template-letter.docx` as downloaded from IEEE (Strict OOXML) and `..._transitional.docx`, the same file re-saved by Word so python-docx can open it |

Rebuild order: `experiments/review_analysis.py` → `experiments/paper_numbers.py` → `paper/figures/make_figures.py` →
`paper/build_ieee_docx.py` → `paper/docx_to_pdf.ps1`.


### Round 4 (2026-11-10 evening)

| File | Change |
|---|---|
| `paper/paper_content.py` | **New.** All paper text (title, abstract, body, Box 1, tables) with `{m:}`/`{c:}` markup; `build_ieee_docx.py` imports it |
| `paper/build_ieee_docx.py` | Optional output name (`python paper/build_ieee_docx.py TELMED2027_submission_v2.docx`), shaded recipe box, line breaks and per-table font size in table cells |
| `paper/docx_to_pdf.ps1` | `-Name` parameter (e.g. `-Name TELMED2027_submission_v2`) |
| `paper/figures/make_figures.py` | Fig. 4 (`fig4_device_cost`): missed and unnecessary per 100 patients with laptop seconds per pair; Fig. 2 wording "exclusion needs two keys" |
| `experiments/review_analysis.py` | `section_same_model` now also reports hosted gpt-oss-20b (`gptoss20b_hosted`: −compiler ablation vs TEST_proxy) with recall, missed and three CI schemes |
| `experiments/paper_numbers.py` | Macros `twentyVsSplit*`, `fourBvsSplit{AccRead,AccComp,RecRead,RecComp,MissRead,MissComp}` |


### Round 5 (2026-11-10 night)

| File | Change |
|---|---|
| `experiments/run_record_cloud.py` | `--decider {cloud, edge_proxy, edge_local}`: the cloud model, hosted gpt-oss-20b or local Qwen3-4B decides from a SPLIT-Match fact sheet (same zero-shot system prompt; device-model settings as in the −compiler ablation / local zero-shot) |
| `experiments/review_runs.py` | `zs-local --nocache --rep N`: fresh repeat runs that neither read nor overwrite the reply cache |
| `experiments/gateway_suite.py` | **New.** Regression suite for the frozen privacy guard (prohibited / permitted payloads) plus a partial-overlap audit of the real fact queries → `results/review/GATEWAY_SUITE.{json,md}` |
| `experiments/review_analysis.py` | New sections `missed`, `decomposition`, `local_repeats`, `outage_sensitivity` |
| `experiments/paper_numbers.py` | Macros `rec*`, `recD*`, `mcE*`, `dec*`, `outHalf*`, `gw*`, `rep*`, `uniq*TenK` |
| `scripts/queue_round5_local.sh` | Laptop queue: Qwen3-4B on its fact sheets, fresh Qwen3-4B repeat (270), fresh gpt-oss-20b repeat (40), `ollama show` model details |
| `paper/build_ieee_docx.py` | `ALLOW_PENDING=1` renders missing numbers as [pending] for layout previews only |

### Round 7 (2026-11-13)

| File | Change |
|---|---|
| `experiments/l2_attribution.py` | **New.** Exclusion route of every missed eligible pair (TEST_proxy, AB_noL2, TEST_deploy) → `results/review/L2_ATTRIBUTION.json` |
| `experiments/paper_numbers.py` | Macros `ltwo*`, `privDistinctDeploy` |
| `paper/build_ieee_docx.py` | `{n:macro}` token (sign-flipped number for "system minus reference"); tables and headings kept with following text |
| `paper/paper_content.py` | Round-7 rewrite; master output `paper/TELMED2027_submission_v4.docx` |
