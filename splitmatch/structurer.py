"""
splitmatch/structurer.py — EDGE tier. Turns a private note into a FactSheet.

Reader 1: small language model (EDGE_LOCAL in deploy runs; EDGE_PROXY in dev).
Reader 2: deterministic regex reader.
A field is VERIFIED iff (a) the SLM's evidence quote is found verbatim (modulo
whitespace/punctuation) in the note, and (b) the regex reader independently
produced an equal value. Everything else is kept but unverified.
"""
from __future__ import annotations

import math
import re

from . import llm, regex_reader
from .llm import Channel
from .schema import (FIELDS, THERAPY_CLASSES, Fact, FactSheet, Kind, Status, TherapyEvent)

PROMPT_VERSION = "structurer-v1.1"  # prompt unchanged; merge adds relevance check
INF = math.inf


def _field_lines() -> str:
    out = []
    for n, s in FIELDS.items():
        if n in ("tnm_t", "tnm_n", "tnm_m", "egfr_detail"):
            continue
        d = n
        if s.kind is Kind.ENUM and s.values:
            d += " (" + "|".join(s.values) + ")"
        elif s.kind is Kind.NUM:
            d += f" (number{', ' + s.unit if s.unit else ''})"
        elif s.kind is Kind.BOOL:
            d += " (true|false)"
        out.append(d)
    return "; ".join(out)


SYSTEM = f"""You read ONE oncology patient note and extract facts as JSON. Copy evidence verbatim.
Fields (name (allowed values)): {_field_lines()}; tnm (e.g. "T3N2M1b").
Return JSON:
{{"facts": {{"<field>": {{"v": <value>, "q": "<short verbatim quote>"}}}},
  "therapy_history": "described" | "none" | "not_mentioned",
  "therapies": [{{"cls": one of {THERAPY_CLASSES} (use "systemic" when the kind of systemic therapy is not stated), "agents": [..], "line": int|null, "setting": str|null, "thoracic": bool|null, "months_ago": [lo, hi]|null, "ongoing": bool|null, "evidence": "<quote>"}}],
  "prior_lines": int|null}}
Rules:
- Include ONLY fields the note states. Explicit absence ("no brain metastases", "free of infection") -> false / "none" with the quote.
- Numbers: plain numbers; ranges/bounds as [lo, hi] (use null for open ends, e.g. life expectancy >12 weeks -> [2.76, null] months).
- months_ago = time since the LAST dose, in months (weeks/4.345, days/30.44). "1-3 months ago" -> [1,3]; "within 1 month" -> [0,1]; "over 6 months ago" -> [6,null]. A timing stated once for several listed therapies applies to each of them.
- KPS stays in kps; ECOG/Zubrod in ecog. Do not convert.
- Labs in units: creatinine/bilirubin mg/dL; hemoglobin/albumin g/dL; ANC/WBC/platelets in 10^3/uL (245k -> 245).
- Biomarkers: "positive" if a driver alteration is reported, "negative" if tested negative or "no actionable mutation", "not_tested" if not performed.
- "v" for an enum field is the allowed STRING itself (e.g. "male", "adenocarcinoma", "progressed_after_prior"), never an index. stage_group is a roman stage string like "IIIB".
- therapy_history = "described" whenever ANY prior treatment is mentioned; "none" only if the note says there was no prior treatment.
- "q": at most 15 words copied exactly from the note.
Example (invented note: "A 70-year-old woman with stage IV squamous NSCLC, ECOG 2, progressed after two lines of carboplatin-based chemotherapy, last dose 5 weeks ago; no brain metastases."):
{{"facts": {{"age": {{"v": 70, "q": "70-year-old woman"}}, "sex": {{"v": "female", "q": "woman"}}, "stage_group": {{"v": "IV", "q": "stage IV squamous NSCLC"}}, "histology": {{"v": "squamous", "q": "squamous NSCLC"}}, "cancer_type": {{"v": "nsclc", "q": "squamous NSCLC"}}, "ecog": {{"v": 2, "q": "ECOG 2"}}, "disease_status": {{"v": "progressed_after_prior", "q": "progressed after two lines"}}, "brain_mets": {{"v": "none", "q": "no brain metastases"}}}},
 "therapy_history": "described", "therapies": [{{"cls": "chemo", "agents": ["carboplatin"], "line": null, "setting": "advanced", "thoracic": null, "months_ago": [1.15, 1.15], "ongoing": false, "evidence": "two lines of carboplatin-based chemotherapy, last dose 5 weeks ago"}}], "prior_lines": 2}}
JSON only."""


def slm_read(note: str, channel: Channel, local_ref: str = "", run_id: str = "") -> tuple[dict, dict]:
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": note}]
    extra = {"json": True} if channel is Channel.EDGE_LOCAL else \
        {"response_format": {"type": "json_object"}, "reasoning_effort": "medium"}
    rep = llm.call(channel, msgs, max_tokens=6000, extra=extra, run_id=run_id,
                   tag="structure", local_ref=local_ref)
    return llm.parse_json(rep.text), {"cached": rep.cached, **rep.meta}


# ── value normalisation and comparison ──────────────────────────────────────
def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def grounded(evidence: str | None, note: str) -> bool:
    return bool(evidence) and len(_alnum(evidence)) >= 3 and _alnum(evidence) in _alnum(note)


def _norm_value(name: str, v):
    spec = FIELDS[name]
    if spec.kind is Kind.NUM:
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)):
            return [float(v), float(v)]
        if isinstance(v, str):
            m = re.findall(r"\d+(?:\.\d+)?", v)
            return [float(m[0]), float(m[0])] if m else None
        if isinstance(v, (list, tuple)) and len(v) == 2:
            lo = -INF if v[0] is None else float(v[0])
            hi = INF if v[1] is None else float(v[1])
            return [lo, hi]
        return None
    if spec.kind is Kind.BOOL:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "yes", "present", "positive")
        return bool(v) if v is not None else None
    if spec.kind is Kind.ENUM:
        s = str(v).strip().lower().replace(" ", "_").replace("-", "_")
        alias = {"squamous_cell_carcinoma": "squamous", "squamous_cell": "squamous",
                 "nsclc_nos": "nos", "not_otherwise_specified": "nos", "large_cell_carcinoma": "large_cell",
                 "non_small_cell_lung_cancer": "nsclc", "treated/stable": "treated_stable",
                 "false": "none", "absent": "none", "no": "none"}
        s = alias.get(s, s)
        if spec.values and s not in spec.values and name not in ("stage_group",):
            return None
        if name == "stage_group":
            s = str(v).upper().replace("STAGE", "").strip()
        return s
    if name in ("tnm_t", "tnm_n", "tnm_m"):
        return str(v).strip().upper()
    return str(v)


def _equal(name: str, a, b) -> bool:
    if a is None or b is None:
        return False
    if FIELDS[name].kind is Kind.NUM:
        return all(abs(x - y) <= max(0.051 * max(abs(x), abs(y)), 0.051) if math.isfinite(x) and math.isfinite(y)
                   else x == y for x, y in zip(a, b))
    return a == b


def _negated(name: str, v) -> bool:
    spec = FIELDS[name]
    return (spec.kind is Kind.BOOL and v is False) or (spec.kind is Kind.ENUM and v == "none")


# A fact's quote must be ABOUT the field (not merely present in the note): found on the
# local-model dev check, where one true quote ("no prior systemic therapy") was reused to
# negate unrelated fields. Fields without an entry are not relevance-checked.
RELEVANCE = {
    "malignant_effusion": r"effusion",
    "brain_mets": r"brain|cns|intracranial|cerebral|leptomening",
    "active_infection": r"infect|sepsis|pneumonia",
    "autoimmune_active": r"autoimmun|lupus|rheumat|crohn|colitis|psoria",
    "steroids_systemic": r"steroid|cortico|prednis|dexameth",
    "pregnant": r"pregnan|menopaus|childbearing|breast.?feed|lactat",
    "mi_history": r"myocard|infarct|mi|heart attack|cardiac|cardiovascular|coronary",
    "mi_months_ago": r"myocard|infarct|mi|heart attack",
    "unstable_angina": r"angina|cardiac|cardiovascular|coronary",
    "chf": r"heart failure|chf|cardiac|cardiovascular|ejection|lvef|nyha",
    "arrhythmia": r"arrhythm|fibrillation|cardiac|cardiovascular|qtc|rhythm",
    "qtc_ms": r"qtc|qt ",
    "neuropathy_grade": r"neuropath",
    "measurable_disease": r"measur|lesion|recist|evaluable",
    "malignant": r"",
    **{g: r"molecular|mutation|alteration|rearrang|fusion|driver|tested|testing|genomic|biomarker|"
          + g for g in ("egfr", "alk", "ros1", "kras", "ret", "braf", "met")},
    "pdl1_tps": r"pd-?l1|tps|tumou?r proportion",
    "fev1_pct": r"fev1|pulmonary function",
    "fev1_l": r"fev1|pulmonary function",
    "life_expectancy_months": r"life expectancy|prognosis|survival",
    "ecog": r"ecog|zubrod|performance|ps|who",
    "kps": r"karnofsky|kps|performance",
}


def relevant_quote(name: str, evidence) -> bool:
    pat = RELEVANCE.get(name)
    if not pat:
        return True
    return bool(evidence) and bool(re.search(pat, str(evidence), re.I))

# ── merge ───────────────────────────────────────────────────────────────────
def _unpack(item):
    """Accept {"v","q"} objects (current prompt) and [value, quote] pairs."""
    if isinstance(item, dict):
        return item.get("v", item.get("value")), item.get("q", item.get("evidence"))
    if isinstance(item, list) and len(item) in (1, 2) and not (
            len(item) == 2 and all(isinstance(x, (int, float)) or x is None for x in item)):
        return item[0], (item[1] if len(item) > 1 else None)
    return item, None


def build_factsheet(patient_id: str, note: str, slm: dict, rx: dict, reader: str) -> FactSheet:
    facts = slm.get("facts", {}) or {}
    fields: dict[str, Fact] = {}
    conflicts = []
    # TNM convenience
    tnm = facts.pop("tnm", None)
    if tnm:
        tv, tq = _unpack(tnm)
        m = re.match(r"\s*(T[0-4][a-c]?)(N[0-3][a-c]?)(M[01][a-c]?)", str(tv), re.I)
        if m:
            for k, g in (("tnm_t", 1), ("tnm_n", 2), ("tnm_m", 3)):
                facts[k] = {"v": m.group(g).upper(), "q": tq}
    for name, item in facts.items():
        if name not in FIELDS:
            continue
        val, ev = _unpack(item)
        v = _norm_value(name, val)
        if v is None:
            continue                       # "no mention" / unparseable -> treat as not mentioned
        if name == "stage_group" and not re.fullmatch(r"(I{1,3}|IV)[ABC]?\d?", str(v)):
            continue
        if _negated(name, v) and not grounded(ev, note):
            continue                       # an absence must be QUOTED from the note, never invented
        if not relevant_quote(name, ev):
            continue                       # the quote must be about this field
        rv = rx["fields"].get(name)
        rv = _norm_value(name, rv) if rv is not None else None
        agree = _equal(name, v, rv)
        if rv is not None and not agree:
            conflicts.append(name)
        status = Status.NEGATED if _negated(name, v) else Status.VALUE
        fields[name] = Fact(status=status, value=None if status is Status.NEGATED and
                            FIELDS[name].kind is Kind.BOOL else v,
                            evidence=ev, readers=[reader] + (["regex"] if agree else []),
                            verified=bool(agree and grounded(ev, note)))
    for name, rv in rx["fields"].items():            # regex-only facts: kept, unverified
        if name not in fields and name in FIELDS:
            v = _norm_value(name, rv)
            if v is None:
                continue
            st = Status.NEGATED if _negated(name, v) else Status.VALUE
            fields[name] = Fact(status=st, value=None if st is Status.NEGATED and
                                FIELDS[name].kind is Kind.BOOL else v, readers=["regex"], verified=False)

    # therapies
    rx_ev = rx["events"]
    events = []
    for e in slm.get("therapies", []) or []:
        try:
            cls = str(e.get("cls", "other")).lower()
            cls = cls if cls in THERAPY_CLASSES else "other"
            mo = e.get("months_ago")
            if isinstance(mo, (int, float)):
                mo = [mo, mo]
            mo = None if not (isinstance(mo, list) and len(mo) == 2) else \
                [0.0 if mo[0] is None else float(mo[0]), INF if mo[1] is None else float(mo[1])]
            match = any(r["cls"] == cls and (r["months_ago"] == mo or (r["months_ago"] and mo and
                        _equal("mi_months_ago", r["months_ago"], mo))) for r in rx_ev)
            ev = e.get("evidence")
            events.append(TherapyEvent(cls=cls, agents=[str(a).lower() for a in e.get("agents") or []],
                                       line=e.get("line") if isinstance(e.get("line"), int) else None,
                                       setting=e.get("setting"), thoracic=e.get("thoracic"),
                                       months_ago=mo, ongoing=e.get("ongoing"), evidence=ev,
                                       verified=bool(match and grounded(ev, note))))
        except Exception:
            continue
    hist = str(slm.get("therapy_history", "not_mentioned")).lower()
    if not events and rx_ev:          # SLM missed therapies the regex reader saw: keep, unverified
        events = [TherapyEvent(cls=r["cls"], months_ago=r["months_ago"], verified=False) for r in rx_ev]
    if events:
        therapy_status = Status.VALUE
    elif hist == "none" or rx["therapy_negated"]:
        therapy_status = Status.NEGATED
    else:
        therapy_status = Status.NOT_MENTIONED
    therapy_verified = (hist == "none") == rx["therapy_negated"] if not events else \
        all(ev.verified for ev in events)
    pl = slm.get("prior_lines")
    return FactSheet(patient_id=patient_id, fields=fields, therapy_status=therapy_status,
                     events=events,
                     lines_of_therapy=[float(pl), float(pl)] if isinstance(pl, int) else None,
                     reader_meta={"reader": reader, "conflicts": conflicts,
                                  "therapy_verified": bool(therapy_verified),
                                  "lines_verified": False, "prompt_version": PROMPT_VERSION})


def structure(patient_id: str, note: str, channel: Channel, run_id: str = "") -> FactSheet:
    rx = regex_reader.read(note)
    try:
        slm, meta = slm_read(note, channel, local_ref=patient_id, run_id=run_id)
    except Exception as e:                       # reader failure -> regex-only, all unverified
        slm, meta = {"facts": {}, "therapies": []}, {"error": str(e)[:200]}
    fs = build_factsheet(patient_id, note, slm, rx, reader=channel.value)
    fs.reader_meta["slm_meta"] = meta
    return fs
