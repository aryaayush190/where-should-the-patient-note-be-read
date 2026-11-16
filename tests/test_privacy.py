"""The privacy guard must fail closed, and the post-hoc audit must catch leaks."""
import pytest

from splitmatch import llm
from splitmatch.llm import REGISTRY, Channel, PrivacyViolation, guard
from splitmatch.privacy import audit

NOTE = ("A 61-year-old man with stage IV adenocarcinoma. He has an ECOG performance "
        "status of 1. He previously received carboplatin and pemetrexed three months ago.")
REGISTRY.register(NOTE)


def test_guard_blocks_private_sentence_on_cloud_channels():
    for ch in (Channel.CLOUD_PUBLIC, Channel.CLOUD_FACT):
        with pytest.raises(PrivacyViolation):
            guard(ch, "Criterion: ECOG 0-1. Note: He has an ECOG performance status of 1.")


def test_guard_blocks_patient_ids():
    with pytest.raises(PrivacyViolation):
        guard(Channel.CLOUD_FACT, "fact for P0007: ecog=1")


def test_guard_allows_minimised_fact():
    guard(Channel.CLOUD_FACT, "Criterion: ECOG 0-1 required. Fact: performance status ECOG = 1.")


def test_guard_ignores_edge_local():
    guard(Channel.EDGE_LOCAL, NOTE)


def test_edge_proxy_forbidden_in_deploy(monkeypatch):
    monkeypatch.setenv("SPLITMATCH_MODE", "deploy")
    with pytest.raises(PrivacyViolation):
        guard(Channel.EDGE_PROXY, NOTE)
    monkeypatch.setenv("SPLITMATCH_MODE", "dev")
    guard(Channel.EDGE_PROXY, NOTE)


def test_call_raises_before_any_io(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network must not be reached")
    monkeypatch.setattr(llm, "_groq", boom)
    with pytest.raises(PrivacyViolation):
        llm.call(Channel.CLOUD_FACT, [{"role": "user", "content": NOTE}], use_cache=False)


def test_audit_counts_leaks_and_k_anonymity():
    recs = [
        {"channel": "cloud_fact", "payload": "Fact: ECOG = 1", "local_ref": "P0001__NCT1",
         "disclosed_fields": ["ecog"]},
        {"channel": "cloud_fact", "payload": "Fact: ECOG = 1", "local_ref": "P0002__NCT1",
         "disclosed_fields": ["ecog"]},
        {"channel": "cloud_public", "payload": "He has an ECOG performance status of 1.",
         "local_ref": ""},
        {"channel": "baseline_cloud", "payload_chars": 900},
    ]
    a = audit(recs)
    assert a["raw_egress_violations"] == 1
    assert a["k_anonymity"]["min"] == 2
    assert a["disclosed_fields_per_escalated_pair"]["median"] == 1
    assert a["baseline_egress_chars"] == 900


def test_structurer_drops_negation_with_irrelevant_quote():
    from splitmatch.structurer import build_factsheet
    note = "He has received no prior systemic or radiation therapy. ECOG performance status of 1."
    slm = {"facts": {"malignant_effusion": {"v": False, "q": "no prior systemic or radiation therapy"},
                     "active_infection": {"v": False, "q": "no prior systemic or radiation therapy"},
                     "ecog": {"v": 1, "q": "ECOG performance status of 1"}}, "therapies": []}
    rx = {"fields": {"ecog": [1.0, 1.0]}, "events": [], "therapy_negated": True}
    fs = build_factsheet("X", note, slm, rx, reader="edge_local")
    assert "malignant_effusion" not in fs.fields and "active_infection" not in fs.fields
    assert fs.fields["ecog"].verified
