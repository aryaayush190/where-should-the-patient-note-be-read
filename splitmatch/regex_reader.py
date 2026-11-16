"""
splitmatch/regex_reader.py — deterministic SECOND READER (edge, no model).

Written from general clinical phrasing and checked on development notes only.
It is deliberately conservative: it extracts a field only when the phrasing is
unambiguous, and returns nothing otherwise. Its role is not to be complete but
to independently confirm (verify) values the SLM reader extracts.
"""
from __future__ import annotations

import math
import re

INF = math.inf
NUM = r"(\d+(?:\.\d+)?)"


def _iv(x: float) -> list[float]:
    return [float(x), float(x)]


_LT = re.compile(r"(<|≤|=<|less than|below|under|lower than|not exceeding|up to)\s*=?\s*$")
_GT = re.compile(r"(>|≥|=>|greater than|above|over|more than|exceeding|at least)\s*=?\s*$")


def _bounded(t: str, m: re.Match, g: int = 1) -> list[float]:
    """Value of group g, as an interval if a comparator precedes it ("<480 ms" -> [-inf, 480])."""
    v = float(m.group(g))
    before = t[max(0, m.start(g) - 16):m.start(g)]
    if _LT.search(before):
        return [-INF, v]
    if _GT.search(before):
        return [v, INF]
    return [v, v]


def timing_interval(text: str) -> list[float] | None:
    """Map a time phrase to an interval in months (since last dose)."""
    t = text.lower()
    unit = lambda u: 1.0 if u.startswith("month") else (1 / 4.345 if u.startswith("week") else  # noqa: E731
                                                        (1 / 30.44 if u.startswith("day") else 12.0))
    m = re.search(rf"within (?:the )?(?:past |last )?{NUM}\s*(day|week|month|year)s?", t)
    if m:
        return [0.0, float(m.group(1)) * unit(m.group(2))]
    m = re.search(rf"{NUM}\s*(?:-|–|to)\s*{NUM}\s*(day|week|month|year)s?\s*(?:ago|prior|before|earlier)", t)
    if m:
        u = unit(m.group(3))
        return [float(m.group(1)) * u, float(m.group(2)) * u]
    m = re.search(rf"(?:over|more than|>|greater than|at least)\s*{NUM}\s*(day|week|month|year)s?\s*(?:ago|prior|before|earlier)?", t)
    if m:
        return [float(m.group(1)) * unit(m.group(2)), INF]
    m = re.search(rf"(?:less than|under|<)\s*{NUM}\s*(day|week|month|year)s?\s*(?:ago|prior|before)", t)
    if m:
        return [0.0, float(m.group(1)) * unit(m.group(2))]
    m = re.search(rf"{NUM}\s*(day|week|month|year)s?\s*(?:ago|prior|before|earlier)", t)
    if m:
        v = float(m.group(1)) * unit(m.group(2))
        return [v, v]
    return None


ROMAN_STAGE = r"(?:stage\s*)(I{1,3}V?|IV)([ABC]?)(\d?)"
LABS = {
    "creatinine_mg_dl": rf"creatinine(?: of| level of)?\s*{NUM}\s*mg/?dl",
    "bilirubin_mg_dl": rf"bilirubin(?: of)?\s*{NUM}\s*mg/?dl",
    "hemoglobin_g_dl": rf"(?:hemoglobin|haemoglobin|hgb|hb)(?: of)?\s*{NUM}\s*g/?dl",
    "albumin_g_dl": rf"albumin(?: of)?\s*{NUM}\s*g/?dl",
    "anc_k_ul": rf"(?:anc|absolute neutrophil count|absolute granulocytes(?: \(anc\))?)(?: of)?\s*{NUM}\s*(?:x\s*10\^?3|x10³|×\s*10\^?3)",
    "wbc_k_ul": rf"(?:wbc|white blood (?:cell )?count)(?: of)?\s*{NUM}\s*(?:x\s*10\^?3|x10³|×\s*10\^?3)",
    "platelets_k_ul": rf"platelets?(?: count)?(?: of)?\s*{NUM}\s*k",
    "crcl_ml_min": rf"creatinine clearance(?: of)?\s*(?:>|≥|greater than|above)?\s*{NUM}\s*(?:ml|cc)",
}


def read(note: str) -> dict:
    """Return {"fields": {name: value}, "events": [...], "therapy_negated": bool}."""
    t = note.lower()
    f: dict = {}

    m = re.search(r"\b(\d{2})[- ]year[- ]old\b", t)
    if m:
        f["age"] = _iv(int(m.group(1)))
    if re.search(r"\b(female|woman|she|her|ms\.)\b", t):
        f["sex"] = "female"
    elif re.search(r"\b(male|man|he|his|mr\.)\b", t):
        f["sex"] = "male"

    if "squamous" in t and "non-squamous" not in t and "nonsquamous" not in t and "skin" not in t:
        f["histology"] = "squamous"
    elif "adenocarcinoma" in t:
        f["histology"] = "adenocarcinoma"
    elif "large cell" in t or "large-cell" in t:
        f["histology"] = "large_cell"
    elif re.search(r"\bnos\b|not otherwise specified", t):
        f["histology"] = "nos"

    if re.search(r"non[- ]small[- ]cell|nsclc", t):
        f["cancer_type"] = "nsclc"
    elif "melanoma" in t:
        f["cancer_type"] = "melanoma"
    elif "renal cell" in t:
        f["cancer_type"] = "renal_cell"

    m = re.search(ROMAN_STAGE, note, re.I)
    if m:
        f["stage_group"] = (m.group(1) + m.group(2) + m.group(3)).upper()
    m = re.search(r"\b(T[0-4][a-c]?)(N[0-3][a-c]?)(M[01][a-c]?)\b", note)
    if m:
        f["tnm_t"], f["tnm_n"], f["tnm_m"] = m.group(1).upper(), m.group(2).upper(), m.group(3).upper()

    m = re.search(r"(?:ecog|zubrod|who)(?: performance status| ps)?(?: score)?(?: of| is|:)?\s*([0-4])\b", t)
    if m:
        f["ecog"] = _iv(int(m.group(1)))
    m = re.search(r"(?:karnofsky|kps)(?: performance status| performance score)?(?: of| is|:)?\s*(\d{2,3})", t)
    if m:
        f["kps"] = _iv(int(m.group(1)))
    m = re.search(rf"fev1(?: of)?\s*(?:[<>≤≥]=?\s*)?{NUM}\s*%", t)
    if m:
        f["fev1_pct"] = _bounded(t, m)

    if re.search(r"measurable disease|measurable (?:target )?lesions?|measurable per recist", t):
        f["measurable_disease"] = not re.search(r"no measurable|non-?measurable", t)
    if re.search(r"newly diagnosed|treatment[- ]na[iï�]?ve", t):
        f["disease_status"] = "newly_diagnosed"
    elif re.search(r"progress\w* (?:following|after|on)", t):
        f["disease_status"] = "progressed_after_prior"
    elif "recurrent" in t:
        f["disease_status"] = "recurrent"
    elif re.search(r"stable on (?:ongoing|current)", t):
        f["disease_status"] = "stable_on_therapy"

    gene_pos = {"egfr": r"egfr\s*(?:exon\s*19|l858r|exon\s*21|t790m|mutation|sensitizing)",
                "alk": r"alk\s*(?:rearrange|fusion|positive|translocation)",
                "ros1": r"ros1\s*(?:fusion|rearrange|positive)", "kras": r"kras\s*g12",
                "ret": r"ret\s*(?:fusion|rearrange)", "braf": r"braf\s*v600",
                "met": r"met\s*exon\s*14"}
    for g, pat in gene_pos.items():
        if re.search(pat, t) and not re.search(rf"(?:no|negative for|without)\s+(?:\w+\s+){{0,3}}{g}", t):
            f[g] = "positive"
    if re.search(r"no actionable (?:driver )?mutation|no (?:targetable|actionable) alteration", t):
        for g in gene_pos:
            f.setdefault(g, "negative")
    if re.search(r"molecular testing has not been performed|not been tested|testing (?:was )?not performed", t):
        for g in gene_pos:
            f.setdefault(g, "not_tested")

    if re.search(r"untreated(?: symptomatic)? brain metast|symptomatic brain metast|active brain metast", t):
        f["brain_mets"] = "untreated_or_symptomatic"
    elif re.search(r"(?:treated|stable)[^.]{0,40}brain metast|brain metast[^.]{0,60}(?:treated|stable)", t):
        f["brain_mets"] = "treated_stable"
    elif re.search(r"no (?:evidence of )?brain metast|no cns metast", t):
        f["brain_mets"] = "none"

    if re.search(r"malignant (?:pleural|pericardial) effusion", t):
        f["malignant_effusion"] = not re.search(r"no (?:malignant )?(?:pleural|pericardial) effusion", t)

    m = re.search(r"neuropathy[^.]{0,20}grade\s*([0-4])|grade\s*([0-4])[^.]{0,20}neuropathy", t)
    if m:
        f["neuropathy_grade"] = _iv(int(m.group(1) or m.group(2)))
    if re.search(r"myocardial infarction within the past (\d+) months", t):
        n = float(re.search(r"myocardial infarction within the past (\d+) months", t).group(1))
        f["mi_history"], f["mi_months_ago"] = True, [0.0, n]
    elif re.search(r"myocardial infarction more than (\d+) months ago", t):
        n = float(re.search(r"myocardial infarction more than (\d+) months ago", t).group(1))
        f["mi_history"], f["mi_months_ago"] = True, [n, INF]
    if re.search(r"(?:recent|unstable) angina", t):
        f["unstable_angina"] = True
    if re.search(r"controlled (?:cardiac )?arrhythmia", t):
        f["arrhythmia"] = "controlled"
    if re.search(r"(?:currently has|with) an active infection", t):
        f["active_infection"] = True
    elif re.search(r"(?:free of|no) (?:any )?active infection", t):
        f["active_infection"] = False
    if re.search(r"active autoimmune (?:condition|disease)", t):
        f["autoimmune_active"] = not re.search(r"no active autoimmune", t)
    if re.search(r"currently pregnant|is pregnant", t):
        f["pregnant"] = True
    m = re.search(r"life expectancy (?:of )?(?:>|greater than|more than|exceeds|over)\s*(\d+)\s*(week|month)", t)
    if m:
        n = float(m.group(1)) / (4.345 if m.group(2) == "week" else 1)
        f["life_expectancy_months"] = [n, INF]
    m = re.search(r"qtc[^.]{0,20}?(\d{3})\s*ms", t)
    if m:
        f["qtc_ms"] = _bounded(t, m)
    for name, pat in LABS.items():
        m = re.search(pat, t)
        if m:
            f[name] = _bounded(t, m)

    # therapy history
    events, negated = [], False
    if re.search(r"no prior (?:systemic|anticancer|cancer)?\s*(?:or radiation )?(?:therapy|treatment)|"
                 r"has received no prior|treatment[- ]na[iï�]?ve|naive to all prior", t):
        negated = True
    cls_pat = {"chemo": r"chemotherap|platinum|carboplatin|cisplatin|pemetrexed|paclitaxel|docetaxel|gemcitabine|vinorelbine|etoposide",
               "radio": r"radiotherap|radiation therap|irradiation",
               "tki": r"\btki\b|tyrosine kinase|erlotinib|gefitinib|afatinib|osimertinib|crizotinib|alectinib",
               "io": r"immunotherap|pembrolizumab|nivolumab|atezolizumab|durvalumab|checkpoint"}
    prior_ctx = re.findall(r"[^.]*(?:previously received|prior|received|following|after|completed)[^.]*\.", t)
    for sent in prior_ctx:
        if re.search(r"\bno prior|naive|has received no", sent):
            continue
        for c, pat in cls_pat.items():
            if re.search(pat, sent):
                events.append({"cls": c, "months_ago": timing_interval(sent)})
    seen, uniq = set(), []
    for e in events:
        key = (e["cls"], tuple(e["months_ago"]) if e["months_ago"] else None)
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return {"fields": f, "events": uniq, "therapy_negated": negated and not uniq}
