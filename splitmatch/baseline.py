"""
splitmatch/baseline.py — the INDICON zero-shot baseline, replicated exactly
(prompt text, 4000-char criteria truncation, temperature 0, max_tokens 1000,
reasoning_effort "low" for gpt-oss, identical vote parser with the conservative
"Not Eligible" default). Used for stress variants (cloud) and as the edge-SLM
end-to-end baseline (local model, same prompt).
"""
from __future__ import annotations

import json
import re

from . import llm
from .llm import Channel

BASELINE_SYSTEM = (
    "You are a clinical trial eligibility assistant for non-small-cell lung "
    "cancer (NSCLC). Decide whether the patient meets EVERY inclusion criterion "
    "and violates NO exclusion criterion. Respond ONLY with a JSON object: "
    '{"prediction": "Eligible" | "Not Eligible", "confidence": <0..1>, '
    '"reasoning": "<one sentence>"}.'
)


def user_block(note: str, inclusion: str, exclusion: str) -> str:
    return (f"PATIENT PROFILE:\n{note}\n\n"
            f"TRIAL INCLUSION CRITERIA:\n{inclusion[:4000]}\n\n"
            f"TRIAL EXCLUSION CRITERIA:\n{exclusion[:4000]}\n"
            "\nDecide eligibility. Respond in the required JSON format.")


def parse_vote(raw: str):
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL)
    text = re.sub(r"```json|```", "", text).strip()
    try:
        obj = json.loads(text)
        return obj.get("prediction", "Not Eligible"), max(0.0, min(1.0, float(obj.get("confidence", 0.5))))
    except Exception:
        pass
    m = re.search(r'"?prediction"?\s*[:=]\s*"?\s*(not\s+eligible|ineligible|eligible)', text, re.I)
    if m:
        return ("Eligible" if m.group(1).lower() == "eligible" else "Not Eligible"), 0.5
    if re.search(r"\bnot\s+eligible\b|\bineligible\b", text, re.I):
        return "Not Eligible", 0.5
    if re.search(r"\beligible\b", text, re.I):
        return "Eligible", 0.5
    return None, 0.5


def zero_shot(note: str, inclusion: str, exclusion: str, channel: Channel, local_ref: str = "",
              run_id: str = "") -> dict:
    msgs = [{"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": user_block(note, inclusion, exclusion)}]
    if channel is Channel.EDGE_LOCAL:
        extra, model, mt = {"json": True, "num_ctx": 8192}, llm.EDGE_LOCAL_MODEL, 300
    else:
        extra, model, mt = {"reasoning_effort": "low"}, llm.CLOUD_PRIMARY, 1000
    rep = llm.call(channel, msgs, model=model, max_tokens=mt, extra=extra, run_id=run_id,
                   tag="zero_shot", local_ref=local_ref)
    pred, conf = parse_vote(rep.text)
    if pred is None:
        pred, conf = "Not Eligible", 0.5
    norm = "Eligible" if str(pred).strip().lower() == "eligible" else "Not Eligible"
    return {"prediction": norm, "confidence": conf, "latency_s": rep.meta.get("latency_s")}
