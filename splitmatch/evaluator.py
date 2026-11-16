"""
splitmatch/evaluator.py — deterministic, local, three-valued evaluation of a
compiled TrialProgram against a FactSheet. No LLM, no network.

Kleene strong logic over {T, F, U}. Every AtomResult also says whether the
verdict is VERIFIED (all facts used are two-reader verified, no compiler
disagreement, no approximate conversion near the threshold) and whether it
rests on an ASSUMED pertinent negative (closed-world default). The authority
policy (policy.py) only lets VERIFIED negative verdicts exclude a patient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .schema import (FIELDS, INF, SYSTEMIC_CLASSES, ULN, XULN_ALIASES, Atom, AtomType, EventFilter, Fact,
                     FactSheet, Kind, Status, TherapyEvent, TrialProgram)


class TV(str, Enum):
    T = "T"
    F = "F"
    U = "U"


def t_not(a: TV) -> TV:
    return {TV.T: TV.F, TV.F: TV.T, TV.U: TV.U}[a]


def t_and(*xs: TV) -> TV:
    if any(x is TV.F for x in xs):
        return TV.F
    if all(x is TV.T for x in xs):
        return TV.T
    return TV.U


def t_or(*xs: TV) -> TV:
    if any(x is TV.T for x in xs):
        return TV.T
    if all(x is TV.F for x in xs):
        return TV.F
    return TV.U


def t_implies(a: TV, b: TV) -> TV:
    return t_or(t_not(a), b)


@dataclass
class AtomResult:
    atom_id: str
    value: TV
    verified: bool = False
    assumed: bool = False
    approx: bool = False
    unscreenable: bool = False
    facts: list[str] = field(default_factory=list)
    reason: str = ""


# ── interval comparison ─────────────────────────────────────────────────────
def cmp_interval(lo: float, hi: float, op: str, v: float) -> TV:
    if op == "<":
        return TV.T if hi < v else TV.F if lo >= v else TV.U
    if op == "<=":
        return TV.T if hi <= v else TV.F if lo > v else TV.U
    if op == ">":
        return TV.T if lo > v else TV.F if hi <= v else TV.U
    if op == ">=":
        return TV.T if lo >= v else TV.F if hi < v else TV.U
    if op == "==":
        if lo == hi == v:
            return TV.T
        return TV.F if (v < lo or v > hi) else TV.U
    if op == "!=":
        return t_not(cmp_interval(lo, hi, "==", v))
    raise ValueError(op)


def near(lo: float, hi: float, v: float, rel: float = 0.10) -> bool:
    tol = abs(v) * rel if v != 0 else rel
    return any(abs(e - v) <= tol for e in (lo, hi) if e not in (INF, -INF))


# ── performance-status conversion (WHO/ECOG ↔ Karnofsky) ───────────────────
ECOG_TO_KPS = {0: (90.0, 100.0), 1: (70.0, 80.0), 2: (50.0, 60.0), 3: (30.0, 40.0), 4: (10.0, 20.0)}


def kps_to_ecog(lo: float, hi: float) -> tuple[float, float]:
    def one(k: float) -> float:
        return 0 if k >= 90 else 1 if k >= 70 else 2 if k >= 50 else 3 if k >= 30 else 4
    return float(one(hi)), float(one(lo))


def ecog_to_kps(lo: float, hi: float) -> tuple[float, float]:
    return ECOG_TO_KPS[int(hi)][0], ECOG_TO_KPS[int(lo)][1]


# ── fact resolution ─────────────────────────────────────────────────────────
@dataclass
class Resolved:
    status: Status
    value: object
    verified: bool
    assumed: bool = False
    approx: bool = False


def resolve(fs: FactSheet, name: str) -> Resolved:
    """Return the effective value of a field, applying derivations and the
    closed-world default for pertinent negatives."""
    if name in XULN_ALIASES:                       # ×ULN view of an absolute lab
        base = resolve(fs, XULN_ALIASES[name])
        if base.status is Status.VALUE:
            u = ULN[XULN_ALIASES[name]]
            lo, hi = base.value
            return Resolved(Status.VALUE, [lo / u, hi / u], base.verified, base.assumed, True)
        return base
    f: Fact = fs.get(name)
    if f.status is Status.NOT_MENTIONED:
        if name == "ecog":
            k = fs.get("kps")
            if k.status is Status.VALUE:
                return Resolved(Status.VALUE, list(kps_to_ecog(*k.value)), k.verified, approx=True)
        if name == "kps":
            e = fs.get("ecog")
            if e.status is Status.VALUE:
                return Resolved(Status.VALUE, list(ecog_to_kps(*e.value)), e.verified, approx=True)
        if name == "mi_months_ago":
            h = resolve(fs, "mi_history")
            if h.status is not Status.VALUE or h.value is False:
                return Resolved(Status.NEGATED, None, h.verified, h.assumed)
        spec = FIELDS.get(name)
        if spec is not None and spec.cwa_default is not None:
            v = spec.cwa_default
            if spec.kind is Kind.NUM:
                v = [float(v), float(v)]
            return Resolved(Status.VALUE, v, False, assumed=True)
        return Resolved(Status.NOT_MENTIONED, None, f.verified)
    if f.status is Status.NEGATED:
        spec = FIELDS.get(name)
        if spec is not None:
            if spec.kind is Kind.BOOL:
                return Resolved(Status.VALUE, False, f.verified)
            if spec.kind is Kind.ENUM and "none" in spec.values:
                return Resolved(Status.VALUE, "none", f.verified)
            if name == "neuropathy_grade":
                return Resolved(Status.VALUE, [0.0, 0.0], f.verified)
        return Resolved(Status.NEGATED, None, f.verified)
    return Resolved(Status.VALUE, f.value, f.verified)


# ── stage logic (ported from INDICON app.py, extended to AJCC-8 substages) ──
STAGE_SUBSTAGES = {
    "I": ["I", "IA", "IA1", "IA2", "IA3", "IB"],
    "IA": ["IA", "IA1", "IA2", "IA3"],
    "II": ["II", "IIA", "IIB"],
    "III": ["III", "IIIA", "IIIB", "IIIC"],
    "IV": ["IV", "IVA", "IVB"],
}
TN_TO_GROUP = {"T1N0": "IA", "T1AN0": "IA", "T1BN0": "IA", "T1CN0": "IA", "T2N0": "IB",
               "T2AN0": "IB"}


def _norm_stage(s: str) -> str:
    return str(s).upper().replace("STAGE", "").replace(" ", "").strip()


def expand_allowed(allowed) -> set[str]:
    out = set()
    for a in allowed or []:
        A = _norm_stage(a)
        if not A:
            continue
        out.add(A)
        out.update(STAGE_SUBSTAGES.get(A, []))
        if A in TN_TO_GROUP:
            out.add(TN_TO_GROUP[A])
    return out


def stage_in(patient_stage: str, allowed) -> TV:
    A = expand_allowed(allowed)
    p = _norm_stage(patient_stage)
    cands = {p} | ({TN_TO_GROUP[p]} if p in TN_TO_GROUP else set())
    if cands & A:
        return TV.T
    subs = set(STAGE_SUBSTAGES.get(p, [])) - {p}
    if subs and subs & A:          # patient stage is coarser than the criterion
        return TV.T if subs <= A else TV.U
    return TV.F


def prefix_in(patient_val: str, allowed) -> TV:
    p = str(patient_val).upper().strip()
    al = [str(a).upper().strip() for a in allowed]
    if any(p.startswith(a) for a in al):
        return TV.T
    if any(a.startswith(p) for a in al):   # patient less specific (M1 vs M1a)
        return TV.U
    return TV.F


# ── therapy-event matching ──────────────────────────────────────────────────
def event_matches(ev: TherapyEvent, flt: EventFilter | None) -> TV:
    flt = flt or EventFilter()
    if "systemic" in flt.cls:              # "any systemic therapy" covers every systemic class
        flt = flt.model_copy(update={"cls": sorted(set(flt.cls) | SYSTEMIC_CLASSES | {"systemic"})})
    if flt.cls and ev.cls not in flt.cls:
        # an unspecified "systemic therapy" may be any systemic class -> unknown
        if ev.cls == "systemic" and (set(flt.cls) & SYSTEMIC_CLASSES):
            return TV.U
        return TV.F
    if flt.agents:
        names = " ".join([ev.cls] + [a.lower() for a in ev.agents])
        if not any(a.lower() in names for a in flt.agents):
            # class matched but the agent list is empty → cannot tell which agent
            return TV.U if (not ev.agents and (not flt.cls or ev.cls in flt.cls)) else TV.F
    if flt.thoracic is not None:
        if ev.thoracic is None:
            return TV.U
        if ev.thoracic != flt.thoracic:
            return TV.F
    if flt.setting:
        if ev.setting is None:
            return TV.U
        if ev.setting not in flt.setting:
            return TV.F
    return TV.T


def _ev_months(ev: TherapyEvent):
    if ev.ongoing:
        return (0.0, 0.0)
    return tuple(ev.months_ago) if ev.months_ago else None


def therapy_within(fs: FactSheet, flt, months: float) -> tuple[TV, bool]:
    """Some matching event's last dose was < `months` ago."""
    therapy_verified = bool(fs.reader_meta.get("therapy_verified", False))
    if fs.therapy_status is Status.NEGATED and not fs.events:
        return TV.F, therapy_verified
    if fs.therapy_status is Status.NOT_MENTIONED and not fs.events:
        return TV.U, False
    vals, ver = [], True
    for ev in fs.events:
        m = event_matches(ev, flt)
        mo = _ev_months(ev)
        w = TV.U if mo is None else (TV.T if mo[1] < months else TV.F if mo[0] >= months else TV.U)
        vals.append(t_and(m, w))
        if m is not TV.F:
            ver = ver and ev.verified
    return (t_or(*vals) if vals else TV.F), ver and bool(vals)


def therapy_has(fs: FactSheet, flt) -> tuple[TV, bool]:
    therapy_verified = bool(fs.reader_meta.get("therapy_verified", False))
    if fs.therapy_status is Status.NEGATED and not fs.events:
        return TV.F, therapy_verified
    if fs.therapy_status is Status.NOT_MENTIONED and not fs.events:
        return TV.U, False
    vals = [event_matches(ev, flt) for ev in fs.events]
    res = t_or(*vals) if vals else TV.F
    if res is TV.T:
        ver = any(v is TV.T and ev.verified for v, ev in zip(vals, fs.events))
    else:
        ver = all(ev.verified for ev in fs.events) and (therapy_verified or bool(fs.events))
    return res, ver


def therapy_count(fs: FactSheet, flt) -> tuple[list[float] | None, bool]:
    if fs.therapy_status is Status.NEGATED and not fs.events:
        return [0.0, 0.0], bool(fs.reader_meta.get("therapy_verified", False))
    if fs.therapy_status is Status.NOT_MENTIONED and not fs.events:
        return None, False
    # Lines of therapy: prefer an explicit statement when the filter is "any systemic"
    if fs.lines_of_therapy is not None and (flt is None or not (flt.cls or flt.agents)):
        return list(fs.lines_of_therapy), bool(fs.reader_meta.get("lines_verified", False))
    sure = sum(1 for ev in fs.events if event_matches(ev, flt) is TV.T)
    maybe = sum(1 for ev in fs.events if event_matches(ev, flt) is TV.U)
    return [float(sure), float(sure + maybe)], all(ev.verified for ev in fs.events)


# ── atom evaluation ─────────────────────────────────────────────────────────
def evaluate_atom(atom: Atom, fs: FactSheet) -> AtomResult:
    r = _eval(atom, fs)
    if atom.downgraded:
        r.verified = False
        r.reason = (r.reason + " | compiler-disagreement").strip(" |")
    return r


def _eval(atom: Atom, fs: FactSheet) -> AtomResult:
    t = atom.type
    R = lambda v, **kw: AtomResult(atom.id, v, **kw)  # noqa: E731

    if t is AtomType.UNSCREENABLE:
        return R(TV.U, unscreenable=True, reason="not decidable at pre-screening")
    if t is AtomType.JUDGE:
        return R(TV.U, reason="semantic criterion → ladder")

    if t in (AtomType.CMP, AtomType.IN, AtomType.IS):
        rs = resolve(fs, atom.field)
        facts = [atom.field]
        if rs.status is Status.NOT_MENTIONED:
            return R(TV.U, facts=facts, reason=f"{atom.field} not mentioned")
        if rs.status is Status.NEGATED:
            # e.g. mi_months_ago when no MI: the comparison concerns a non-event
            return R(TV.F, verified=rs.verified, assumed=rs.assumed, facts=facts,
                     reason=f"no {atom.field} event")
        if t is AtomType.CMP:
            lo, hi = rs.value
            v = cmp_interval(lo, hi, atom.op, float(atom.value))
            approx_near = rs.approx and near(lo, hi, float(atom.value))
            return R(v, verified=rs.verified and not approx_near, assumed=rs.assumed,
                     approx=rs.approx, facts=facts,
                     reason=f"{atom.field}=[{lo},{hi}] {atom.op} {atom.value}")
        if t is AtomType.IN:
            if atom.field == "stage_group":
                v = stage_in(rs.value, atom.values)
            elif atom.field in ("tnm_t", "tnm_n", "tnm_m"):
                v = prefix_in(rs.value, atom.values)
            else:
                v = TV.T if str(rs.value) in [str(x) for x in atom.values] else TV.F
            return R(v, verified=rs.verified, assumed=rs.assumed, facts=facts,
                     reason=f"{atom.field}={rs.value} in {atom.values}")
        v = TV.T if bool(rs.value) is bool(atom.value) else TV.F
        return R(v, verified=rs.verified, assumed=rs.assumed, facts=facts,
                 reason=f"{atom.field}={rs.value} is {atom.value}")

    if t is AtomType.HAS:
        v, ver = therapy_has(fs, atom.filter)
        return R(v, verified=ver, facts=["therapy"], reason="has matching therapy")
    if t is AtomType.WITHIN:
        v, ver = therapy_within(fs, atom.filter, float(atom.months))
        return R(v, verified=ver, facts=["therapy"], reason=f"therapy within {atom.months} mo")
    if t is AtomType.SINCE:
        v, ver = therapy_within(fs, atom.filter, float(atom.months))
        return R(t_not(v), verified=ver, facts=["therapy"], reason=f"washout >= {atom.months} mo")
    if t is AtomType.COUNT:
        n, ver = therapy_count(fs, atom.filter)
        if n is None:
            return R(TV.U, facts=["therapy"], reason="therapy history not mentioned")
        v = cmp_interval(n[0], n[1], atom.op, float(atom.k))
        return R(v, verified=ver, facts=["therapy"], reason=f"count={n} {atom.op} {atom.k}")

    kids = [evaluate_atom(c, fs) for c in atom.children]
    facts = sorted({f for k in kids for f in k.facts})
    assumed = any(k.assumed for k in kids)
    approx = any(k.approx for k in kids)
    if t is AtomType.IF:
        a, b = kids
        v = t_implies(a.value, b.value)
        if v is TV.T:
            ver = (a.value is TV.F and a.verified) or (b.value is TV.T and b.verified)
        else:
            ver = a.verified and b.verified
        return R(v, verified=ver, assumed=assumed, approx=approx, facts=facts, reason="if-then")
    if t is AtomType.ANY:
        v = t_or(*[k.value for k in kids])
        ver = any(k.value is TV.T and k.verified for k in kids) if v is TV.T else all(k.verified for k in kids)
        return R(v, verified=ver, assumed=assumed, approx=approx, facts=facts, reason="any-of")
    if t is AtomType.ALL:
        v = t_and(*[k.value for k in kids])
        ver = any(k.value is TV.F and k.verified for k in kids) if v is TV.F else all(k.verified for k in kids)
        return R(v, verified=ver, assumed=assumed, approx=approx, facts=facts, reason="all-of")
    raise ValueError(f"unhandled atom type {t}")


def evaluate_program(prog: TrialProgram, fs: FactSheet) -> list[tuple[Atom, AtomResult]]:
    return [(a, evaluate_atom(a, fs)) for a in prog.atoms]
