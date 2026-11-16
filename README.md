# Where Should the Patient Note Be Read?

**Missed Referrals, Privacy and Device Cost of LLM Pre-Screening for Clinical Trials in Telemedicine**

Code, data and released outputs for the paper submitted to the **6th TELMED Workshop at IEEE PerCom 2027** (Goa, India).

Ayush Arya¹, Neha Kriti¹, Harsha Kulkarni², Sarthak Srivastava¹, Shruti Kaushik³, Varun Dutt¹ (corresponding author)
¹ Applied Cognitive Science Lab, Indian Institute of Technology Mandi, India · ² University Institute of Technology, Himachal Pradesh University, India · ³ Syneos Health, India

📄 Paper: [`paper/TELMED2027_paper.pdf`](paper/TELMED2027_paper.pdf)

---

## What the paper does

A health worker at a district clinic pre-screens a patient on the clinic laptop and refers likely-eligible patients to a trial site by teleconsultation. A cloud large language model (LLM) pre-screens well, but only if it receives the full patient note. We measure what it costs to keep that note on the device, at four levels of patient information sent to the cloud: **full note, de-identified record, single facts, nothing**. Every device step runs on a 16 GB CPU-only laptop.

The main measure is **missed eligible patients**, the one error the trial site cannot correct later. Main findings on 270 synthetic lung cancer patient–trial pairs from 18 unseen trials:

- **SPLIT-Match** is a privacy-split pre-screener that compiles criteria into rules and sends only single facts to the cloud. It missed 28 of 69 eligible pairs, against 5–10 for the full-note cloud model. Most of these misses came from a cloud judge that saw a single fact.
- **Reading beats compiling.** Holding the device model fixed, reading the note instead of running the rules cut missed eligible pairs from 28 to 11 with Qwen3-4B (laptop) and from 30 to 6 with gpt-oss-20b (hosted).
- **Open models reading the note on the laptop** missed 10–11 eligible pairs. This is not a statistically significant increase over the cloud, although the uncertainty is wide. They made more unnecessary referrals instead, at 37 s (Qwen3-4B) and 138 s (gpt-oss-20b) per pair.

## Repository structure

```
.
├── splitmatch/            the SPLIT-Match system (library); 26 files frozen before the test run
├── experiments/           experiment drivers and analysis scripts
├── scripts/
│   ├── reproduce.py       regenerate the paper's numbers from the released outputs
│   ├── restore_artifacts.py   unpack artifacts/ into runtime/
│   ├── verify_freeze.py   check the frozen files against the pre-test SHA-256 manifest
│   └── run_queues/        the exact job queues used for the study (Windows, Git Bash)
├── tests/                 unit tests (evaluator, authority policy, privacy gateway)
├── data/                  synthetic patient–trial pairs, real trial criteria, generator tooling
├── baselines_indicon/     cached replies and results of the earlier full-note baselines
├── results/               all outputs: per-pair predictions, compiled programs, analyses
├── artifacts/             compressed call log and reply caches (see artifacts/README.md)
├── docs/                  pre-specified analysis plan, freeze manifest, design, code reference
└── paper/                 final PDF, figure scripts, generated numbers, Word build
```

## Setup

Tested with Python 3.13 on Windows 11. The analysis code is platform-independent.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q tests
python scripts/verify_freeze.py  # 25/25 frozen code files match the pre-test manifest
```

## Reproducing the paper

| Level | What it does | Needs | Command |
|---|---|---|---|
| 1 | Regenerates every number in the paper (`paper/generated/numbers.tex`) from the released analyses, per-pair predictions and call log | CPU only, ~5 min | `python scripts/reproduce.py` |
| 2 | Level 1, plus recomputes the analyses (hypothesis tests, bootstrap CIs, ablations, stress tests) from the per-pair predictions | CPU only, ~10 min | `python scripts/reproduce.py --level 2` |
| — | Redraws Figs. 1–3 | `pip install -r requirements-paper.txt` | `python scripts/reproduce.py --figures` |
| 3 | Re-runs the experiments themselves | Groq API keys (`groq_keys.txt`, see `groq_keys.example.txt`) and [Ollama](https://ollama.com) with `qwen3:4b-instruct`, `qwen3:1.7b`, `gpt-oss:20b` | See below |

Levels 1 and 2 call no model. Outputs are written in place, so `git diff --stat` afterwards shows what changed; on our machine both levels reproduce `paper/generated/numbers.tex` exactly.

**Level 3.** Calls are cached by request content, so after `python scripts/restore_artifacts.py` an identical re-run replays the released replies. Delete `runtime/llm_cache/` to force fresh calls. Main entry points:

```bash
python experiments/compile_trials.py test                                          # compile criteria (cloud)
SPLITMATCH_MODE=deploy python experiments/run_splitmatch.py --split test --edge local --name TEST_deploy
python experiments/run_splitmatch.py --split test --edge proxy --name TEST_proxy  # hosted stand-in
python experiments/run_ablations.py                                                # pre-specified ablations
python experiments/run_stress.py redaction|counterfactual|noisy --edge proxy
python experiments/run_zero_shot.py --split test --where cloud --name ZS_cloud_test_rerun
python experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_test --think low --max-tokens 1500
python experiments/run_record_cloud.py --split test --factsheets-from TEST_proxy --name REC_edge20b_test_proxy --decider edge_proxy
```

In `SPLITMATCH_MODE=deploy` the privacy gateway refuses the hosted stand-in, so patient text is processed only by the local Ollama model. On a 16 GB laptop, `gpt-oss:20b` needs `LLAMA_ARG_NO_REPACK=1` (weights memory-mapped from disk); see `scripts/run_queues/queue_local20b_full.sh`. `docs/CODE_DOCUMENTATION.md` describes every script.

## Where each result comes from

| Paper | Source file | Produced by |
|---|---|---|
| Table I, Fig. 3 (privacy levels, recall CIs) | `results/PAPER_NUMBERS.json`, `results/REVIEW_ANALYSIS.json` → `clinical`, `missed` | `analyze.py`, `review_analysis.py` |
| Sec. V-A: H1, cloud-judge attribution (30 → 8 missed) | `results/ANALYSIS_TEST_deploy.json`, `results/review/L2_ATTRIBUTION.json` | `analyze.py`, `l2_attribution.py` |
| Table II (note / fact sheet / rules) | `results/REVIEW_ANALYSIS.json` → `decomposition`, `same_model` | `review_analysis.py` |
| Table III (models reading the note, laptop time) | `results/REVIEW_ANALYSIS.json` → `capacity`, `local20b_full`, `local_repeats` | `review_analysis.py` |
| Sec. V-D robustness (run-to-run noise, long notes) | `results/REVIEW_ANALYSIS.json` → `noise`, `long_notes` | `review_analysis.py` |
| Sec. V-E privacy (gateway suite, uniqueness, network link) | `results/review/GATEWAY_SUITE.json`, `results/REVIEW_ANALYSIS.json` → `uniqueness`, `outage_sim` | `gateway_suite.py`, `review_analysis.py` |
| Pre-specified ablations, H3–H8 | `results/ANALYSIS_EXTRA.json`, `results/ANALYSIS_STRESS_TEST_proxy_proxy.json` | `analyze_extra.py`, `analyze.py` |
| Every number as printed | `paper/generated/numbers.tex` | `paper_numbers.py` |

Per-pair predictions are in `results/runs/<run>/predictions.jsonl` (with a decision trace per pair in `results/runs/<run>/pairs/`), `results/baselines/` and `results/review/`. `results/README.md` lists every run.

## Study safeguards

- **Analysis plan:** `docs/PREREGISTRATION.md` fixed the hypotheses (H1–H8), the non-inferiority margin, the ablations and the statistics before any test-set run. Its deviation log records every later change.
- **Freeze:** SPLIT-Match was developed on development data only, frozen with a SHA-256 manifest of 26 files (`docs/FREEZE_MANIFEST_v1.json`): the 25 code files and the analysis plan. It was then run once on the test set. `scripts/verify_freeze.py` checks the 25 code files; the analysis plan was edited after the freeze, and its deviation log (section 9) records dated changes with reasons.
- **Statistics:** 95% bootstrap CIs that resample trials (18 clusters, as pre-specified), with two-way trial × patient resampling as a sensitivity check; exact McNemar tests.
- **Disclosure:** analyses marked *exploratory* in the paper were added after the test run.

## Data

All patients are **synthetic**: attributes were sampled without reference to any trial and rendered as short narratives. Trial criteria are verbatim public records from ClinicalTrials.gov. No real patient data were used and no human participants were involved. See `data/README.md` and `data/DATASET_CREATION.md`. The benchmark was established in our earlier study on the same data (Arya et al., IEEE INDICON 2026).

## Hardware and runtime

Intel i5-13500H (12 cores), 16 GB RAM, no GPU; Ollama 0.40.15 with default CPU threading. Qwen3 models used Q4_K_M quantisation and gpt-oss-20b its native MXFP4 format, with context 8,192 tokens, temperature 0 and seed 0. Hosted models (gpt-oss-120b, gpt-oss-20b, Qwen3.8-27B) were served by Groq.

## Citation

```bibtex
@inproceedings{arya2027patientnote,
  author    = {Ayush Arya and Neha Kriti and Harsha Kulkarni and Sarthak Srivastava and Shruti Kaushik and Varun Dutt},
  title     = {Where Should the Patient Note Be Read? Missed Referrals, Privacy and Device Cost of {LLM} Pre-Screening for Clinical Trials in Telemedicine},
  booktitle = {Proc. IEEE Int. Conf. Pervasive Computing and Communications Workshops (PerCom Workshops), TELMED},
  year      = {2027},
  note      = {Submitted}
}
```

See also `CITATION.cff`.

## License

Code is released under the [MIT License](LICENSE). Data, results and documentation are released under [CC BY 4.0](LICENSE-DATA.md). Trial criteria are public records from ClinicalTrials.gov.

## Acknowledgment

This work was supported by grants from Syneos Health (IITM/CONS/SHILC-USA/VD/111), the Department of Science and Technology (IITM/DST/VD/603), the All India Council for Technical Education (IITM/IKS-MoE/VD/548), and Mr. Satish and Kamlesh Agarwal Master Account (IITM/DORA/MASTER Account/2025/03) awarded to Prof. Varun Dutt. We thank IIT Mandi for infrastructure and computational resources. *Competing interests:* S. Kaushik is affiliated with Syneos Health, one of the funders.

## Contact

Varun Dutt — varun@iitmandi.ac.in (corresponding author) · Ayush Arya — aryaayush190@gmail.com
