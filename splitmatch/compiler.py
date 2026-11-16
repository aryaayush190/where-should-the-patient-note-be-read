"""
splitmatch/compiler.py — CLOUD tier, public data only.

Compiles a trial's verbatim inclusion/exclusion text, ONCE, into a typed
three-valued TrialProgram:
  1. deterministic line splitting + numbering (no model involved)
  2. two independent cloud models (different families) compile the numbered lines
  3. deterministic type-check; one repair round with the error list
  4. per-line agreement between the two compilations; any line on which they
     disagree has its primary atoms DOWNGRADED (no deterministic authority)

Only public trial text is ever sent (channel CLOUD_PUBLIC, guarded).
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from . import llm
from .llm import Channel
from .schema import (FIELDS, THERAPY_CLASSES, XULN_ALIASES, Atom, AtomType, Kind, TrialProgram,
                     program_errors)

PROMPT_VERSION = "compiler-v1.2"

# ── 1. deterministic line splitting ─────────────────────────────────────────
_COHORT_HEADER = re.compile(r"^\s*((stage\s*)?(I{1,3}|IV)[ABC]?|cohort\b.*|arm\b.*|part\b.*|phase\b.*|group\b.*)\s*:\s*$", re.I)
_HEADER = re.compile(r"^\s*(inclusion|exclusion)?\s*(criteria)?\s*:?\s*$", re.I)


def split_lines(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n|\n\s*(?=[-•*]\s)|\n\s*(?=\d{1,2}[.)]\s)", text or "")
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        p = re.sub(r"^[-•*]\s*", "", p)
        if len(p) < 4 or _HEADER.match(p):
            continue
        p = re.sub(r"^(inclusion|exclusion)\s+criteria\s*:\s*", "", p, flags=re.I)
        if len(p) < 4:
            continue
        # a lowercase-initial fragment continues the previous criterion (list items split
        # across blank lines, e.g. "...except: basal cell carcinoma;" / "carcinoma in situ;")
        if out and p[0].islower() and not _COHORT_HEADER.match(out[-1]):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def numbered(trial: dict) -> tuple[list[tuple[int, str, str]], str]:
    """[(line_no, section, text)] and the rendered numbered block."""
    rows, n = [], 0
    for section, key in (("inclusion", "inclusion_criteria"), ("exclusion", "exclusion_criteria")):
        for ln in split_lines(trial.get(key, "")):
            n += 1
            rows.append((n, section, ln))
    block = []
    for section in ("inclusion", "exclusion"):
        block.append(f"## {section.upper()} CRITERIA")
        block += [f"[{i}] {t}" for i, s, t in rows if s == section]
    return rows, "\n".join(block)


# ── 2. prompt ───────────────────────────────────────────────────────────────
def _field_catalogue() -> str:
    lines = []
    for name, sp in FIELDS.items():
        d = f"- {name} ({sp.kind.value}"
        if sp.values:
            d += f": {'|'.join(sp.values)}"
        if sp.unit:
            d += f"; unit {sp.unit}"
        lines.append(d + ")")
    for alias, base in XULN_ALIASES.items():
        lines.append(f"- {alias} (num; multiples of upper limit of normal for {base.split('_')[0]})")
    return "\n".join(lines)


SYSTEM = f"""You compile clinical-trial eligibility criteria into a typed, machine-checkable program.
You see ONLY the trial's public criteria text (numbered lines). Output JSON: {{"atoms": [ ... ]}}.

PATIENT FIELDS you may reference (use exactly these names and enum values):
{_field_catalogue()}
stage_group values are roman stages such as IA, IB, IIA, IIB, IIIA, IIIB, IIIC, IV, IVA, IVB (a base group like "III" covers its substages).
tnm_t / tnm_n / tnm_m are text like "T4", "N2", "M1a" (prefix match).

THERAPY EVENTS: prior treatments have class in {THERAPY_CLASSES} ("systemic" = unspecified systemic therapy; filter on the specific classes you need); optional agents (lower-case drug or drug-class names, e.g. "platinum", "docetaxel", "egfr tki", "pd-1"), thoracic (radiation to the chest), setting (adjuvant|neoadjuvant|advanced|definitive|palliative).

ATOM TYPES (every atom: "type", "polarity", "lines" = list of line numbers it encodes):
- CMP   {{"field","op" in < <= > >= == !=, "value": number}}     e.g. ECOG 0-1 -> CMP ecog <= 1
- IN    {{"field","values":[...]}}                               e.g. stage IIIB or IV -> IN stage_group ["IIIB","IV"]
- IS    {{"field","value": true|false}}                          boolean fields only
- HAS   {{"filter": {{"cls":[...],"agents":[...],"thoracic":bool|null,"setting":[...]}}}}   some prior therapy matches
- WITHIN {{"filter", "months": X}}   a matching therapy was received within the past X months
- SINCE  {{"filter", "months": X}}   ALL matching therapy ended at least X months ago (washout satisfied)
- COUNT {{"filter" (optional), "op", "k"}}   number of prior lines/regimens of matching therapy
- IF    {{"children":[condition, requirement]}}   "requirement applies only if condition"
- ANY / ALL {{"children":[...]}}   OR / AND groups
- JUDGE {{"text", "cwa": true|false}}   criterion that cannot be expressed with the fields above but CAN be judged from a clinical note. cwa=true only for adverse findings/medications/events that a note would normally document if present (e.g. "uncontrolled hypertension", "on CYP3A4 inhibitors").
- UNSCREENABLE {{"text"}}   not decidable at pre-screening from a clinical note: consent, willingness/compliance, contraception agreement, investigator discretion, scheduling/administrative, study-procedure logistics.

POLARITY: "inclusion" atoms must be TRUE for eligibility. "exclusion" atoms describe the EXCLUDING condition (TRUE = patient excluded). A negative requirement written in the inclusion list (e.g. "chemotherapy-naive", "no prior radiotherapy") is encoded as an EXCLUSION atom (HAS chemo, polarity exclusion).

RULES
1. Cover EVERY numbered line with at least one atom. Split multi-part lines into several atoms that share the same line number.
2. Prefer the most specific typed atom; use JUDGE only when no field/therapy atom fits.
3. Units: convert weeks to months by /4.345 and days by /30.44 (round to 3 decimals). Labs in canonical units: platelets and ANC/WBC in 10^3/uL (100,000/mm3 -> 100; 1500/mm3 -> 1.5), haemoglobin g/dL, creatinine and bilirubin mg/dL. "x ULN" limits: bilirubin_xuln / creatinine_xuln / ast_xuln / alt_xuln.
4. Disease: "non-small cell lung cancer" -> IN cancer_type ["nsclc"]. "metastatic" -> stage IV; "locally advanced or metastatic"/"advanced" -> IN stage_group ["IIIB","IIIC","IV"].
5. Performance status: ECOG/Zubrod -> ecog; Karnofsky -> kps.
6. Prior therapy wording: "no prior X" -> HAS X (exclusion); "no X within N weeks" -> WITHIN X months=N/4.345 (exclusion); "at least N weeks since X" -> SINCE (inclusion); "failed/progressed after >= 1 prior platinum regimen" -> COUNT agents ["platinum"] >= 1 (inclusion); "more than one prior regimen" -> COUNT > 1 (exclusion).
7. Conditionals ("stage IIIB only with malignant effusion", "unless", "if ...") -> IF.
7a. ALTERNATIVES: requirements joined by "or" (e.g. "Stage IIIB with effusion OR Stage IV"), and criteria listed under different cohort/arm/phase headers (lines such as "IIIA:", "Cohort B:", "For Phase II:", "Patients with distant metastases ... are eligible") are ALTERNATIVE pathways. Encode them as ONE ANY atom whose children are the pathways (use ALL for a pathway with several conditions). NEVER emit alternatives as separate inclusion atoms (that would wrongly require all of them).
7b. PERMISSIONS: a line that only permits something ("X is allowed/permitted/acceptable if C") is NOT a requirement to have X. Encode only the restriction it implies, as an EXCLUSION (e.g. "prior radiotherapy allowed if completed >= 3 weeks before" -> WITHIN radio months=0.69, exclusion). If no restriction is implied, emit UNSCREENABLE with text "permission: ...".
8. Add "question": a short plain-language question a health worker could ask/check if the needed fact is missing, and "answerable_by": patient|record|clinician.
9. Output JSON only."""


def _messages(block: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": block}]


# ── 3. parse + type-check + repair ──────────────────────────────────────────
_OPS = {"≤": "<=", "=<": "<=", "≥": ">=", "=>": ">=", "=": "==", "<>": "!=", "≠": "!="}


def _normalise(d: dict, by_line: dict) -> dict:
    """Purely syntactic clean-up of model output (case, operator symbols, number
    strings). No semantic change is made here."""
    if "type" in d:
        d["type"] = str(d["type"]).upper().strip()
    if "polarity" in d:
        d["polarity"] = str(d["polarity"]).lower().strip()
    elif d.get("lines"):
        try:
            d["polarity"] = by_line[int(d["lines"][0])][0]
        except (KeyError, ValueError, TypeError):
            pass
    if isinstance(d.get("lines"), int):
        d["lines"] = [d["lines"]]
    if "op" in d and d["op"] is not None:
        d["op"] = _OPS.get(str(d["op"]).strip(), str(d["op"]).strip())
    for k in ("value", "k", "months"):
        v = d.get(k)
        if isinstance(v, str):
            vs = v.strip().lower()
            if vs in ("true", "false") and k == "value":
                d[k] = vs == "true"
            else:
                try:
                    d[k] = float(vs)
                except ValueError:
                    pass
    if isinstance(d.get("values"), (str, int, float)):
        d["values"] = [d["values"]]
    if d.get("field") in ("stage", "stage_group"):
        d["field"] = "stage_group"
    if isinstance(d.get("filter"), dict):
        f = d["filter"]
        for key in ("cls", "agents", "setting"):
            if isinstance(f.get(key), str):
                f[key] = [f[key]]
            if f.get(key) is None:
                f[key] = []
        f["cls"] = [str(c).lower() for c in f.get("cls", [])]
        f["agents"] = [str(c).lower() for c in f.get("agents", [])]
    if d.get("answerable_by") not in (None, "patient", "record", "clinician"):
        d.pop("answerable_by")
    return d


def _to_atoms(raw: Any, rows: list[tuple[int, str, str]], prefix: str = "") -> list[Atom]:
    items = raw.get("atoms", raw) if isinstance(raw, dict) else raw
    by_line = {i: (s, t) for i, s, t in rows}
    atoms = []

    def build(d: dict, aid: str) -> Atom:
        d = _normalise(dict(d), by_line)
        d["id"] = aid
        kids = d.pop("children", []) or []
        lines = [int(x) for x in (d.get("lines") or []) if str(x).isdigit()]
        d["lines"] = lines
        if not d.get("source_line") and lines:
            d["source_line"] = " | ".join(by_line[l][1] for l in lines if l in by_line)
        if lines and lines[0] in by_line:
            d["section"] = by_line[lines[0]][0]
        d["children"] = [build(c, f"{aid}.{j}") for j, c in enumerate(kids)]
        allowed = set(Atom.model_fields)
        return Atom(**{k: v for k, v in d.items() if k in allowed})

    for j, d in enumerate(items or []):
        try:
            atoms.append(build(d, f"{prefix}A{j}"))
        except Exception as e:  # malformed atom -> keep as JUDGE so the line is not lost
            lines = [int(x) for x in (d.get("lines") or []) if str(x).isdigit()] if isinstance(d, dict) else []
            pol = str(d.get("polarity", "inclusion")).lower() if isinstance(d, dict) else "inclusion"
            atoms.append(Atom(id=f"{prefix}A{j}", type=AtomType.JUDGE, lines=lines,
                              polarity=pol if pol in ("inclusion", "exclusion") else "inclusion",
                              text=f"[unparseable atom: {e}]", downgraded=True,
                              source_line=" | ".join(by_line[l][1] for l in lines if l in by_line)))
    return atoms


def _render(rows) -> str:
    out = []
    for section in ("inclusion", "exclusion"):
        sub = [(i, t) for i, s, t in rows if s == section]
        if sub:
            out.append(f"## {section.upper()} CRITERIA")
            out += [f"[{i}] {t}" for i, t in sub]
    return "\n".join(out)


def _chunks(rows, model: str):
    size = 22 if "gpt-oss" in model else 16
    return [rows[i:i + size] for i in range(0, len(rows), size)]


def _compile_chunk(trial_id: str, rows, model: str, run_id: str, ci: int) -> tuple[list[Atom], dict]:
    msgs = _messages(_render(rows))
    extra = {"response_format": {"type": "json_object"}}
    max_tok = 24000 if "gpt-oss" in model else 6000
    if "gpt-oss" in model:
        extra["reasoning_effort"] = "medium"
    meta = {"repaired": False}
    try:
        rep = llm.call(Channel.CLOUD_PUBLIC, msgs, model=model, max_tokens=max_tok, extra=extra,
                       run_id=run_id, tag=f"compile:{trial_id}:{model}:c{ci}")
        atoms = _to_atoms(llm.parse_json(rep.text), rows, prefix=f"c{ci}")
    except Exception as e:                       # unparseable / rejected -> every line becomes JUDGE
        meta["failure"] = str(e)[:200]
        return [Atom(id=f"c{ci}F{i}", type=AtomType.JUDGE, polarity=s, lines=[i], source_line=t,
                     text=t, downgraded=True) for i, s, t in rows], meta
    errs = program_errors(TrialProgram(trial_id=trial_id, atoms=atoms)) + _coverage_errors(atoms, rows)
    if errs:
        meta["repaired"] = True
        meta["errors_before_repair"] = errs[:30]
        msgs2 = msgs + [{"role": "assistant", "content": rep.text},
                        {"role": "user", "content": "Fix these problems and return the FULL corrected "
                                                    "JSON:\n- " + "\n- ".join(errs[:40])}]
        try:
            rep2 = llm.call(Channel.CLOUD_PUBLIC, msgs2, model=model, max_tokens=max_tok, extra=extra,
                            run_id=run_id, tag=f"repair:{trial_id}:{model}:c{ci}")
            atoms2 = _to_atoms(llm.parse_json(rep2.text), rows, prefix=f"c{ci}")
            errs2 = program_errors(TrialProgram(trial_id=trial_id, atoms=atoms2)) + \
                _coverage_errors(atoms2, rows)
            if len(errs2) <= len(errs):
                atoms, errs = atoms2, errs2
        except Exception as e:
            meta["repair_failure"] = str(e)[:200]
    # uncovered lines are kept as downgraded JUDGE atoms (nothing silently dropped)
    covered = {l for a in atoms for l in a.lines}
    for i, s, t in rows:
        if i not in covered:
            atoms.append(Atom(id=f"c{ci}M{i}", type=AtomType.JUDGE, polarity=s, lines=[i],
                              source_line=t, text=t, downgraded=True))
    meta["errors_after_repair"] = errs[:30]
    return atoms, meta


STAGE_FIELDS = {"stage_group", "tnm_t", "tnm_n", "tnm_m"}


def _is_stage_req(a: Atom) -> bool:
    leaves = [l for l, _ in _leaves(a)]
    return a.polarity == "inclusion" and bool(leaves) and any(l.field in STAGE_FIELDS for l in leaves) and         all(l.field in STAGE_FIELDS | {"malignant_effusion"} for l in leaves if l.field)


def merge_stage_alternatives(atoms: list[Atom]) -> tuple[list[Atom], int]:
    """Two or more top-level stage/TNM REQUIREMENTS on the same criterion line are
    alternatives (a patient has one stage): merge them into a single ANY atom."""
    by_line: dict[tuple, list[Atom]] = {}
    for a in atoms:
        if _is_stage_req(a) and a.type is not AtomType.ANY:
            by_line.setdefault(tuple(a.lines), []).append(a)
    merged, n = [], 0
    consumed = set()
    for key, group in by_line.items():
        if len(group) >= 2:
            n += 1
            consumed |= {g.id for g in group}
            merged.append(Atom(id=group[0].id + "+any", type=AtomType.ANY, polarity="inclusion",
                               lines=list(key), source_line=group[0].source_line,
                               children=[g.model_copy(update={"id": f"{group[0].id}+any.{i}"})
                                         for i, g in enumerate(group)],
                               downgraded=any(g.downgraded for g in group),
                               question=group[0].question, answerable_by=group[0].answerable_by))
    out = [a for a in atoms if a.id not in consumed] + merged
    return out, n


def compile_once(trial: dict, model: str, run_id: str = "compile") -> tuple[TrialProgram, dict]:
    rows, _ = numbered(trial)
    atoms, chunk_meta = [], []
    for ci, chunk in enumerate(_chunks(rows, model)):
        a, m = _compile_chunk(trial["trial_id"], chunk, model, run_id, ci)
        atoms += a
        chunk_meta.append(m)
    atoms, n_merged = merge_stage_alternatives(atoms)
    prog = TrialProgram(trial_id=trial["trial_id"], atoms=atoms)
    errs = program_errors(prog)
    meta = {"stage_alternatives_merged": n_merged, "model": model, "prompt_version": PROMPT_VERSION, "n_lines": len(rows),
            "repaired": any(m["repaired"] for m in chunk_meta),
            "chunk_failures": [m.get("failure") for m in chunk_meta if m.get("failure")]}
    # atoms that still fail the type-check become JUDGE (never silently dropped)
    bad_ids = {e.split(":")[0].split(".")[0] for e in program_errors(prog)}
    fixed = []
    for a in prog.atoms:
        if a.id in bad_ids:
            fixed.append(Atom(id=a.id, type=AtomType.JUDGE, polarity=a.polarity, lines=a.lines,
                              source_line=a.source_line, text=a.source_line, downgraded=True,
                              question=a.question, answerable_by=a.answerable_by))
        else:
            fixed.append(a)
    prog = TrialProgram(trial_id=trial["trial_id"], atoms=fixed)
    meta["errors_after_repair"] = errs[:50]
    meta["n_atoms"] = len(fixed)
    return prog, meta


def _coverage_errors(atoms, rows) -> list[str]:
    covered = {l for a in atoms for l in a.lines}
    return [f"line [{i}] has no atom" for i, _, _ in rows if i not in covered]


# ── 4. cross-model agreement ────────────────────────────────────────────────
def _num(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return x


def signature(a: Atom) -> Any:
    """Canonical, order-independent description of what an atom checks."""
    t = a.type.value
    if t in ("JUDGE", "UNSCREENABLE"):
        return (t, a.polarity)
    f = a.filter
    flt = None if f is None else (tuple(sorted(f.cls)), tuple(sorted(x.lower() for x in f.agents)),
                                  f.thoracic, tuple(sorted(f.setting)))
    kids = tuple(sorted((signature(c) for c in a.children), key=repr))
    vals = tuple(sorted(str(v).upper() for v in a.values))
    return (t, a.polarity, a.field, a.op, _num(a.value) if not isinstance(a.value, bool) else a.value,
            vals, flt, _num(a.k), _num(a.months), kids)


def line_agreement(p1: TrialProgram, p2: TrialProgram, rows) -> dict[int, bool]:
    def by_line(p):
        d: dict[int, set] = {}
        for a in p.atoms:
            for l in a.lines:
                d.setdefault(l, set()).add(repr(signature(a)))
        return d
    b1, b2 = by_line(p1), by_line(p2)
    return {i: b1.get(i, set()) == b2.get(i, set()) for i, _, _ in rows}


def _leaves(a: Atom, lines=None):
    lines = lines or a.lines
    if a.children:
        for c in a.children:
            yield from _leaves(c, c.lines or lines)
    else:
        yield a, set(lines)


def _leaf_equiv(a: Atom, b: Atom) -> bool:
    from .evaluator import expand_allowed
    if a.type != b.type:
        return False
    t = a.type
    if t in (AtomType.CMP,):
        return a.field == b.field and a.op == b.op and _close(a.value, b.value)
    if t is AtomType.IN:
        if a.field != b.field:
            return False
        if a.field == "stage_group":
            return _finest(expand_allowed(a.values)) == _finest(expand_allowed(b.values))
        return {str(v).lower() for v in a.values} == {str(v).lower() for v in b.values}
    if t is AtomType.IS:
        return a.field == b.field and a.value == b.value
    if t in (AtomType.HAS, AtomType.WITHIN, AtomType.SINCE, AtomType.COUNT):
        fa, fb = a.filter, b.filter
        ca = set(fa.cls) if fa else set()
        cb = set(fb.cls) if fb else set()
        if ca != cb:
            return False
        if t in (AtomType.WITHIN, AtomType.SINCE) and not _close(a.months, b.months, rel=0.10):
            return False
        if t is AtomType.COUNT and not (a.op == b.op and _close(a.k, b.k)):
            return False
        return True
    return t in (AtomType.JUDGE, AtomType.UNSCREENABLE)


_FINEST = {"I": {"IA1", "IA2", "IA3", "IB"}, "IA": {"IA1", "IA2", "IA3"}, "II": {"IIA", "IIB"},
           "III": {"IIIA", "IIIB", "IIIC"}, "IV": {"IVA", "IVB"}}


def _finest(stages: set[str]) -> set[str]:
    out = set()
    for s in stages:
        out |= _FINEST.get(s, {s})
    return out


def _close(x, y, rel=0.02) -> bool:
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError):
        return x == y
    return abs(x - y) <= max(rel * max(abs(x), abs(y)), 1e-6)


def atom_agreed(a: Atom, other: TrialProgram) -> bool:
    """A primary atom keeps deterministic authority iff every typed leaf has an
    equivalent leaf in the independent compilation on an overlapping line, with
    the same top-level polarity."""
    pool = [(l, ls, top.polarity) for top in other.atoms for l, ls in _leaves(top)]
    for leaf, ls in _leaves(a):
        if leaf.type in (AtomType.JUDGE, AtomType.UNSCREENABLE):
            continue
        if not any(_leaf_equiv(leaf, o) and (ls & ols) and pol == a.polarity
                   for o, ols, pol in pool):
            return False
    return True


def compile_trial(trial: dict, run_id: str = "compile",
                  single_model: bool = False) -> TrialProgram:
    rows, _ = numbered(trial)
    p1, m1 = compile_once(trial, llm.CLOUD_PRIMARY, run_id)
    if single_model:
        p1.compiler_meta = {"primary": m1, "single_model": True}
        return p1
    p2, m2 = compile_once(trial, llm.CLOUD_SECONDARY, run_id)
    agree = line_agreement(p1, p2, rows)
    atoms, n_typed, n_typed_agree = [], 0, 0
    for a in p1.atoms:
        typed = a.type not in (AtomType.JUDGE, AtomType.UNSCREENABLE)
        if typed:
            n_typed += 1
            ok = (not a.downgraded) and atom_agreed(a, p2)
            n_typed_agree += ok
            if not ok:
                a = a.model_copy(update={"downgraded": True})
        atoms.append(a)
    meta = {"primary": m1, "secondary": m2, "prompt_version": PROMPT_VERSION,
            "lines": len(rows), "lines_exact_agree": sum(agree.values()),
            "typed_atoms": n_typed, "typed_atoms_agree": n_typed_agree,
            "downgraded_atoms": sum(a.downgraded for a in atoms)}
    return TrialProgram(trial_id=trial["trial_id"], atoms=atoms, compiler_meta=meta)
