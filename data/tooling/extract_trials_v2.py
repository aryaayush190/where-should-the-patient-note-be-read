"""
extract_trials_v2.py

Extracts BOTH trial sets for the NSCLC eligibility dataset:
  - DEVELOPMENT set (22 trials): the original mechanism-stratified shortlist, used
    for framework engineering, prompt design, and ablation development. These were
    selected with awareness of parser coverage and are therefore NOT used for
    headline evaluation numbers.
  - HELD-OUT TEST set (18 trials): selected by a framework-BLIND pipeline that never
    references parser coverage, supported attributes, model predictions, or criterion
    compatibility. Selection order is: high-recall NSCLC screen -> therapeutic-trial
    screen -> complete-criteria screen -> mechanism classification -> family dedup ->
    fixed-seed stratified sampling -> clinical-relevance review. Field coverage is
    computed ONLY AFTER this set is frozen, so it characterises the sample without
    influencing its composition.

The field_checklist is a NON-AUTHORITATIVE navigation aid. Annotators judge eligibility
against the full verbatim inclusion/exclusion criteria, never against the checklist.

Usage:
    python extract_trials_v2.py --corpus corpus.jsonl --out-dir ./dataset_trials
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# DEVELOPMENT set — the original 22 (parser-coverage-aware; NOT for headline eval)
# ---------------------------------------------------------------------------
DEV_TRIALS = {
    "NCT02718066": "Immunotherapy", "NCT03110978": "Immunotherapy",
    "NCT03468985": "Immunotherapy", "NCT04023617": "Immunotherapy",
    "NCT00826449": "Targeted-TKI", "NCT00410059": "Targeted-TKI",
    "NCT00411632": "Targeted-TKI", "NCT03058094": "Targeted-TKI",
    "NCT01248247": "Targeted-TKI", "NCT01416961": "Chemoradiation",
    "NCT01753414": "Chemoradiation", "NCT01507428": "Chemoradiation",
    "NCT00745732": "Chemoradiation", "NCT00215930": "Chemotherapy",
    "NCT01948141": "Chemotherapy", "NCT00203931": "Chemotherapy",
    "NCT00558636": "Chemotherapy", "NCT00378573": "Anti-angiogenic",
    "NCT00250978": "Anti-angiogenic", "NCT00614822": "Anti-angiogenic",
    "NCT00409968": "Other/Novel-agent", "NCT00410189": "Other/Novel-agent",
}

# ---------------------------------------------------------------------------
# HELD-OUT TEST set — framework-blind selected + clinically reviewed (18)
# Frozen here so the selection is reproducible and auditable.
# ---------------------------------------------------------------------------
TEST_TRIALS = {
    "NCT02182102": "Anti-angiogenic", "NCT02182232": "Anti-angiogenic",
    "NCT02073968": "Chemoradiation", "NCT03431415": "Chemoradiation",
    "NCT00465907": "Chemotherapy", "NCT00753714": "Chemotherapy",
    "NCT03057340": "Immunotherapy", "NCT03141359": "Immunotherapy",
    "NCT00266877": "Other/Novel-agent", "NCT01766739": "Other/Novel-agent",
    "NCT03360929": "Other/Novel-agent", "NCT00049543": "Targeted-TKI",
    "NCT00550173": "Targeted-TKI", "NCT01047059": "Targeted-TKI",
    "NCT01342965": "Targeted-TKI", "NCT01639508": "Targeted-TKI",
    "NCT02109016": "Targeted-TKI", "NCT04808752": "Targeted-TKI",
}

# ---------------------------------------------------------------------------
# CORRECTED field-detection patterns. Each is scoped to reduce false positives.
# Purpose: characterise which eligibility dimensions a trial exercises. Aid only.
# ---------------------------------------------------------------------------
FIELD_PATTERNS = {
    # stage: require roman-numeral stage token
    "stage": r"\bstage\s*(?:group\s*)?(?:[0iv]+[ab]?)\b",
    # age cutoff: require an explicit age-bound context, not any "<n> years"
    # matches ">= 18 years", "age 18 or older", "aged 18-75", "18 years or older",
    # "minimum age 18", but NOT "within 5 years" / "grade 3" / "3 weeks"
    "age_cutoff": (
        r"(?:aged?\s+|age\s+(?:of\s+)?|minimum\s+age\s+|maximum\s+age\s+)\d{1,3}"
        r"|\b\d{2}\s*years?\s*(?:or\s+(?:older|younger)|of\s+age\s+or)"
        r"|[\u2265\u2264><]=?\s*\d{2}\s*years"
    ),
    "ecog_kps": r"\becog\b|\bzubrod\b|\bkarnofsky\b|\bkps\b|performance\s+status",
    "fev1": r"\bfev\s*1\b|\bfev1\b",
    # prior therapy: require "prior/previous" within a few words of the therapy noun
    "prior_chemo": r"(?:prior|previous|preceding)\s+\w{0,15}?chemo",
    "prior_radio": r"(?:prior|previous|preceding)\s+\w{0,15}?(?:radio|radiation)",
    "egfr_alk_biomarker": r"\begfr\b|\balk\b|\bt790m\b|\bros1\b|\bkras\b|\bret\b\s+fusion|sensitizing mutation",
    # cardiovascular exclusion: scope to exclusion-relevant cardiac events
    "cardiovascular_excl": r"myocardial\s+infarction|unstable\s+angina|congestive\s+heart|serious\s+cardiac|significant\s+cardiovascular|arrhythmia",
    "neuropathy_excl": r"neuropathy",
    "cns_brain_mets": r"brain\s+metasta|cns\s+metasta|leptomeningeal|cerebral\s+metasta",
    # labs: require an explicit threshold or ULN reference nearby, not bare mention
    "renal_hepatic_labs": r"creatinine\s*(?:clearance)?\s*[\u2265\u2264><=]|bilirubin\s*[\u2265\u2264><=]|\bALT\b\s*[\u2265\u2264><=]|\bAST\b\s*[\u2265\u2264><=]|[\u00d7x]\s*uln|times\s+(?:the\s+)?upper\s+limit",
    "pregnancy": r"pregnan|breast\s*feed|lactat|adequate\s+contracept|childbearing",
}


def detect_fields(inclusion: str, exclusion: str) -> dict:
    text = f"{inclusion}\n{exclusion}".lower()
    return {field: bool(re.search(pat, text, re.IGNORECASE)) for field, pat in FIELD_PATTERNS.items()}


def load_corpus(path: Path) -> dict:
    trials = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            trials[rec["_id"]] = rec
    return trials


def build_records(corpus: dict, trial_map: dict, split_name: str) -> list:
    missing = [tid for tid in trial_map if tid not in corpus]
    if missing:
        print(f"WARNING [{split_name}]: {len(missing)} trial IDs not in corpus: {missing}",
              file=sys.stderr)
    records = []
    for tid, mechanism in trial_map.items():
        if tid not in corpus:
            continue
        src = corpus[tid]
        inclusion = src.get("inclusion_criteria", "") or ""
        exclusion = src.get("exclusion_criteria", "") or ""
        records.append({
            "trial_id": tid,
            "split": split_name,
            "mechanism_class": mechanism,
            "title": src.get("title", ""),
            "phase": src.get("phase", ""),
            "brief_summary": src.get("brief_summary", ""),
            "drugs_list": src.get("drugs_list", []),
            "diseases_list": src.get("diseases_list", []),
            "enrollment": src.get("enrollment", ""),
            "inclusion_criteria": inclusion,
            "exclusion_criteria": exclusion,
            "full_text": src.get("full_text", ""),
            # NON-AUTHORITATIVE aid, computed AFTER selection
            "field_checklist": detect_fields(inclusion, exclusion),
        })
    records.sort(key=lambda r: (r["mechanism_class"], r["trial_id"]))
    return records


def write_jsonl(records: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_markdown(records: list, path: Path, title: str, note: str) -> None:
    lines = [f"# {title}", f"\n{note}\n",
             f"\n**{len(records)} trials**, stratified by mechanism class.\n",
             "\n> The field checklist below is a NON-AUTHORITATIVE navigation aid. "
             "Judge eligibility against the full verbatim criteria, never the checklist.\n"]
    current = None
    for r in records:
        if r["mechanism_class"] != current:
            current = r["mechanism_class"]
            lines.append(f"\n---\n## {current}\n")
        lines.append(f"\n### {r['trial_id']} — {r['title']}")
        lines.append(f"**Phase:** {r['phase'] or 'unspecified'}  |  "
                     f"**Enrollment:** {r['enrollment'] or 'n/a'}  |  "
                     f"**Drugs:** {', '.join(r['drugs_list']) or 'n/a'}")
        lines.append(f"\n**Brief summary:** {r['brief_summary']}")
        present = [k for k, v in r["field_checklist"].items() if v]
        lines.append(f"\n**Dimensions this trial appears to test (aid only):** "
                     f"{', '.join(present) if present else 'none detected'}")
        lines.append(f"\n**Inclusion criteria (authoritative):**\n```\n{r['inclusion_criteria'].strip()}\n```")
        lines.append(f"\n**Exclusion criteria (authoritative):**\n```\n{r['exclusion_criteria'].strip()}\n```")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=Path("corpus.jsonl"))
    ap.add_argument("--out-dir", type=Path, default=Path("dataset_trials"))
    args = ap.parse_args()

    corpus = load_corpus(args.corpus)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    dev = build_records(corpus, DEV_TRIALS, "development")
    test = build_records(corpus, TEST_TRIALS, "test")

    write_jsonl(dev, args.out_dir / "trials_development.jsonl")
    write_jsonl(test, args.out_dir / "trials_test.jsonl")
    write_markdown(dev, args.out_dir / "trials_development_reference.md",
                   "Development Trial Set (framework-tuning; not for headline eval)",
                   "These 22 trials informed framework engineering and were selected "
                   "with awareness of parser coverage. Use for development and ablations, "
                   "NOT for reported generalisation numbers.")
    write_markdown(test, args.out_dir / "trials_test_reference.md",
                   "Held-Out Test Trial Set (framework-blind; headline eval)",
                   "These 18 trials were selected by a pipeline that never referenced "
                   "parser coverage or model behaviour. Headline evaluation numbers come "
                   "from this set. Field coverage was computed only after freezing.")

    # summary
    for name, recs in [("development", dev), ("test", test)]:
        by_m = defaultdict(int)
        for r in recs:
            by_m[r["mechanism_class"]] += 1
        print(f"\n{name}: {len(recs)} trials — {dict(by_m)}")
    print(f"\nWrote 4 files to {args.out_dir}/")


if __name__ == "__main__":
    main()
