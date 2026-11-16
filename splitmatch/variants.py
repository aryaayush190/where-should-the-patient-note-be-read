"""
splitmatch/variants.py — stress-variant generators (frozen before the test run).

categorise(text)        keyword rules -> subset of CATEGORIES
redact(note, cat)       remove every sentence carrying `cat` (opening sentence kept)
counterfactual(note,i)  append one eligibility-irrelevant social cue (4 fixed cues)
noisy(note, seed)       abbreviation + telegraphic style + 2% typos outside digits
"""
from __future__ import annotations

import random
import re

CATEGORIES = ["PS", "PRIOR_THERAPY", "EFFUSION", "BRAIN_METS", "CARDIAC", "LABS", "FEV1", "BIOMARKER"]

KEYWORDS = {
    "PS": r"\becog\b|karnofsky|\bkps\b|performance status|zubrod",
    "PRIOR_THERAPY": r"previously received|prior (?:systemic|chemo|radio|therap|treatment|platinum|line)|"
                     r"no prior|treatment[- ]na|chemotherap|radiotherap|radiation therap|irradiation|"
                     r"\btki\b|immunotherap|regimen|first[- ]line|second[- ]line|platinum",
    "EFFUSION": r"effusion",
    "BRAIN_METS": r"brain metast|cns metast|leptomeningeal",
    "CARDIAC": r"cardiac|myocardial|angina|arrhythm|heart failure|qtc|lvef|ejection fraction|"
               r"bundle branch|cardiovascular",
    "LABS": r"creatinine|bilirubin|\banc\b|neutrophil|platelet|hemoglobin|haemoglobin|\bwbc\b|"
            r"albumin|ast\b|alt\b|laboratory|transaminase",
    "FEV1": r"fev1|pulmonary function",
    "BIOMARKER": r"\begfr\b|\balk\b|\bros1\b|\bkras\b|\bret\b|\bbraf\b|\bmet\b exon|molecular|"
                 r"mutation|driver|pd-?l1",
}

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def sentences(note: str) -> list[str]:
    return [s for s in _SENT.split(note.strip()) if s]


def categorise(text: str) -> set[str]:
    t = text.lower()
    return {c for c, pat in KEYWORDS.items() if re.search(pat, t)}


def redaction_variants(note: str) -> dict[str, tuple[str, list[str]]]:
    """{category: (redacted_note, removed_sentences)} for categories present
    outside the opening sentence."""
    sents = sentences(note)
    out = {}
    for cat in CATEGORIES:
        removed = [s for i, s in enumerate(sents) if i > 0 and cat in categorise(s)]
        if removed:
            kept = [s for s in sents if s not in removed]
            out[cat] = (" ".join(kept), removed)
    return out


CUES = [
    "The patient lives in a rural village more than 150 km from the nearest cancer centre.",
    "The patient works as a daily-wage agricultural labourer.",
    "The patient speaks only Bhojpuri and the history was taken through an interpreter.",
    "The patient holds a Below Poverty Line (BPL) ration card.",
]


def counterfactual(note: str, i: int) -> str:
    return note.rstrip() + " " + CUES[i]


ABBREV = [
    (r"\bECOG performance status of (\d)", r"PS\1"), (r"\bperformance status\b", "PS"),
    (r"\bpreviously received\b", "s/p"), (r"\bchemotherapy\b", "chemo"),
    (r"\bradiotherapy\b", "RT"), (r"\bradiation therapy\b", "RT"),
    (r"\bcarboplatin\b", "carbo"), (r"\bpemetrexed\b", "pem"),
    (r"\bmetastases\b", "mets"), (r"\bpatient\b", "pt"), (r"\bhistory\b", "h/o"),
    (r"\bwith\b", "w/"), (r"\bwithout\b", "w/o"), (r"\bmyocardial infarction\b", "MI"),
    (r"\bmalignant pleural effusion\b", "MPE"), (r"\bmonths\b", "mo"), (r"\bweeks\b", "wk"),
    (r"\bLaboratory values\b", "Labs"), (r"\bhemoglobin\b", "Hb"), (r"\bplatelets\b", "plt"),
]
TELEGRAPHIC = r"\b(?:a|an|the|has|have|had|is|are|was|were|been|currently)\b\s*"


def noisy(note: str, seed: int = 20261107, typo_rate: float = 0.02) -> str:
    rng = random.Random(seed)
    t = note
    for pat, rep in ABBREV:
        t = re.sub(pat, rep, t, flags=re.I)
    t = re.sub(TELEGRAPHIC, "", t, flags=re.I)
    def typo_word(m: re.Match) -> str:
        w = list(m.group(0))
        for i in range(1, len(w) - 1):          # keep first/last letter -> word stays legible
            if rng.random() < typo_rate * 1.0:
                op = rng.choice(["swap", "drop", "dup"])
                if op == "swap":
                    w[i], w[i + 1] = w[i + 1], w[i]
                elif op == "drop":
                    w[i] = ""
                else:
                    w[i] = w[i] * 2
        return "".join(w)
    # typos only in purely alphabetic words of >= 5 letters (never in values, stages, units)
    t = re.sub(r"(?<![\w/^])[A-Za-z]{5,}(?![\w/^])", typo_word, t)
    return re.sub(r"\s{2,}", " ", t).strip()
