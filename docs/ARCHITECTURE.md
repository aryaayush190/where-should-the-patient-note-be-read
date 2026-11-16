# SPLIT-Match — System Architecture

SPLIT-Match is a privacy-split, edge-first pre-screener for clinical trials. It is written for a tele-oncology setting: a community health worker or a district clinic decides whether a lung-cancer patient (NSCLC) should be referred for a trial screening visit.

The design starts from one fact about the data.

- **Trial criteria are public.** They are published on ClinicalTrials.gov.
- **Patient notes are private.**

So the expensive language reasoning over criteria can run in the cloud, once per trial, on public text only. Everything that touches the patient runs on the device. Only minimal single-fact questions may cross the boundary, and only when needed. Every one of those crossings is logged and audited.

```
                PUBLIC SIDE (cloud)                         PRIVATE SIDE (edge device)
 ┌───────────────────────────────────────────┐   ┌──────────────────────────────────────────────┐
 │ Trial criteria (verbatim, ClinicalTrials) │   │ Patient note (free text, never leaves)        │
 │            │                              │   │            │                                 │
 │   (1) Dual-model compiler                 │   │   (2) Edge structurer                         │
 │   gpt-oss-120b  ║  qwen3.8-27b            │   │   SLM reader  +  regex reader                 │
 │   typed atoms   ║  typed atoms            │   │   → FactSheet (intervals, quotes, verified?)  │
 │        └── per-atom agreement ──┘         │   │            │                                 │
 │   TrialProgram (agreed / downgraded)  ────┼──►│   (3) Three-valued evaluator (Kleene, local)  │
 │   (cached on disk, once per trial)        │   │            │  T / F / U per atom              │
 │                                           │   │   (4) Evidence-conditioned authority policy   │
 │   (5b) L2 cloud judge  ◄── one criterion ─┼───┤   (5a) L1 edge judge (batched per patient)    │
 │        + minimal fact statement           │   │            │                                 │
 │        + relevant record fields (guarded) │   │   ELIGIBLE | NOT_ELIGIBLE | NEED_INFO | DEFER │
 └───────────────────────────────────────────┘   └──────────────────────────────────────────────┘
                 ▲ every call passes through the privacy gateway (llm.py) and is logged ▲
```

Cost structure: **O(T + P)** model calls, plus occasional per-pair cloud fact queries.
- One compile per trial (cloud).
- One structuring call and one batched L1 call per patient (edge).
- Per-pair evaluation is deterministic and takes about 1 ms.

---

## 1. Cloud compiler: public criteria → typed program (`splitmatch/compiler.py`)

1. **Deterministic line splitting** (no model).
   - Criteria are split on blank lines and bullets.
   - A lowercase fragment is merged into the previous line, unless that line is a cohort header ("Cohort A:", "Phase I only:").
   - Each line keeps its section: inclusion or exclusion.
2. **Two independent compilers from different model families.**
   - `openai/gpt-oss-120b` (primary) and `qwen/qwen3.8-27b` (secondary) each compile the numbered lines into typed atoms.
   - Long trials are chunked: 22 lines per call for gpt-oss, 16 for qwen.
   - Prompt v1.2 has explicit rules:
     - 7a: listed alternatives become one `ANY` atom;
     - 7b: lines that only grant permission ("X is allowed") are not requirements.
3. **Type check plus one repair round.** `schema.type_errors` rejects unknown fields, wrong operators, bad units and duplicate ids. The error list is sent back once.
4. **Atom-level agreement.**
   - A typed atom of the primary compiler keeps deterministic authority only if the secondary compiler produced an equivalent atom on the same line.
   - Equivalence means: same field, same direction, threshold within 2%, same therapy filter. Stages are compared on their finest substages.
   - Otherwise the atom is **downgraded**: it can never exclude deterministically. It is judged later on its verbatim criterion line, in that line's section polarity.
5. **Stage-alternative merge.** Separate stage requirements produced from one line ("IIIB with effusion" / "IV") are merged into an `ANY`. This stops each one from acting as an independent veto.

**Atom types:**

| Type | Meaning |
|---|---|
| `CMP` | Numeric comparison: field op value |
| `IN` | Enum membership: stage, histology, biomarker status |
| `IS` | Boolean condition present: CHF, pregnancy, infection, … |
| `HAS` | Prior therapy of a class or agent |
| `COUNT` | Number of prior lines or regimens |
| `WITHIN` / `SINCE` | Therapy within / not within N months |
| `IF` | Conditional |
| `ANY` / `ALL` | Disjunction / conjunction |
| `JUDGE` | Free-text criterion left to the judges |
| `UNSCREENABLE` | Consent, investigator opinion and similar; sent to the site checklist |

Only public trial text is sent here, over channel `CLOUD_PUBLIC`.

## 2. Edge structurer: private note → FactSheet (`splitmatch/structurer.py`, `regex_reader.py`, `schema.py`)

- **Reader 1, the small language model.**
  - Deployment: local `qwen3:4b-instruct` via Ollama (`EDGE_LOCAL`).
  - Development: the Groq model `gpt-oss-20b` stands in for it (`EDGE_PROXY`).
  - It returns `{"v": value, "q": verbatim quote}` per field, plus therapy events (class, agents, setting, months since last dose, ongoing).
- **Reader 2, a deterministic regex reader.** It is conservative: it extracts a value only from unambiguous phrasing.
- **A fact is *verified* iff all three hold:**
  - the quote is found verbatim in the note (*grounded*);
  - the quote is *relevant* to the field (a keyword lexicon blocks one quote being reused for unrelated fields);
  - the regex reader produced an equal value.
- **Kept but unverified:** single-reader facts. Ungrounded negations and null values are dropped.
- **Value representation:** numbers are closed intervals [lo, hi]. For example, "1–3 months ago" becomes [1, 3], and KPS 70 seen through an ECOG criterion is converted as an interval. Coarse statements therefore stay exact.
- **Schema:** 47 fields, from age and stage through biomarkers, cardiac history and labs, plus therapy events of 9 classes.

## 3. Three-valued evaluator (`splitmatch/evaluator.py`)

- Deterministic, local, no model and no network.
- Strong Kleene logic over {T, F, U}. Interval comparison returns U only when the interval genuinely straddles the threshold.
- Each result carries flags:
  - **verified:** all facts used are verified, the atom is not downgraded, and no approximate conversion falls within ±10% of the threshold;
  - **assumed:** the result rests on a closed-world pertinent negative.
- Supporting machinery:
  - ECOG↔KPS and ×ULN conversion;
  - stage subsumption, e.g. IV ⊇ IVA/IVB;
  - therapy-event matching, where `systemic` covers every systemic class;
  - interval arithmetic for WITHIN, SINCE and COUNT.

## 4. Evidence-conditioned authority policy (`splitmatch/policy.py`)

**Two-key exclusion.** An exclusion is authoritative only with two independent keys. Accepted pairs:

| Key pair |
|---|
| (a) Deterministic verdict on verified facts |
| (b) Deterministic verdict on unverified facts, confirmed by the L1 judge |
| (c) L1 judge confirmed by the L2 cloud judge |

- A single key never excludes.
- Inclusions may be *provisional*, i.e. rest on unverified or assumed facts.
- Rationale: at pre-screening, a false exclusion is final, while a false inclusion is caught at the site.

**Missing-information routing:**

| Case | Route |
|---|---|
| Excluding condition not mentioned | Presumed absent (provisional) |
| Clinical inclusion requirement not mentioned (disease or treatment history) | Selective mode: **ASK** (a question for the health worker). Forced mode: L2 judges on "not stated in the note" plus the relevant record fields; unknown counts as not excluding |
| Other inclusion items (labs, scans within N weeks, consent, …) | Site screening checklist |
| Permission lines | Never requirements (deterministic guard) |

**Outputs:**
- *Selective* (deployment): `ELIGIBLE / NOT_ELIGIBLE / NEED_INFO / DEFER`.
- *Forced*: binary, for comparison with gold labels.
- Per pair, an uncertainty score: `u = n_L2 + n_forced_unknown + 0.5·n_provisional`.
- An audit trace of every atom's route.

## 5. Escalation ladder (`splitmatch/ladder.py`, `render.py`)

- **L1 edge judge.**
  - One call per patient, batched over all residual criteria of all that patient's trials. Batches are chunked at 12, split on failure, and missing items are marked "unavailable".
  - It reads the full note, because it runs on the device.
  - Per criterion it returns T/F/U, whether the fact is stated, and a *minimal fact statement* with no identifiers and no narrative copying.
- **L2 cloud judge** (`gpt-oss-120b`, channel `CLOUD_FACT`).
  - It sees one criterion statement, the L1 minimal fact (or "not stated"), and the structured record values of the fields relevant to that criterion.
  - It runs behind the fail-closed privacy guard.
  - It is used for reasoning on stated-but-ambiguous facts, and as the second key for exclusions only L1 supports.

## 6. Privacy gateway and accounting (`splitmatch/llm.py`, `privacy.py`)

- Every model call goes through `llm.call(channel, …)`.

| Channel | What it carries |
|---|---|
| `CLOUD_PUBLIC` | Trial text only (guarded) |
| `CLOUD_FACT` | Minimal single-criterion fact (guarded) |
| `EDGE_LOCAL` | On-device; any content |
| `EDGE_PROXY` | Groq model standing in for the edge model; forbidden in deploy mode |
| `BASELINE_CLOUD` | Full-note baselines, logged as egress |

- **The guard fails closed.** It raises before any network I/O if a cloud payload contains:
  - a sentence of any registered patient narrative (normalised matching), or
  - a patient or pair identifier.
- **Logging:** every call is logged to `runtime/llm_calls.jsonl`, with payloads for non-local channels. The H2 privacy numbers are recomputed from this log by a post-hoc audit that is independent of the runtime guard.
- **Caching:** responses are cached by a hash of (model, messages, parameters). Runs are therefore exactly replayable, and interrupted jobs resume free.

## 7. Design properties claimed and how each is checked

| Property | Mechanism | Evidence |
|---|---|---|
| No raw narrative leaves the device | Guard + post-hoc log audit | H2 (0 violations on test) |
| Compilation errors lose authority | Dual-model agreement | Fresh-trial audit: auditor flags 20% of agreed vs 56% of downgraded atoms (p = 9e-7); 2.8% real errors among agreed |
| A single error cannot exclude | Two-key policy | Unit tests (`tests/test_policy.py`); hard-veto ablation |
| Cost O(T + P) | Compile once per trial; one batched L1 per patient | Call counts per run (H3) |
| Replayable and auditable | Call log, response cache, per-pair trace JSON | `results/runs/*/pairs/*.json` |

The measured results, including where the design falls short, are in `results/RESULTS.md`.
