"""Unit tests for the three-valued evaluator. Generic constraint types only —
no test-set trial or patient content is used here."""
import math

import pytest

from splitmatch.evaluator import (TV, cmp_interval, evaluate_atom, kps_to_ecog, resolve,
                                  stage_in, t_and, t_implies, t_not, t_or)
from splitmatch.schema import (Atom, AtomType, EventFilter, Fact, FactSheet, Status,
                               TherapyEvent, TrialProgram, program_errors, type_errors)

T, F, U = TV.T, TV.F, TV.U


def fs(**fields):
    events = fields.pop("events", [])
    therapy = fields.pop("therapy", Status.VALUE if events else Status.NOT_MENTIONED)
    lines = fields.pop("lines", None)
    meta = fields.pop("meta", {"therapy_verified": True})
    return FactSheet(patient_id="X", fields={k: (v if isinstance(v, Fact) else
                                                Fact(status=Status.VALUE, value=v, verified=True))
                                             for k, v in fields.items()},
                     events=events, therapy_status=therapy, lines_of_therapy=lines, reader_meta=meta)


def A(**kw):
    kw.setdefault("id", "a")
    return Atom(**kw)


# ── Kleene truth tables ─────────────────────────────────────────────────────
@pytest.mark.parametrize("a,b,and_,or_", [
    (T, T, T, T), (T, F, F, T), (T, U, U, T), (F, F, F, F), (F, U, F, U), (U, U, U, U)])
def test_kleene_and_or(a, b, and_, or_):
    assert t_and(a, b) is and_ and t_and(b, a) is and_
    assert t_or(a, b) is or_ and t_or(b, a) is or_


def test_kleene_not_implies():
    assert t_not(U) is U and t_not(T) is F
    assert t_implies(F, U) is T and t_implies(T, U) is U and t_implies(U, T) is T and t_implies(T, F) is F


# ── interval comparison ─────────────────────────────────────────────────────
@pytest.mark.parametrize("lo,hi,op,v,exp", [
    (1, 1, "<=", 1, T), (2, 2, "<=", 1, F), (0, 2, "<=", 1, U),
    (1, 3, "<", 1, F), (0.5, 3, "<", 1, U), (1, 3, ">=", 1, T), (0, 0.9, ">=", 1, F),
    (5, 5, "==", 5, T), (4, 6, "==", 5, U), (6, 7, "!=", 5, T)])
def test_cmp_interval(lo, hi, op, v, exp):
    assert cmp_interval(lo, hi, op, v) is exp


# ── CMP / IN / IS ───────────────────────────────────────────────────────────
def test_cmp_ecog_point():
    assert evaluate_atom(A(type="CMP", field="ecog", op="<=", value=1), fs(ecog=1)).value is T
    assert evaluate_atom(A(type="CMP", field="ecog", op="<=", value=1), fs(ecog=2)).value is F


def test_cmp_not_mentioned_is_unknown_for_required_measurement():
    r = evaluate_atom(A(type="CMP", field="fev1_pct", op=">=", value=40), fs())
    assert r.value is U and not r.verified


def test_kps_seen_through_ecog_criterion():
    # KPS 70 => ECOG 1  -> satisfies ECOG<=1 ; KPS 60 => ECOG 2 -> fails ECOG<=1
    assert evaluate_atom(A(type="CMP", field="ecog", op="<=", value=1), fs(kps=70)).value is T
    assert evaluate_atom(A(type="CMP", field="ecog", op="<=", value=1), fs(kps=60)).value is F
    assert kps_to_ecog(80, 80) == (1.0, 1.0)


def test_ecog_seen_through_kps_criterion_is_interval():
    # ECOG 1 => KPS 70-80: KPS>=70 true, KPS>=80 unknown
    assert evaluate_atom(A(type="CMP", field="kps", op=">=", value=70), fs(ecog=1)).value is T
    assert evaluate_atom(A(type="CMP", field="kps", op=">=", value=80), fs(ecog=1)).value is U


def test_approx_conversion_near_threshold_not_verified():
    # KPS 70 vs KPS>=70 is exact; ECOG1 -> KPS [70,80] vs >=70: approx & near => unverified
    r = evaluate_atom(A(type="CMP", field="kps", op=">=", value=70), fs(ecog=1))
    assert r.value is T and not r.verified


def test_xuln_conversion():
    # bilirubin 0.8 mg/dL (ULN 1.2) => 0.67 xULN <= 1.5 : T, far from threshold => verified
    r = evaluate_atom(A(type="CMP", field="bilirubin_xuln", op="<=", value=1.5), fs(bilirubin_mg_dl=0.8))
    assert r.value is T and r.verified and r.approx
    # 1.75 mg/dL => 1.46 xULN, within 10% of 1.5 => not verified
    r = evaluate_atom(A(type="CMP", field="bilirubin_xuln", op="<=", value=1.5), fs(bilirubin_mg_dl=1.75))
    assert r.value is T and not r.verified


@pytest.mark.parametrize("patient,allowed,exp", [
    ("IIIB", ["IIIB", "IV"], T), ("IV", ["IIIB", "IV"], T), ("IIIA", ["IIIB", "IV"], F),
    ("IIIB", ["III"], T), ("IVA", ["IV"], T), ("IV", ["IVA"], U), ("IV", ["IVA", "IVB"], T),
    ("IA2", ["I"], T), ("T1N0", ["IA"], T), ("Stage IIIB", ["IIIB"], T)])
def test_stage_subsumption(patient, allowed, exp):
    assert stage_in(patient, allowed) is exp


def test_stage_list_inclusion_atom():
    a = A(type="IN", field="stage_group", values=["IIIB", "IV"])
    assert evaluate_atom(a, fs(stage_group="IV")).value is T


def test_tnm_prefix():
    a = A(type="IN", field="tnm_m", values=["M1"])
    assert evaluate_atom(a, fs(tnm_m="M1a")).value is T
    a2 = A(type="IN", field="tnm_m", values=["M1a"])
    assert evaluate_atom(a2, fs(tnm_m="M1")).value is U


def test_enum_in():
    a = A(type="IN", field="histology", values=["adenocarcinoma", "large_cell", "nos"])
    assert evaluate_atom(a, fs(histology="squamous")).value is F


def test_is_bool():
    assert evaluate_atom(A(type="IS", field="malignant_effusion", value=True),
                         fs(malignant_effusion=True)).value is T


# ── closed-world pertinent negatives ────────────────────────────────────────
def test_pertinent_negative_assumed_absent():
    r = evaluate_atom(A(type="IS", field="active_infection", value=True, polarity="exclusion"), fs())
    assert r.value is F and r.assumed and not r.verified


def test_negated_bool_is_verified_false():
    r = evaluate_atom(A(type="IS", field="active_infection", value=True),
                      fs(active_infection=Fact(status=Status.NEGATED, verified=True)))
    assert r.value is F and r.verified and not r.assumed


def test_brain_mets_default_none():
    a = A(type="IN", field="brain_mets", values=["untreated_or_symptomatic"], polarity="exclusion")
    assert evaluate_atom(a, fs()).value is F


def test_recent_mi_when_no_mi_history():
    a = A(type="CMP", field="mi_months_ago", op="<=", value=6, polarity="exclusion")
    r = evaluate_atom(a, fs())
    assert r.value is F and r.assumed


def test_recent_mi_interval():
    a = A(type="CMP", field="mi_months_ago", op="<=", value=6, polarity="exclusion")
    assert evaluate_atom(a, fs(mi_history=True, mi_months_ago=[0, 6])).value is T
    assert evaluate_atom(a, fs(mi_history=True, mi_months_ago=[6.01, math.inf])).value is F


# ── therapy: HAS / WITHIN / SINCE / COUNT (temporal + quantified) ──────────
def ev(cls, months=None, agents=(), verified=True, **kw):
    return TherapyEvent(cls=cls, months_ago=months, agents=list(agents), verified=verified, **kw)


def test_has_prior_chemo():
    a = A(type="HAS", filter=EventFilter(cls=["chemo"]))
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3])])).value is T
    assert evaluate_atom(a, fs(events=[ev("tki", [1, 3])])).value is F


def test_has_with_no_therapy_statement_is_unknown():
    a = A(type="HAS", filter=EventFilter(cls=["chemo"]))
    assert evaluate_atom(a, fs()).value is U


def test_has_with_negated_history_is_false_verified():
    a = A(type="HAS", filter=EventFilter(cls=["chemo"]))
    r = evaluate_atom(a, fs(therapy=Status.NEGATED))
    assert r.value is F and r.verified


@pytest.mark.parametrize("months,window,exp", [
    ([0, 1], 0.46, U),      # "within 1 month" vs "within 14 days" -> cannot tell
    ([1, 3], 0.92, F),      # 1-3 months ago vs "within 4 weeks" -> washout satisfied
    ([0, 1], 3.0, T),       # within 1 month vs "within 3 months" -> inside window
    ([6, math.inf], 6.0, F)])
def test_within_washout_intervals(months, window, exp):
    a = A(type="WITHIN", filter=EventFilter(cls=["chemo"]), months=window, polarity="exclusion")
    assert evaluate_atom(a, fs(events=[ev("chemo", months)])).value is exp


def test_since_is_negation_of_within():
    a = A(type="SINCE", filter=EventFilter(cls=["radio"]), months=0.92)
    assert evaluate_atom(a, fs(events=[ev("radio", [1, 3])])).value is T


def test_within_ongoing_therapy():
    a = A(type="WITHIN", filter=EventFilter(cls=["tki"]), months=0.5)
    assert evaluate_atom(a, fs(events=[ev("tki", None, ongoing=True)])).value is T


def test_within_unknown_timing_is_unknown():
    a = A(type="WITHIN", filter=EventFilter(cls=["chemo"]), months=1)
    assert evaluate_atom(a, fs(events=[ev("chemo", None)])).value is U


def test_count_more_than_one_prior_regimen():
    a = A(type="COUNT", filter=EventFilter(cls=["chemo"]), op=">", k=1, polarity="exclusion")
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3])])).value is F
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3]), ev("chemo", [6, math.inf])])).value is T


def test_count_uses_explicit_lines():
    a = A(type="COUNT", op=">=", k=1)
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3])], lines=[1, 1],
                               meta={"therapy_verified": True, "lines_verified": True})).value is T


def test_count_with_negated_history_is_zero():
    a = A(type="COUNT", op=">=", k=1)
    assert evaluate_atom(a, fs(therapy=Status.NEGATED)).value is F


def test_agent_filter_unknown_agent():
    a = A(type="HAS", filter=EventFilter(cls=["chemo"], agents=["platinum"]))
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3])])).value is U
    assert evaluate_atom(a, fs(events=[ev("chemo", [1, 3], agents=["carboplatin platinum"])])).value is T


def test_thoracic_radiation_filter():
    a = A(type="HAS", filter=EventFilter(cls=["radio"], thoracic=True))
    assert evaluate_atom(a, fs(events=[ev("radio", [1, 3])])).value is U
    assert evaluate_atom(a, fs(events=[ev("radio", [1, 3], thoracic=False)])).value is F


# ── conditionals / composition ──────────────────────────────────────────────
def iiib_requires_effusion():
    return A(type="IF", children=[
        A(id="c", type="IN", field="stage_group", values=["IIIB"]),
        A(id="d", type="IS", field="malignant_effusion", value=True)])


def test_conditional_iiib_with_effusion():
    a = iiib_requires_effusion()
    assert evaluate_atom(a, fs(stage_group="IIIB", malignant_effusion=True)).value is T
    assert evaluate_atom(a, fs(stage_group="IIIB", malignant_effusion=False)).value is F
    assert evaluate_atom(a, fs(stage_group="IV")).value is T          # antecedent false
    assert evaluate_atom(a, fs(stage_group="IIIB")).value is U        # effusion unknown


def test_any_all():
    anyof = A(type="ANY", children=[A(id="x", type="CMP", field="ecog", op="<=", value=1),
                                    A(id="y", type="CMP", field="kps", op=">=", value=70)])
    assert evaluate_atom(anyof, fs(kps=70)).value is T
    allof = A(type="ALL", children=[A(id="x", type="CMP", field="ecog", op="<=", value=1),
                                    A(id="y", type="CMP", field="fev1_pct", op=">=", value=40)])
    assert evaluate_atom(allof, fs(ecog=1)).value is U
    assert evaluate_atom(allof, fs(ecog=2)).value is F


def test_downgraded_atom_never_verified():
    a = A(type="CMP", field="ecog", op="<=", value=1, downgraded=True)
    r = evaluate_atom(a, fs(ecog=3))
    assert r.value is F and not r.verified


def test_unverified_fact_gives_unverified_verdict():
    r = evaluate_atom(A(type="CMP", field="ecog", op="<=", value=1),
                      fs(ecog=Fact(status=Status.VALUE, value=3, verified=False)))
    assert r.value is F and not r.verified


def test_judge_and_unscreenable():
    assert evaluate_atom(A(type="JUDGE", text="no clinically significant cardiac disease"), fs()).value is U
    r = evaluate_atom(A(type="UNSCREENABLE", text="able to give informed consent"), fs())
    assert r.unscreenable


# ── type checker ────────────────────────────────────────────────────────────
def test_type_checker_rejects_bad_atoms():
    assert type_errors(A(type="CMP", field="nonexistent", op="<", value=1))
    assert type_errors(A(type="CMP", field="ecog", op="~", value=1))
    assert type_errors(A(type="IN", field="histology", values=["squamous-ish"]))
    assert type_errors(A(type="WITHIN", filter=EventFilter(cls=["chemo"])))
    assert type_errors(A(type="IF", children=[A(id="z", type="IS", field="pregnant", value=True)]))
    assert not type_errors(A(type="CMP", field="bilirubin_xuln", op="<=", value=1.5))


def test_program_duplicate_ids():
    p = TrialProgram(trial_id="t", atoms=[A(type="JUDGE", text="x"), A(type="JUDGE", text="y")])
    assert "duplicate atom ids" in program_errors(p)


def test_systemic_filter_covers_all_systemic_classes():
    a = A(type="HAS", filter=EventFilter(cls=["systemic"]), polarity="exclusion")
    assert evaluate_atom(a, fs(events=[ev("chemo", [6, math.inf])])).value is T
    assert evaluate_atom(a, fs(events=[ev("io", [1, 3])])).value is T
    assert evaluate_atom(a, fs(events=[ev("radio", [1, 3])])).value is F
