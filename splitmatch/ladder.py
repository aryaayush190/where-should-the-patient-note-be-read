"""
splitmatch/ladder.py — escalation ladder for residual criteria.

L1  EDGE judge, batched PER PATIENT over all residual criteria of all that
    patient's trials (one local call per patient, not per pair). It reads the
    full private note (it runs on the device) and returns, per criterion, a
    verdict T/F/U, whether the needed fact is stated in the note, and a
    MINIMAL fact statement (no identifiers, no narrative copying).
L2  CLOUD judge on ONE criterion + the L1 minimal fact statement (guarded:
    no narrative sentence and no identifier can pass). Used for reasoning
    capacity on stated-but-ambiguous facts and as the second key for
    exclusions that only the L1 judge supports.
"""
from __future__ import annotations

import hashlib
import json

from . import llm
from .llm import Channel

L1_VERSION = "l1-v1"
L2_VERSION = "l2-v2"

L1_SYSTEM = """You are a careful clinical pre-screening assistant running on a clinic device.
You get ONE patient note and a numbered list of criterion statements. For EACH statement decide
whether it is true for this patient, using ONLY the note.
Return JSON {"items": [{"id": <id>, "verdict": "T"|"F"|"U", "basis": "stated"|"not_mentioned", "fact": "<minimal fact>"}]}
- verdict T = the statement is true; F = false; U = cannot be decided from the note.
- For an [EXCLUSION] statement, T means the excluding condition IS present.
- basis "not_mentioned" when the note says nothing relevant (then verdict must be U).
- fact: the minimal clinical fact(s) needed for this one statement, rewritten in your own words in
  at most 20 words, e.g. "last platinum chemotherapy ended 1-3 months ago". Never include the
  patient's name, age, sex, or any sentence copied from the note. Use "not stated" if not mentioned.
JSON only."""

L2_SYSTEM = """You are an oncology trial-eligibility expert. You get ONE criterion statement and a
minimal description of the relevant patient facts (nothing else is available).
Return JSON {"verdict": "T"|"F"|"U", "why": "<= 20 words"}.
For an [EXCLUSION] statement, T means the excluding condition IS present. Use U only if the facts
genuinely do not allow a decision. JSON only."""


def item_key(statement: str) -> str:
    return hashlib.sha1(statement.encode("utf-8")).hexdigest()[:10]


def _l1_call(patient_ref, note, statements, part, channel, run_id) -> list[dict]:
    lst = "\n".join(f"{k}: {statements[k]}" for k in part)
    msgs = [{"role": "system", "content": L1_SYSTEM},
            {"role": "user", "content": f"PATIENT NOTE:\n{note}\n\nSTATEMENTS:\n{lst}"}]
    if channel is Channel.EDGE_LOCAL:
        extra, mt = {"json": True}, 120 + 75 * len(part)
    else:
        extra, mt = {"response_format": {"type": "json_object"}, "reasoning_effort": "low"}, 4000 + 120 * len(part)
    rep = llm.call(channel, msgs, max_tokens=mt, extra=extra, run_id=run_id, tag="l1",
                   local_ref=patient_ref)
    j = llm.parse_json(rep.text)
    items = j.get("items", j) if isinstance(j, dict) else j
    if isinstance(items, dict):                       # {"<id>": {...}} form
        items = [{"id": k, **v} for k, v in items.items() if isinstance(v, dict)]
    return [it for it in (items or []) if isinstance(it, dict)]


def l1_batch(patient_ref: str, note: str, statements: dict[str, str], channel: Channel,
             run_id: str = "", chunk: int = 12) -> dict[str, dict]:
    """statements: {key: statement}. Returns {key: {verdict, basis, fact}}.
    A failed batch is split in half and retried (down to single statements);
    statements the judge never answers are marked basis="unavailable"."""
    out: dict[str, dict] = {}
    keys = sorted(statements)
    queue = [keys[i:i + chunk] for i in range(0, len(keys), chunk)]
    errors = []
    while queue:
        part = queue.pop(0)
        try:
            items = _l1_call(patient_ref, note, statements, part, channel, run_id)
        except Exception as e:
            errors.append(str(e)[:160])
            if len(part) > 1:
                h = len(part) // 2
                queue[:0] = [part[:h], part[h:]]
            continue
        for it in items:
            k = str(it.get("id", "")).strip()
            if k in statements:
                v = str(it.get("verdict", "U")).upper()[:1]
                out[k] = {"verdict": v if v in "TFU" else "U",
                          "basis": "not_mentioned" if str(it.get("basis", "")).startswith("not") else "stated",
                          "fact": str(it.get("fact", "not stated"))[:240]}
    for k in keys:
        out.setdefault(k, {"verdict": "U", "basis": "unavailable", "fact": "not stated"})
    if errors:
        out["_errors"] = {"n": len(errors), "first": errors[0]}
    return out


L2_FORCED_RUBRIC = (" This is a forced binary pre-screening decision. Labelling convention: if a REQUIRED"
                    " clinical finding or treatment-history item (e.g. a required effusion, stage, histology,"
                    " biomarker, or prior-therapy failure) is not documented, it counts as NOT met (F)."
                    " Minor details that are not documented (e.g. weight loss, exact dates, routine"
                    " assessments) are presumed acceptable (T).")


def l2_judge(statement: str, fact: str, local_ref: str, disclosed: list[str],
             run_id: str = "", forced: bool = False) -> dict:
    msgs = [{"role": "system", "content": L2_SYSTEM + (L2_FORCED_RUBRIC if forced else "")},
            {"role": "user", "content": f"CRITERION: {statement}\nPATIENT FACTS: {fact}"}]
    try:
        rep = llm.call(Channel.CLOUD_FACT, msgs, max_tokens=1500,
                       extra={"response_format": {"type": "json_object"}, "reasoning_effort": "low"},
                       run_id=run_id, tag="l2", local_ref=local_ref, disclosed_fields=disclosed)
        j = llm.parse_json(rep.text)
        v = str(j.get("verdict", "U")).upper()[:1]
        return {"verdict": v if v in "TFU" else "U", "why": str(j.get("why", ""))[:200]}
    except llm.PrivacyViolation as e:
        # the fact statement leaked note text -> it is NOT sent; the criterion is deferred
        return {"verdict": "U", "why": "blocked by privacy guard", "blocked": True, "err": str(e)[:120]}
    except Exception as e:
        return {"verdict": "U", "why": "error", "err": str(e)[:120]}
