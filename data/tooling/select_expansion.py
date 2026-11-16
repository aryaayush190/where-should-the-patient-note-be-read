"""
select_expansion.py  —  READ-ONLY development-pool expansion selection.

Selects ~12-18 ADDITIONAL NSCLC trials from corpus.jsonl using the framework-BLIND
pipeline documented in DATASET_CREATION.md §3.3, disjoint from BOTH the 22
development trials and the 18 held-out test trials.

Reuses from extract_trials_v2.py (not reimplemented): load_corpus, build_records,
detect_fields, and the DEV_TRIALS / TEST_TRIALS id sets. The four screen functions
(is_nsclc, is_therapeutic, has_complete_criteria, classify_mechanism) are NOT
present in that file (only the final id lists were committed), so they are
implemented here VERBATIM from DATASET_CREATION.md §3.3 — same keyword lists,
same thresholds, same priority order.

Nothing in the framework (rules/parser/prompt/config) is touched. Only the test
file's trial_id field is read (for the disjointness check), nothing else.
New seed for this expansion draw: 3027 (distinct from the original 2026).
"""
import json
import random
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# ---- reuse existing, committed logic --------------------------------------
from extract_trials_v2 import load_corpus, build_records, DEV_TRIALS, TEST_TRIALS

CORPUS = HERE / "corpus.jsonl"
TEST_JSONL = HERE / "trials_test.jsonl"
OUT = HERE / "trials_development_expansion.jsonl"
SEED = 3027
TARGET = 15          # midpoint of the requested 12-18

EXCLUDE_IDS = set(DEV_TRIALS) | set(TEST_TRIALS)   # the 40 ids to exclude

# ---------------------------------------------------------------------------
# Screen functions — implemented verbatim from DATASET_CREATION.md §3.3
# ---------------------------------------------------------------------------
NSCLC_KEEP = ["non-small cell lung", "non small cell lung", "non-small-cell lung",
              "nsclc", "squamous cell lung", "lung adenocarcinoma", "lung non-small",
              "lung cancer", "lung neoplasm"]
NSCLC_SPECIFIC = ["non-small", "nsclc", "non small", "squamous cell lung", "lung adenocarcinoma"]
OTHER_PRIMARY = ["breast cancer", "ovarian", "lymphoma", "leukemia", "melanoma",
                 "renal cell", "head and neck", "testicular", "small cell lung cancer",
                 "sclc", "asthma", "cachexia", "cushing", "tuberculous", "mesothelioma",
                 "hepatocellular", "esophageal", "laryngeal", "hypopharyngeal"]


def is_nsclc(rec) -> bool:
    dz = " ; ".join(rec.get("diseases_list", []) or []).lower()
    if not any(t in dz for t in NSCLC_KEEP):
        return False
    if (not any(t in dz for t in NSCLC_SPECIFIC)) and any(t in dz for t in OTHER_PRIMARY):
        return False
    return True


SUMMARY_DROP = ["observational", "registry", "quality of life", "imaging study",
                "biomarker study", "screening study", "prevention trial",
                "feasibility of", "questionnaire", "survey"]
TITLE_DROP = ["pain in patients", "shortness of breath", "dyspnea", "rash",
              "pulmonary fibrosis", "nausea", "fatigue", "supportive care",
              "esophageal pain", "cachexia", "cough in"]


def is_therapeutic(rec) -> bool:
    phase = (rec.get("phase") or "").lower()
    drugs = rec.get("drugs_list") or []
    if ("phase" not in phase) and (not drugs):
        return False
    summ = (rec.get("brief_summary") or "").lower()
    if any(s in summ for s in SUMMARY_DROP):
        return False
    title = (rec.get("title") or "").lower()
    if any(s in title for s in TITLE_DROP):
        return False
    return True


def has_complete_criteria(rec) -> bool:
    inc = rec.get("inclusion_criteria") or ""
    exc = rec.get("exclusion_criteria") or ""
    return len(inc) >= 300 and len(exc) >= 300


MECH_ORDER = [
    ("Immunotherapy", ["pembrolizumab", "nivolumab", "atezolizumab", "durvalumab",
                        "pd-1", "pd-l1", "ipilimumab", "avelumab", "sintilimab",
                        "immune checkpoint", "immunotherapy"]),
    ("Targeted-TKI", ["erlotinib", "gefitinib", "afatinib", "osimertinib", "crizotinib",
                      "alectinib", "egfr", "alk", "tyrosine kinase", "tki", "ceritinib",
                      "dacomitinib", "icotinib", "almonertinib", "cabozantinib",
                      "anlotinib", "tarceva"]),
    ("Anti-angiogenic", ["bevacizumab", "ramucirumab", "nintedanib", "angiogen", "vegf",
                         "endostatin", "axitinib", "ag-013736", "bibf"]),
    ("Chemoradiation", ["chemoradi", "radiation", "radiotherapy", "concurrent chemo"]),
    ("Chemotherapy", ["cisplatin", "carboplatin", "pemetrexed", "paclitaxel", "docetaxel",
                      "gemcitabine", "vinorelbine", "topotecan", "chemotherapy", "platinum"]),
]


def classify_mechanism(rec) -> str:
    text = " ".join([" ".join(rec.get("drugs_list", []) or []),
                     rec.get("brief_summary", "") or "",
                     rec.get("title", "") or ""]).lower()
    for label, kws in MECH_ORDER:
        if any(k in text for k in kws):
            return label
    return "Other/Novel-agent"


# ---------------------------------------------------------------------------
# Qualified-constraint scanners (a-d) — verbatim-criteria signal detection
# ---------------------------------------------------------------------------
PAT_QUANTIFIED = re.compile(
    r"(?:more than|at least|no more than|up to|greater than|fewer than|"
    r"≥|>=|>)\s*(?:one|two|three|four|1|2|3|4)\s+"
    r"(?:prior|previous|preceding)?\s*(?:line|lines|regimen|regimens|course|courses"
    r"|chemo\w*|treatment|therap\w*)"
    r"|(?:one|two|three|1|2|3)\s+(?:or more\s+)?(?:prior|previous)\s+"
    r"(?:line|regimen|chemo\w*|therap\w*)", re.I)
PAT_TEMPORAL = re.compile(
    r"within\s+\d+\s*(?:day|days|week|weeks|month|months|year|years)"
    r"|in the (?:past|last|previous)\s+\d+\s*(?:day|week|month|year)"
    r"|\d+\s*(?:day|days|week|weeks|month|months)\s+(?:prior|before|preceding|of)"
    r"|[≤]\s*\d+\s*(?:day|week|month)", re.I)
PAT_CONDITIONAL = re.compile(
    r"\bunless\b|\bexcept\b|except if|provided that|only if"
    r"|that would\s+(?:overlap|impede|result in|preclude|require)"
    r"|if\b[^.\n]{0,60}\b(?:then|would|is not eligible|are not eligible)\b", re.I)
PAT_INCLUSIVE = re.compile(
    r"stage[^.\n]{0,40}\([^)]*(?:including|with|effusion|pleural)[^)]*\)"
    r"|\([^)]*\bincluding\b[^)]*\)"
    r"|\b(?:iiia|iiib|iii|ii)\b\s*(?:,|/|\bor\b)\s*\b(?:iiib|iv|iii)\b"
    r"|stage\s+[ivx]+[ab]?\s*(?:,|/|\bor\b)\s*[ivx]+[ab]?", re.I)


def scan_constraints(rec):
    text = f"{rec.get('inclusion_criteria','')}\n{rec.get('exclusion_criteria','')}"
    def m(pat):
        g = pat.search(text)
        return g.group(0).strip()[:60] if g else ""
    return {"quantified": m(PAT_QUANTIFIED), "temporal_washout": m(PAT_TEMPORAL),
            "conditional": m(PAT_CONDITIONAL), "inclusive_multistage": m(PAT_INCLUSIVE)}


# ---------------------------------------------------------------------------
# Clinical-relevance review flag (Step 7) — flag, do NOT auto-remove
# ---------------------------------------------------------------------------
REVIEW_SIGNALS = ["mesothelioma", "hepatocellular", "solid tumor", "solid tumour",
                  "melanoma", "metastas", "ebus", "endobronchial ultrasound",
                  "dysplasia", "pleural effusion" ]  # borderline-purpose cues


def review_flag(rec):
    hay = " ".join([rec.get("title", ""), rec.get("brief_summary", ""),
                    " ".join(rec.get("diseases_list", []) or [])]).lower()
    hits = [s for s in REVIEW_SIGNALS if s in hay]
    # only flag when NSCLC is not clearly the sole/primary disease context
    dz = " ".join(rec.get("diseases_list", []) or []).lower()
    nsclc_primary = any(t in dz for t in NSCLC_SPECIFIC)
    return hits if (hits and not nsclc_primary) else ([f"(nsclc-primary; note:{','.join(hits)})"] if hits else [])


# ---------------------------------------------------------------------------
def main():
    corpus = load_corpus(CORPUS)
    print(f"corpus: {len(corpus)} trials")

    # test file: read ONLY trial_id (integrity)
    test_ids_from_file = {json.loads(l)["trial_id"] for l in open(TEST_JSONL, encoding="utf-8") if l.strip()}

    # candidate pool = corpus minus the 40 dev+test ids
    candidates = [r for tid, r in corpus.items() if tid not in EXCLUDE_IDS]
    print(f"candidate pool (corpus - 22 dev - 18 test = -{len(EXCLUDE_IDS)}): {len(candidates)}")

    s1 = [r for r in candidates if is_nsclc(r)]
    s2 = [r for r in s1 if is_therapeutic(r)]
    s3 = [r for r in s2 if has_complete_criteria(r)]
    print(f"Step1 NSCLC screen:            {len(s1)}")
    print(f"Step2 therapeutic screen:      {len(s2)}")
    print(f"Step3 complete-criteria (>=300 both): {len(s3)}")

    # Step 4 — mechanism classification
    for r in s3:
        r["_mech"] = classify_mechanism(r)
    by_mech = defaultdict(list)
    for r in s3:
        by_mech[r["_mech"]].append(r)
    print("Step4 mechanism classes:", {k: len(v) for k, v in sorted(by_mech.items())})

    # Step 5 + 6 use the NEW seed 3027 for the whole stochastic portion
    random.seed(SEED)

    # Step 5 — protocol-family dedup within each mechanism class
    deduped = []
    for mech, recs in by_mech.items():
        fam = defaultdict(list)
        for r in recs:
            drugs = sorted((d.lower() for d in (r.get("drugs_list") or [])))[:2]
            key = tuple(drugs) if drugs else (r["_id"],)  # no drugs -> unique family
            fam[key].append(r)
        for key, group in fam.items():
            deduped.append(random.choice(group))
    dedup_by_mech = defaultdict(list)
    for r in deduped:
        dedup_by_mech[r["_mech"]].append(r)
    print(f"Step5 protocol-family dedup:   {len(deduped)} "
          f"({ {k: len(v) for k, v in sorted(dedup_by_mech.items())} })")

    # Step 6 — fixed-seed stratified sampling, quota proportional to class share
    total = len(deduped)
    selected = []
    alloc = {}
    for mech, recs in sorted(dedup_by_mech.items()):
        quota = max(1, round(TARGET * len(recs) / total))
        quota = min(quota, len(recs))
        alloc[mech] = quota
        selected.extend(random.sample(recs, quota))
    # keep within 12-18: trim/extend deterministically if needed
    print(f"Step6 stratified sample (seed={SEED}, target~{TARGET}) alloc: {alloc} -> {len(selected)} trials")

    # Step 7 — clinical-relevance review FLAG (not auto-removed)
    for r in selected:
        r["_review"] = review_flag(r)

    selected_ids = [r["_id"] for r in selected]

    # ---- Disjointness check (explicit, per set) ----
    dev_overlap = sorted(set(selected_ids) & set(DEV_TRIALS))
    test_overlap = sorted(set(selected_ids) & set(TEST_TRIALS))
    test_overlap_file = sorted(set(selected_ids) & test_ids_from_file)
    print("\n===== DISJOINTNESS CHECK =====")
    print(f"selected: {len(selected_ids)} | unique: {len(set(selected_ids))}")
    print(f"overlap with 22 DEV trials : {dev_overlap or 'NONE'}")
    print(f"overlap with 18 TEST trials (from extract_trials_v2 TEST_TRIALS): {test_overlap or 'NONE'}")
    print(f"overlap with 18 TEST trials (cross-check, trial_id from trials_test.jsonl): {test_overlap_file or 'NONE'}")

    # ---- Qualified-constraint coverage table ----
    print("\n===== QUALIFIED-CONSTRAINT COVERAGE =====")
    hdr = f"{'trial_id':14s} {'mechanism':16s} {'quant':5s} {'temporal':8s} {'cond':5s} {'incl/list':9s}"
    print(hdr); print("-" * len(hdr))
    counts = Counter()
    rows = []
    for r in sorted(selected, key=lambda x: (x["_mech"], x["_id"])):
        c = scan_constraints(r)
        yn = {k: ("Y" if v else "n") for k, v in c.items()}
        for k, v in c.items():
            if v:
                counts[k] += 1
        print(f"{r['_id']:14s} {r['_mech']:16s} {yn['quantified']:5s} "
              f"{yn['temporal_washout']:8s} {yn['conditional']:5s} {yn['inclusive_multistage']:9s}"
              + (f"   [REVIEW: {r['_review']}]" if r["_review"] else ""))
        rows.append({"trial_id": r["_id"], "mechanism_class": r["_mech"],
                     "quantified": c["quantified"], "temporal_washout": c["temporal_washout"],
                     "conditional": c["conditional"], "inclusive_multistage": c["inclusive_multistage"],
                     "review_flag": r["_review"]})
    n = len(selected)
    print(f"\nSummary (of {n} selected):")
    for k in ["quantified", "temporal_washout", "conditional", "inclusive_multistage"]:
        print(f"  {k:22s}: {counts[k]}/{n}")

    # ---- Save expansion trials in the SAME record format as trials_development.jsonl ----
    trial_map = {r["_id"]: r["_mech"] for r in selected}
    records = build_records(corpus, trial_map, "development_expansion")
    with open(OUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n[saved] {OUT}  ({len(records)} trials)")

    # also save the constraint-coverage table as JSON for review
    cov = HERE / "expansion_constraint_coverage.json"
    json.dump({"seed": SEED, "n_selected": n, "allocation": alloc,
               "summary_counts": dict(counts), "rows": rows},
              open(cov, "w", encoding="utf-8"), indent=2)
    print(f"[saved] {cov}")


if __name__ == "__main__":
    main()
