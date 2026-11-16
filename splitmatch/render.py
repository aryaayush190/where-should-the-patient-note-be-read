"""Human-readable rendering of atoms (for the local judge, cloud fact queries,
ASK questions and the audit trail)."""
from __future__ import annotations

from .schema import FIELDS, Atom, AtomType

OPW = {"<": "below", "<=": "at most", ">": "above", ">=": "at least", "==": "equal to", "!=": "not"}


def _flt(a: Atom) -> str:
    f = a.filter
    if not f:
        return "any prior anticancer therapy"
    parts = []
    if f.agents:
        parts.append("/".join(f.agents))
    if f.cls:
        parts.append("/".join(f.cls))
    if f.thoracic:
        parts.append("to the chest")
    if f.setting:
        parts.append(f"({'/'.join(f.setting)} setting)")
    return "prior " + " ".join(parts) if parts else "any prior anticancer therapy"


def render(a: Atom) -> str:
    t = a.type
    if t is AtomType.CMP:
        unit = FIELDS.get(a.field).unit if a.field in FIELDS else ""
        return f"{a.field} {OPW.get(a.op, a.op)} {a.value:g} {unit}".strip()
    if t is AtomType.IN:
        return f"{a.field} is one of {', '.join(map(str, a.values))}"
    if t is AtomType.IS:
        return f"{a.field} is {'present' if a.value else 'absent'}"
    if t is AtomType.HAS:
        return f"patient has had {_flt(a)}"
    if t is AtomType.WITHIN:
        return f"patient received {_flt(a)} within the past {a.months:.2f} months"
    if t is AtomType.SINCE:
        return f"at least {a.months:.2f} months have passed since {_flt(a)}"
    if t is AtomType.COUNT:
        return f"number of {_flt(a)} lines/regimens is {OPW.get(a.op, a.op)} {a.k:g}"
    if t is AtomType.IF:
        return f"IF ({render(a.children[0])}) THEN ({render(a.children[1])})"
    if t in (AtomType.ANY, AtomType.ALL):
        j = " OR " if t is AtomType.ANY else " AND "
        return "(" + j.join(render(c) for c in a.children) + ")"
    return a.text or a.source_line


def judge_polarity(a: Atom) -> str:
    """Polarity in which a judge's T/F verdict must be read. A contested (downgraded)
    atom is judged on its VERBATIM criterion line, so its section decides."""
    if a.downgraded and a.source_line and a.section:
        return a.section
    return a.polarity


def statement(a: Atom) -> str:
    """The criterion as a statement whose truth the judge evaluates.
    INCLUSION: true = requirement met. EXCLUSION: true = excluding condition present.
    Contested (downgraded) atoms are judged on the verbatim criterion text, because
    their compiled form is exactly what the two compilers disagreed on."""
    if a.downgraded and a.source_line and a.section:
        core, pol = a.source_line, a.section
    else:
        core, pol = render(a), a.polarity
    if pol == "exclusion":
        return f"[EXCLUSION — true means the patient is EXCLUDED] {core}"
    return f"[INCLUSION — true means the requirement is MET] {core}"
