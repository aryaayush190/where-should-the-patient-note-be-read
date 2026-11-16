"""
splitmatch/policy.py — evidence-conditioned authority + action policy.

An exclusion (a failed inclusion or a triggered exclusion) is AUTHORITATIVE only
with two independent keys:
  key 1  deterministic verdict on VERIFIED facts (two readers + grounded quote), or
  key 1' deterministic verdict on unverified facts confirmed by the L1 judge, or
  key 2  L1 judge confirmed by the L2 cloud judge.
A single key never excludes. Satisfied criteria may rest on unverified/assumed
facts (provisional) because at pre-screening a false inclusion is caught at the
trial site while a false exclusion is final (cost asymmetry, PREREGISTRATION §3).

Outputs per pair:
  selective: ELIGIBLE | NOT_ELIGIBLE | NEED_INFO | DEFER
  forced:    ELIGIBLE | NOT_ELIGIBLE
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .evaluator import TV, AtomResult
from .ladder import item_key, l2_judge
from .render import judge_polarity, statement
from .schema import FIELDS, Atom, AtomType


@dataclass
class Config:
    hard_veto: bool = False       # ablation: any decisive negative excludes (no verification)
    use_l1: bool = True           # ablation: −L1
    use_l2: bool = True           # ablation: −L2 (offline-only)
    forced: bool = False          # forced binary mode


@dataclass
class Decision:
    selective: str
    forced: str
    n_l2: int = 0
    n_forced_unknown: int = 0
    n_provisional: int = 0
    asks: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    site_verify: list = field(default_factory=list)


def _neg(pol: str, v: str) -> bool:
    return (pol == "inclusion" and v == "F") or (pol == "exclusion" and v == "T")


def _pos(pol: str, v: str) -> bool:
    return (pol == "inclusion" and v == "T") or (pol == "exclusion" and v == "F")


SITE_FIELDS = {n for n, sp in FIELDS.items() if sp.category == "LABS"} | {"qtc_ms"}
_SITE_TEXT = (r"\binr\b|\bpt\b|\bptt\b|aptt|prothrombin|coagulation|potassium|calcium|magnesium|"
              r"electrolyte|urinalysis|proteinuria|urine protein|\becg\b|\bekg\b|qtc|lvef|ejection fraction|"
              r"echocardiogra|pregnancy test|blood count|hematologic|haematologic|hepatic function|"
              r"renal function|organ function|bone marrow function|laboratory|transaminase|alkaline phosphatase|"
              r"\bast\b|\balt\b|bilirubin|creatinine|neutrophil|platelet|hemoglobin|haemoglobin|albumin|\bwbc\b")


def site_verifiable(atom: Atom) -> bool:
    """Routine screening investigations (labs, coagulation, ECG/echo, pregnancy test) that
    every trial site repeats at screening. Unmentioned -> site checklist, not a question."""
    import re
    fields = [f for f in _fields(atom) if f != "therapy"]
    if fields:
        return all(f in SITE_FIELDS for f in fields)
    return bool(re.search(_SITE_TEXT, (atom.source_line or atom.text or ""), re.I))


_PERMISSIVE = (r"\b(is|are|will be|may be|is also)\s+(allowed|permitted|acceptable|eligible|included|"
               r"accepted)\b|\bpermitted\b|\ballowed\b|\bacceptable\b")


def permissive(atom: Atom) -> bool:
    import re
    return bool(re.search(_PERMISSIVE, atom.source_line or atom.text or "", re.I))


CLINICAL_FIELDS = {"stage_group", "tnm_t", "tnm_n", "tnm_m", "histology", "cancer_type",
                   "malignant_effusion", "egfr", "alk", "ros1", "kras", "ret", "braf", "met",
                   "egfr_detail", "pdl1_tps", "measurable_disease", "disease_status", "ecog", "kps",
                   "brain_mets"}
CLINICAL_CATEGORIES = {"PRIOR_THERAPY", "EFFUSION", "BIOMARKER", "BRAIN_METS", "PS"}


def clinical_requirement(atom: Atom) -> bool:
    """Disease / treatment-history requirements that pre-screening itself must establish
    (asked if missing). Everything else is confirmed at the trial-site screening visit."""
    import re
    from .variants import categorise
    fields = _fields(atom)
    if "therapy" in fields or any(f in CLINICAL_FIELDS for f in fields):
        return True
    if fields:
        return False
    text = atom.source_line or atom.text or ""
    if categorise(text) & CLINICAL_CATEGORIES:
        return True
    return bool(re.search(r"\bstage\b|\b[TNM][0-4]\b|metasta|histolog|cytolog|squamous|adenocarcinoma|"
                          r"measurable|progress|recurren|line of|regimen", text, re.I))


def ask_category(atom: Atom) -> str:
    from .variants import categorise
    for f in _fields(atom):
        if f in FIELDS and FIELDS[f].category:
            return FIELDS[f].category
        if f == "therapy":
            return "PRIOR_THERAPY"
    cats = categorise(atom.text or atom.source_line or "")
    return sorted(cats)[0] if cats else "OTHER"


def _fields(atom: Atom) -> list[str]:
    out = []
    if atom.field:
        out.append(atom.field)
    if atom.type in (AtomType.HAS, AtomType.WITHIN, AtomType.SINCE, AtomType.COUNT):
        out.append("therapy")
    for c in atom.children:
        out += _fields(c)
    return out


def relevant_fields(atom: Atom) -> list[str]:
    """Fact-sheet fields relevant to a criterion: its own fields, plus fields of the
    criterion's clinical category (for JUDGE atoms) and stage/TNM for stage wording."""
    import re
    from .variants import categorise
    out = [f for f in _fields(atom) if f in FIELDS]
    text = (atom.text or atom.source_line or "")
    cats = categorise(text)
    out += [n for n, sp in FIELDS.items() if sp.category and sp.category in cats]
    if re.search(r"\bstage\b|\b[TNM][0-4]\b|metasta|lymph node", text, re.I):
        out += ["stage_group", "tnm_t", "tnm_n", "tnm_m"]
    seen, res = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            res.append(f)
    return res


def record_facts(fs, fields: list[str]) -> str:
    """Structured (never narrative) facts for the cloud judge, with their reliability."""
    if fs is None:
        return ""
    parts = []
    for f in fields:
        fact = fs.get(f)
        if fact.status.value == "not_mentioned":
            continue
        val = "absent" if fact.status.value == "negated" else fact.value
        if isinstance(val, list):
            lo, hi = val
            val = f"{lo:g}" if lo == hi else f"[{lo:g}, {hi:g}]"
        parts.append(f"{f}={val} ({'verified' if fact.verified else 'unverified'})")
    return "; ".join(parts)


def decide(results: list[tuple[Atom, AtomResult]], l1: dict, cfg: Config, local_ref: str,
           run_id: str = "", fs=None) -> Decision:
    neg_keys, asks, defers, trace, site = [], [], [], [], []
    n_l2 = n_forced_unknown = n_prov = 0

    l2_seen: dict[str, str] = {}

    def l2(atom, fact, why, forced=False):
        nonlocal n_l2
        if not cfg.use_l2:
            return {"verdict": "U", "why": "offline"}
        n_l2 += 1
        rel = relevant_fields(atom)
        rec_txt = record_facts(fs, rel)
        full = (fact or "not stated") + (f". Structured record: {rec_txt}" if rec_txt else "")
        res = l2_judge(statement(atom), full, local_ref,
                       disclosed=[f for f in rel if fs is not None and fs.get(f).status.value != "not_mentioned"]
                       + [f"judge:{atom.id}"], run_id=run_id, forced=forced)
        l2_seen[atom.id] = res["verdict"]
        return res

    for atom, r in results:
        pol = atom.polarity
        v = r.value.value
        rec = {"atom": atom.id, "type": atom.type.value, "pol": pol, "det": v,
               "verified": r.verified, "assumed": r.assumed}
        if r.unscreenable:
            site.append(atom.source_line or atom.text)
            rec["route"] = "site_verify"
            trace.append(rec)
            continue
        if judge_polarity(atom) == "inclusion" and permissive(atom):
            # "X is allowed/permitted/acceptable", "... are eligible": never a requirement
            rec["route"] = "permission:not_a_requirement"
            trace.append(rec)
            continue
        decisive_neg = _neg(pol, v)
        if decisive_neg and (r.verified or cfg.hard_veto):
            neg_keys.append(atom.id)
            rec["route"] = "exclude:verified" if r.verified else "exclude:hard_veto"
            trace.append(rec)
            continue
        if _pos(pol, v) and atom.type is not AtomType.JUDGE:
            if not r.verified:
                n_prov += 1
            rec["route"] = "satisfied" + ("" if r.verified else ":provisional")
            trace.append(rec)
            continue

        # residual: U, JUDGE, or an unverified decisive negative.
        # Judge verdicts are read in the judge's polarity (contested atoms are judged
        # on their verbatim criterion line, whose section may differ from atom polarity).
        jp = judge_polarity(atom)
        j = l1.get(item_key(statement(atom))) if cfg.use_l1 else None
        if j is not None and j.get("basis") == "unavailable":
            j = None                                      # local judge failed -> no L1 key
        jv = j["verdict"] if j else "U"
        rec["l1"] = jv
        if decisive_neg:                                   # program says exclude, unverified
            if j and _neg(jp, jv):
                neg_keys.append(atom.id)
                rec["route"] = "exclude:program+l1"
            else:
                res = l2(atom, j["fact"] if j else None, "contested")
                rec["l2"] = res["verdict"]
                if _neg(jp, res["verdict"]):
                    neg_keys.append(atom.id)
                    rec["route"] = "exclude:program+l2"
                elif _pos(jp, res["verdict"]):
                    n_prov += 1
                    rec["route"] = "satisfied:l2"
                else:
                    defers.append(atom.id)
                    rec["route"] = "defer"
            trace.append(rec)
            continue
        if j and _pos(jp, jv):
            n_prov += 1
            rec["route"] = "satisfied:l1"
        elif j and _neg(jp, jv):                           # single key: needs a second
            res = l2(atom, j["fact"], "second-key")
            rec["l2"] = res["verdict"]
            if _neg(jp, res["verdict"]):
                neg_keys.append(atom.id)
                rec["route"] = "exclude:l1+l2"
            else:
                defers.append(atom.id)
                rec["route"] = "defer:l1-l2-disagree"
        elif (not j) or j["basis"] == "not_mentioned":
            if atom.cwa or r.assumed or jp == "exclusion":
                # excluding conditions are documented when present -> presumed absent
                n_prov += 1
                rec["route"] = "satisfied:assumed_absent"
            elif not clinical_requirement(atom):
                # screening-visit items (labs, scans, consent, life-expectancy estimate...)
                site.append(atom.source_line or atom.text)
                n_prov += 1
                rec["route"] = "site_verify:not_mentioned"
            else:
                asks.append({"atom": atom.id, "category": ask_category(atom),
                             "question": atom.question or _default_q(atom),
                             "answerable_by": atom.answerable_by, "pol": jp})
                rec["route"] = "ask"
        else:                                             # stated but ambiguous -> reasoning help
            res = l2(atom, j["fact"], "ambiguous")
            rec["l2"] = res["verdict"]
            if _neg(jp, res["verdict"]):
                defers.append(atom.id)                    # L2 alone is a single key
                rec["route"] = "defer:l2-only-negative"
            elif _pos(jp, res["verdict"]):
                n_prov += 1
                rec["route"] = "satisfied:l2"
            else:
                defers.append(atom.id)
                rec["route"] = "defer"
        trace.append(rec)

    if neg_keys:
        selective = "NOT_ELIGIBLE"
    elif asks:
        selective = "NEED_INFO"
    elif defers:
        selective = "DEFER"
    else:
        selective = "ELIGIBLE"

    # forced mode (PREREGISTRATION §3, as registered + structured record):
    #  - an unmentioned clinical requirement (ASK) is resolved by the cloud judge on
    #    "not stated in the note" plus the relevant STRUCTURED facts; unknown -> not excluding
    #  - DEFER items: the cloud verdict already obtained decides; unknown -> not excluding
    forced = "NOT_ELIGIBLE" if neg_keys else None
    if forced is None:
        n_forced_unknown = len(asks) + len(defers)
        by_id = {a.id: a for a, _ in results}
        for q in asks:
            atom = by_id[q["atom"]]
            res = l2(atom, "this fact is not stated in the patient note", "forced-ask")
            if _neg(judge_polarity(atom), res["verdict"]):
                forced = "NOT_ELIGIBLE"
                trace.append({"atom": q["atom"], "route": "forced:exclude(l2-ask)", "l2": res["verdict"]})
                break
        if forced is None:
            for d in defers:
                v2 = l2_seen.get(d, "U")
                if _neg(judge_polarity(by_id[d]), v2):
                    forced = "NOT_ELIGIBLE"
                    trace.append({"atom": d, "route": "forced:exclude(l2)", "l2": v2})
                    break
        forced = forced or "ELIGIBLE"

    return Decision(selective=selective, forced=forced, n_l2=n_l2,
                    n_forced_unknown=n_forced_unknown, n_provisional=n_prov,
                    asks=asks, trace=trace, site_verify=site)


def _default_q(atom: Atom) -> str:
    for f in _fields(atom):
        if f in FIELDS and FIELDS[f].question:
            return FIELDS[f].question
    return f"Can you confirm: {atom.text or atom.source_line}?"


def uncertainty(d: Decision) -> float:
    """Pre-registered risk score u = n_L2 + n_forced_unknown + 0.5 * n_provisional."""
    return d.n_l2 + d.n_forced_unknown + 0.5 * d.n_provisional
