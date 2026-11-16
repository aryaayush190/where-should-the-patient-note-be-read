"""
splitmatch/privacy.py — privacy accounting computed FROM THE CALL LOG.

Reported quantities (H2):
  raw_egress_sentences   private narrative sentences found in any cloud payload
                         (re-scanned post hoc; independent of the runtime guard)
  disclosed_fields       per pair: distinct fact fields sent to the cloud (CLOUD_FACT)
  k_anonymity            per CLOUD_FACT payload: how many distinct patients produced
                         an identical payload (higher = less identifying)
  baseline_egress_chars  characters of full notes sent by cloud baselines
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict

from . import paths
from .llm import REGISTRY, Channel

CLOUD_CHANNELS = {Channel.CLOUD_PUBLIC.value, Channel.CLOUD_FACT.value}


def load_log(run_id: str | None = None, path=None) -> list[dict]:
    p = path or paths.LLM_LOG
    if not p.exists():
        return []
    recs = [json.loads(l) for l in open(p, encoding="utf-8")]
    return [r for r in recs if run_id is None or r.get("run_id") == run_id]


def audit(records: list[dict], pair_patient: dict[str, str] | None = None) -> dict:
    """pair_patient maps local_ref (pair id) -> patient id for k-anonymity."""
    by_channel = defaultdict(int)
    raw_hits = []
    fields_per_pair: dict[str, set] = defaultdict(set)
    payload_patients: dict[str, set] = defaultdict(set)
    baseline_chars = 0
    for r in records:
        ch = r["channel"]
        by_channel[ch] += 1
        if ch in CLOUD_CHANNELS:
            hits = REGISTRY.private_hits(r.get("payload", ""))
            if hits:
                raw_hits.append({"local_ref": r.get("local_ref"), "channel": ch, "n": len(hits)})
        if ch == Channel.CLOUD_FACT.value:
            ref = r.get("local_ref", "")
            fields_per_pair[ref].update(r.get("disclosed_fields", []))
            pid = (pair_patient or {}).get(ref, ref.split("__")[0])
            payload_patients[r.get("payload", "")].add(pid)
        if ch == Channel.BASELINE_CLOUD.value:
            baseline_chars += r.get("payload_chars", 0)
    nf = [len(v) for v in fields_per_pair.values()]
    ks = [len(v) for v in payload_patients.values()]
    return {
        "calls_by_channel": dict(by_channel),
        "raw_egress_violations": len(raw_hits),
        "raw_egress_detail": raw_hits[:20],
        "pairs_with_cloud_fact_calls": len(fields_per_pair),
        "disclosed_fields_per_escalated_pair": {
            "median": statistics.median(nf) if nf else 0,
            "max": max(nf) if nf else 0,
        },
        "cloud_fact_payloads": len(ks),
        "k_anonymity": {"median": statistics.median(ks) if ks else None,
                        "min": min(ks) if ks else None,
                        "share_k_ge_2": (sum(k >= 2 for k in ks) / len(ks)) if ks else None},
        "baseline_egress_chars": baseline_chars,
    }
