"""
splitmatch/llm.py — every LLM call in the project goes through `call()`.

Why one gateway: the paper's privacy claims (raw patient-text egress = 0,
disclosed attributes per pair, offline coverage) are *measured from this log*,
not asserted. Each call is tagged with a CHANNEL that states which side of the
public/private boundary it belongs to:

  CLOUD_PUBLIC    cloud model, public trial text only           (guarded)
  CLOUD_FACT      cloud model, minimised single-criterion fact  (guarded)
  EDGE_LOCAL      on-device model via Ollama (any content)      (never leaves device)
  EDGE_PROXY      Groq model standing in for the edge model during development
                  — carries patient text; FORBIDDEN when SPLITMATCH_MODE=deploy
  BASELINE_CLOUD  a cloud baseline that sends the full patient note (egress counted)

Guard (fail-closed) for CLOUD_PUBLIC / CLOUD_FACT: the payload may not contain
any *private* narrative sentence (a registered patient-note sentence of >= 25
chars that does not also occur verbatim in the public trial corpus), nor a
patient / pair identifier. Violations raise PrivacyViolation — the call is
never made.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

from . import paths

# ── models ────────────────────────────────────────────────────────────────
CLOUD_PRIMARY = "openai/gpt-oss-120b"      # same primary as INDICON baselines
CLOUD_SECONDARY = "qwen/qwen3.8-27b"       # second-family compiler for agreement
EDGE_PROXY_MODEL = "openai/gpt-oss-20b"    # Groq stand-in for the edge tier (dev only)
EDGE_LOCAL_MODEL = os.environ.get("SPLITMATCH_EDGE_MODEL", "qwen3:4b-instruct")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


class Channel(str, Enum):
    CLOUD_PUBLIC = "cloud_public"
    CLOUD_FACT = "cloud_fact"
    EDGE_LOCAL = "edge_local"
    EDGE_PROXY = "edge_proxy"
    BASELINE_CLOUD = "baseline_cloud"


GUARDED = {Channel.CLOUD_PUBLIC, Channel.CLOUD_FACT}
PATIENT_ID_RE = re.compile(r"\bP\d{4}\b|\bP\d{4}__NCT\d{8}\b")


class PrivacyViolation(RuntimeError):
    pass


def mode() -> str:
    return os.environ.get("SPLITMATCH_MODE", "dev")


# ── privacy registry ──────────────────────────────────────────────────────
_SENT_SPLIT = re.compile(r"(?<=[.;:!?])\s+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


class PrivacyRegistry:
    """Holds the private sentences of every patient note loaded in-process."""

    def __init__(self) -> None:
        self._private: set[str] = set()
        self._public_blob: str | None = None
        self._lock = threading.Lock()

    def _public(self) -> str:
        if self._public_blob is None:
            parts = []
            for f in paths.TRIAL_FILES.values():
                for line in open(f, encoding="utf-8"):
                    t = json.loads(line)
                    parts.append(t.get("inclusion_criteria", ""))
                    parts.append(t.get("exclusion_criteria", ""))
            self._public_blob = _norm(" ".join(parts))
        return self._public_blob

    def register(self, narrative: str) -> None:
        pub = self._public()
        with self._lock:
            for s in _SENT_SPLIT.split(narrative or ""):
                n = _norm(s)
                if len(n) >= 25 and n not in pub:
                    self._private.add(n)

    def private_hits(self, payload: str) -> list[str]:
        p = _norm(payload)
        return [s for s in self._private if s in p]

    def __len__(self) -> int:
        return len(self._private)


REGISTRY = PrivacyRegistry()


def guard(channel: Channel, payload: str) -> None:
    if channel not in GUARDED:
        if channel is Channel.EDGE_PROXY and mode() == "deploy":
            raise PrivacyViolation("EDGE_PROXY (cloud stand-in) is forbidden in deploy mode")
        return
    if PATIENT_ID_RE.search(payload):
        raise PrivacyViolation(f"{channel.value}: patient/pair identifier in payload")
    hits = REGISTRY.private_hits(payload)
    if hits:
        raise PrivacyViolation(
            f"{channel.value}: {len(hits)} private narrative sentence(s) in payload, "
            f"e.g. {hits[0][:60]!r}")


# ── logging & cache ───────────────────────────────────────────────────────
_LOG_LOCK = threading.Lock()


def _log(rec: dict) -> None:
    with _LOG_LOCK, open(paths.LLM_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _cache_key(model: str, messages: list[dict], temperature: float,
               max_tokens: int, extra: dict) -> str:
    blob = json.dumps([model, messages, temperature, max_tokens, extra],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict | None:
    f = paths.LLM_CACHE / f"{key[:2]}" / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def _cache_put(key: str, rec: dict) -> None:
    d = paths.LLM_CACHE / key[:2]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{key}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")


# ── backends ──────────────────────────────────────────────────────────────
def _groq(model: str, messages: list[dict], temperature: float, max_tokens: int,
          extra: dict) -> tuple[str, dict]:
    from .groq_pool import call_groq_with_pool
    t0 = time.perf_counter()
    text = call_groq_with_pool(model, messages, temperature=temperature,
                               max_tokens=max_tokens, extra_params=extra)
    return text, {"latency_s": round(time.perf_counter() - t0, 3)}


def _ollama(model: str, messages: list[dict], temperature: float, max_tokens: int,
            extra: dict) -> tuple[str, dict]:
    opts = {"temperature": temperature, "num_predict": max_tokens,
            "num_ctx": int(extra.pop("num_ctx", 8192)), "seed": 0}
    if "num_thread" in extra:
        opts["num_thread"] = int(extra.pop("num_thread"))
    body = {"model": model, "messages": messages, "stream": False, "options": opts,
            "keep_alive": "30m"}
    if extra.pop("json", False):
        body["format"] = "json"
    t0 = time.perf_counter()
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=1800)
    r.raise_for_status()
    j = r.json()
    wall = time.perf_counter() - t0
    meta = {
        "latency_s": round(wall, 3),
        "prompt_tokens": j.get("prompt_eval_count"),
        "gen_tokens": j.get("eval_count"),
        "prompt_s": round((j.get("prompt_eval_duration") or 0) / 1e9, 3),
        "gen_s": round((j.get("eval_duration") or 0) / 1e9, 3),
        "load_s": round((j.get("load_duration") or 0) / 1e9, 3),
    }
    text = j.get("message", {}).get("content", "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text, meta


@dataclass
class Reply:
    text: str
    cached: bool
    meta: dict


def call(channel: Channel, messages: list[dict], *, model: str | None = None,
         temperature: float = 0.0, max_tokens: int = 1500, extra: dict | None = None,
         run_id: str = "", tag: str = "", disclosed_fields: list[str] | None = None,
         local_ref: str = "", use_cache: bool = True) -> Reply:
    """Make (or replay from cache) one LLM call through the privacy gateway.

    `local_ref` (e.g. a pair id) and `tag` are LOCAL bookkeeping written to the
    on-device log only — they are never part of the payload sent to a model."""
    extra = dict(extra or {})
    if model is None:
        model = {Channel.EDGE_LOCAL: EDGE_LOCAL_MODEL,
                 Channel.EDGE_PROXY: EDGE_PROXY_MODEL}.get(channel, CLOUD_PRIMARY)
    payload = "\n".join(str(m.get("content", "")) for m in messages)
    guard(channel, payload)                       # fail closed BEFORE any I/O

    key = _cache_key(model, messages, temperature, max_tokens, extra)
    rec_base = {
        "ts": time.time(), "channel": channel.value, "model": model, "run_id": run_id,
        "tag": tag, "local_ref": local_ref, "mode": mode(), "payload_chars": len(payload),
        "disclosed_fields": disclosed_fields or [], "cache_key": key,
    }
    if channel is not Channel.EDGE_LOCAL:
        # Everything that (would) leave the device is kept verbatim in the LOCAL log
        # so egress can be re-audited post hoc, independently of the guard.
        rec_base["payload"] = payload
    if use_cache:
        hit = _cache_get(key)
        if hit is not None:
            _log({**rec_base, "cached": True, "reply_chars": len(hit["text"])})
            return Reply(hit["text"], True, hit.get("meta", {}))

    backend = _ollama if channel is Channel.EDGE_LOCAL else _groq
    text, meta = backend(model, messages, temperature, max_tokens, dict(extra))
    if use_cache:
        _cache_put(key, {"text": text, "meta": meta, "model": model})
    _log({**rec_base, "cached": False, "reply_chars": len(text), **meta})
    return Reply(text, False, meta)


# ── JSON helper ───────────────────────────────────────────────────────────
def parse_json(text: str) -> Any:
    """Parse the first JSON object/array in a model reply (tolerates fences)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s = t.find(open_c)
        e = t.rfind(close_c)
        if s != -1 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in reply: {text[:200]!r}")
