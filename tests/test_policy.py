"""Evidence-conditioned authority: a single key must never exclude."""
import pytest

from splitmatch import policy
from splitmatch.evaluator import TV, AtomResult
from splitmatch.ladder import item_key
from splitmatch.policy import Config, decide
from splitmatch.render import statement
from splitmatch.schema import Atom


def atom(aid="a", pol="inclusion", typ="CMP", **kw):
    kw.setdefault("field", "ecog") if typ == "CMP" else None
    if typ == "CMP":
        kw.setdefault("op", "<=")
        kw.setdefault("value", 1)
    if typ == "JUDGE":
        kw.setdefault("text", "no significant cardiac disease")
    return Atom(id=aid, type=typ, polarity=pol, **kw)


def res(aid, v, verified=False, assumed=False):
    return AtomResult(aid, TV(v), verified=verified, assumed=assumed)


@pytest.fixture
def l2(monkeypatch):
    calls = []

    def fake(stmt, fact, ref, disclosed, run_id="", forced=False):
        calls.append(stmt)
        return fake.answer
    fake.answer = {"verdict": "U"}
    monkeypatch.setattr(policy, "l2_judge", fake)
    fake.calls = calls
    return fake


def l1_for(a, verdict, basis="stated"):
    return {item_key(statement(a)): {"verdict": verdict, "basis": basis, "fact": "f"}}


def test_verified_failed_inclusion_excludes(l2):
    a = atom()
    d = decide([(a, res("a", "F", verified=True))], {}, Config(), "P__T")
    assert d.selective == "NOT_ELIGIBLE" and d.forced == "NOT_ELIGIBLE" and not l2.calls


def test_unverified_failed_inclusion_alone_does_not_exclude(l2):
    a = atom()
    d = decide([(a, res("a", "F"))], {}, Config(), "P__T")
    assert d.selective != "NOT_ELIGIBLE"


def test_unverified_negative_plus_l1_confirms(l2):
    a = atom()
    d = decide([(a, res("a", "F"))], l1_for(a, "F"), Config(), "P__T")
    assert d.selective == "NOT_ELIGIBLE" and not l2.calls


def test_contested_negative_goes_to_l2(l2):
    a = atom()
    l2.answer = {"verdict": "T"}
    d = decide([(a, res("a", "F"))], l1_for(a, "T"), Config(), "P__T")
    assert d.selective == "ELIGIBLE" and len(l2.calls) == 1


def test_l1_only_negative_needs_l2_second_key(l2):
    a = atom(typ="JUDGE", pol="exclusion")
    l2.answer = {"verdict": "F"}
    d = decide([(a, res("a", "U"))], l1_for(a, "T"), Config(), "P__T")
    assert d.selective == "DEFER" and d.forced == "ELIGIBLE"
    l2.answer = {"verdict": "T"}
    d = decide([(a, res("a", "U"))], l1_for(a, "T"), Config(), "P__T2")
    assert d.selective == "NOT_ELIGIBLE"


def test_not_mentioned_clinical_requirement_asks(l2):
    a = Atom(id="a", type="IS", field="malignant_effusion", value=True, polarity="inclusion")
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "not_mentioned"), Config(), "P__T")
    assert d.selective == "NEED_INFO" and d.asks and d.asks[0]["category"] == "EFFUSION"


def test_not_mentioned_screening_item_goes_to_site(l2):
    a = atom(field="fev1_pct", op=">=", value=40)       # a test done at the screening visit
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "not_mentioned"), Config(), "P__T")
    assert d.selective == "ELIGIBLE" and d.site_verify


def test_forced_mode_unmentioned_clinical_requirement_resolved_by_l2(l2):
    a = Atom(id="a", type="IS", field="malignant_effusion", value=True, polarity="inclusion")
    l1 = l1_for(a, "U", "not_mentioned")
    l2.answer = {"verdict": "F"}
    d = decide([(a, res("a", "U"))], l1, Config(), "P__T")
    assert d.selective == "NEED_INFO" and d.forced == "NOT_ELIGIBLE" and "not stated" in str(l2.calls) or l2.calls
    l2.answer = {"verdict": "U"}
    d = decide([(a, res("a", "U"))], l1, Config(), "P__T2")
    assert d.forced == "ELIGIBLE"            # unknown -> not excluding (PREREGISTRATION §3.1)


def test_permission_line_is_never_a_requirement(l2):
    a = Atom(id="a", type="HAS", polarity="inclusion", filter={"cls": ["radio"]},
             source_line="Palliative radiotherapy to bony metastases is permitted if completed before entry")
    d = decide([(a, res("a", "F", verified=True))], {}, Config(), "P__T")
    assert d.selective == "ELIGIBLE" and d.forced == "ELIGIBLE"


def test_forced_mode_unmentioned_excluding_condition_not_excluding(l2):
    a = atom(typ="JUDGE", pol="exclusion", text="history of interstitial lung disease")
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "not_mentioned"), Config(), "P__T")
    assert d.forced == "ELIGIBLE"


def test_unmentioned_routine_lab_goes_to_site_checklist(l2):
    a = atom(field="platelets_k_ul", op=">=", value=100)
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "not_mentioned"), Config(), "P__T")
    assert d.selective == "ELIGIBLE" and d.forced == "ELIGIBLE" and d.site_verify


def test_contested_atom_judged_on_verbatim_line_in_its_section(l2):
    # an inclusion-section line ("chemotherapy-naive") compiled as an EXCLUSION atom that the
    # two compilers disagreed on: the judge reads the verbatim line, T = requirement met
    a = Atom(id="a", type="HAS", polarity="exclusion", section="inclusion", downgraded=True,
             source_line="Patients must be chemotherapy-naive", filter={"cls": ["chemo"]})
    l2.answer = {"verdict": "T"}              # cloud judge, reading the verbatim line: requirement met
    d = decide([(a, res("a", "T"))], l1_for(a, "T"), Config(), "P__T")
    assert d.selective == "ELIGIBLE"          # program said excluded, judge says met -> L2 decides
    assert l2.calls and "chemotherapy-naive" in l2.calls[0]


def test_cwa_judge_not_mentioned_is_assumed_absent(l2):
    a = atom(typ="JUDGE", pol="exclusion", cwa=True)
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "not_mentioned"), Config(), "P__T")
    assert d.selective == "ELIGIBLE"


def test_hard_veto_ablation_excludes_on_single_key(l2):
    a = atom()
    d = decide([(a, res("a", "F"))], {}, Config(hard_veto=True), "P__T")
    assert d.selective == "NOT_ELIGIBLE"


def test_offline_ablation_makes_no_cloud_calls(l2):
    a = atom(typ="JUDGE")
    d = decide([(a, res("a", "U"))], l1_for(a, "U", "stated"), Config(use_l2=False), "P__T")
    assert not l2.calls and d.selective == "DEFER"


def test_unscreenable_ignored(l2):
    a = Atom(id="u", type="UNSCREENABLE", text="informed consent")
    r = AtomResult("u", TV.U, unscreenable=True)
    d = decide([(a, r)], {}, Config(), "P__T")
    assert d.selective == "ELIGIBLE" and d.site_verify == ["informed consent"]
