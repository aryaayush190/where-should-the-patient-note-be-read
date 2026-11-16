"""
splitmatch/groq_pool.py  (copied from INDICON src/groq_pool.py; keys path re-rooted)
----------------
Round-robin Groq API key pool with per-key cooldown tracking.

Keys are loaded from a plain-text file (one key per line).
File location: groq_keys.txt in the project root (gitignored).

Usage:
    from src.groq_pool import GroqPool

    pool = GroqPool()                          # loads groq_keys.txt
    client = pool.get_client()                 # next available Groq client
    pool.mark_rate_limited(key)                # call on 429
    pool.mark_success(key)                     # optional, resets cooldown early

Design:
    - Round-robin across all loaded keys
    - On 429: key enters COOLDOWN_SECONDS cooldown, next key tried
    - If ALL keys are cooling down: raises GroqPoolExhausted immediately
      (fail-fast — no silent hang)
    - Thread-safe via threading.Lock (Gradio runs handlers in threads)
"""

import os
import time
import threading
from pathlib import Path
from groq import Groq


# How long a rate-limited key sits out before being retried (seconds)
COOLDOWN_SECONDS = 60

# (key, model) pairs that a key's organisation cannot serve (403 blocked / 413 TPM cap)
_BAD_KEY_MODEL: set[tuple[str, str]] = set()

# Default location of the keys file relative to project root
DEFAULT_KEYS_FILE = Path(__file__).resolve().parent.parent / "groq_keys.txt"  # TELEMED_PERCOM/groq_keys.txt


class GroqPoolExhausted(Exception):
    """Raised when every key in the pool is currently rate-limited."""
    pass


class GroqPool:
    """
    Thread-safe round-robin pool of Groq API keys.

    Instantiate once at module level (or pass around as a singleton).
    Each call to get_client() returns a (key, Groq_client) tuple.
    Call mark_rate_limited(key) on a 429 error.
    """

    def __init__(self, keys_file: str | Path | None = None):
        path = Path(keys_file) if keys_file else DEFAULT_KEYS_FILE

        if not path.exists():
            raise FileNotFoundError(
                f"Groq keys file not found: {path}\n"
                f"Create it with one Groq API key per line.\n"
                f"Example:\n  gsk_aaaa...\n  gsk_bbbb...\n  gsk_cccc..."
            )

        raw = path.read_text(encoding="utf-8").strip().splitlines()
        self._keys = [
            line.strip()
            for line in raw
            if line.strip() and not line.strip().startswith("#")
        ]

        if not self._keys:
            raise ValueError(f"No valid keys found in {path}")

        # Validate format — Groq keys always start with gsk_
        invalid = [k for k in self._keys if not k.startswith("gsk_")]
        if invalid:
            raise ValueError(
                f"{len(invalid)} key(s) in {path} don't look like Groq keys "
                f"(expected 'gsk_...'): {[k[:12]+'...' for k in invalid]}"
            )

        self._lock = threading.Lock()
        self._index = 0                      # next key to try
        self._cooldowns: dict[str, float] = {}  # key → time when cooldown expires

        print(f"[GroqPool] Loaded {len(self._keys)} key(s) from {path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_client(self) -> tuple[str, Groq]:
        """
        Return the next available (key, Groq client) in round-robin order.

        Raises GroqPoolExhausted if every key is currently in cooldown.
        """
        with self._lock:
            now = time.monotonic()
            available = [
                k for k in self._keys
                if now >= self._cooldowns.get(k, 0)
            ]

            if not available:
                wait_times = {
                    k: round(self._cooldowns[k] - now, 1)
                    for k in self._keys
                    if k in self._cooldowns
                }
                shortest = min(wait_times.values()) if wait_times else 0
                raise GroqPoolExhausted(
                    f"All {len(self._keys)} Groq API keys are rate-limited.\n"
                    f"Shortest cooldown remaining: {shortest}s\n"
                    f"Solutions:\n"
                    f"  1. Add more keys to groq_keys.txt\n"
                    f"  2. Wait {shortest}s and retry\n"
                    f"  3. Reduce evaluation batch size"
                )

            # Pick next available key in round-robin order
            # Start from _index, wrap around
            n = len(self._keys)
            for offset in range(n):
                candidate = self._keys[(self._index + offset) % n]
                if candidate in available:
                    self._index = (self._keys.index(candidate) + 1) % n
                    return candidate, Groq(api_key=candidate)

            # Should never reach here
            raise GroqPoolExhausted("No available key found (internal error)")

    def mark_rate_limited(self, key: str) -> None:
        """
        Put a key into cooldown after receiving a 429 response.
        Call this in the except block when Groq raises RateLimitError.
        """
        with self._lock:
            expires_at = time.monotonic() + COOLDOWN_SECONDS
            self._cooldowns[key] = expires_at
            remaining = [
                k for k in self._keys
                if time.monotonic() >= self._cooldowns.get(k, 0)
            ]
            print(
                f"[GroqPool] Key {key[:16]}... rate-limited. "
                f"Cooldown: {COOLDOWN_SECONDS}s. "
                f"Available keys: {len(remaining)}/{len(self._keys)}"
            )

    def seconds_until_available(self) -> float:
        """Seconds until at least one key leaves cooldown (0 if one is free now)."""
        with self._lock:
            now = time.monotonic()
            remaining = [self._cooldowns.get(k, 0) - now for k in self._keys]
            free = [r for r in remaining if r <= 0]
            if free:
                return 0.0
            return max(0.0, min(remaining)) if remaining else 0.0

    def mark_dead(self, key: str, cooldown: float = 3600.0) -> None:
        """
        Quarantine a key that returned an auth error (401 / invalid key) for a
        long cooldown so the round-robin skips it, without removing it outright
        (a key can be re-enabled by the provider). Prints once per quarantine.
        """
        with self._lock:
            self._cooldowns[key] = time.monotonic() + cooldown
            alive = sum(
                1 for k in self._keys
                if time.monotonic() >= self._cooldowns.get(k, 0)
            )
            print(
                f"[GroqPool] Key {key[:16]}... rejected (401/invalid) — "
                f"quarantined for {int(cooldown)}s. Usable keys: {alive}/{len(self._keys)}"
            )

    def mark_success(self, key: str) -> None:
        """
        Clear a key's cooldown after a successful call.
        Optional — cooldowns expire automatically after COOLDOWN_SECONDS.
        """
        with self._lock:
            self._cooldowns.pop(key, None)

    def status(self) -> dict:
        """Return pool health summary — useful for logging and UI display."""
        with self._lock:
            now = time.monotonic()
            return {
                "total_keys":     len(self._keys),
                "available_keys": sum(
                    1 for k in self._keys
                    if now >= self._cooldowns.get(k, 0)
                ),
                "cooling_down":   sum(
                    1 for k in self._keys
                    if now < self._cooldowns.get(k, 0)
                ),
                "cooldown_secs":  COOLDOWN_SECONDS,
            }

    def __len__(self) -> int:
        return len(self._keys)


# ------------------------------------------------------------------
# Module-level singleton — imported by app.py and ensemble agent
# ------------------------------------------------------------------
# Instantiated lazily on first use so missing groq_keys.txt doesn't
# crash the app at import time if the user isn't using the pool.

_pool_instance: GroqPool | None = None
_pool_lock = threading.Lock()


def get_pool(keys_file: str | Path | None = None) -> GroqPool:
    """
    Return the module-level GroqPool singleton, creating it on first call.
    Thread-safe — safe to call from multiple Gradio handler threads.
    """
    global _pool_instance
    if _pool_instance is None:
        with _pool_lock:
            if _pool_instance is None:          # double-checked locking
                _pool_instance = GroqPool(keys_file)
    return _pool_instance


def is_pool_available(keys_file: str | Path | None = None) -> bool:
    """
    True if a usable groq_keys.txt exists (and loads cleanly) — lets call
    sites fall back to the original single-key behavior instead of crashing
    when no pool is configured.
    """
    try:
        get_pool(keys_file)
        return True
    except (FileNotFoundError, ValueError):
        return False


def call_groq_with_pool(
    model_id: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1000,
    extra_params: dict | None = None,
    keys_file: str | Path | None = None,
) -> str:
    """
    Convenience wrapper: call a Groq model using the pool,
    automatically retrying with the next key on 429.

    Returns the response text.
    Raises GroqPoolExhausted if no keys are available.
    Raises other exceptions (model error, network error) immediately.

    A 401 / invalid-API-key on a specific key is treated like a rate-limit for
    that one key (cooled down and skipped) and the NEXT key is tried, rather
    than surfacing the auth error to the caller — a single dead key in the pool
    must not break an otherwise-working validation/ensemble call. If every key
    is dead/rate-limited we fall through to GroqPoolExhausted.
    """
    from groq import RateLimitError
    try:
        from groq import AuthenticationError
    except Exception:  # older/newer groq versions
        AuthenticationError = ()

    pool = get_pool(keys_file)
    extra = extra_params or {}

    # When every key is temporarily rate-limited, WAIT for the shortest
    # cooldown and retry rather than failing the call — free-tier 429s are
    # short (~60s) and transient, so an eval should slow down, not error out.
    # Bounded so a genuinely dead pool still surfaces eventually.
    MAX_TOTAL_WAIT = float(os.environ.get("GROQ_POOL_MAX_WAIT", "900"))
    waited = 0.0

    def _is_auth_error(exc) -> bool:
        if AuthenticationError and isinstance(exc, AuthenticationError):
            return True
        s = str(exc).lower()
        return "401" in s or "invalid_api_key" in s or "invalid api key" in s

    tried = set()
    while True:
        try:
            key, client = pool.get_client()
        except GroqPoolExhausted:
            wait_s = pool.seconds_until_available() + 0.5
            if waited + wait_s > MAX_TOTAL_WAIT:
                raise
            time.sleep(wait_s)
            waited += wait_s
            tried.clear()
            continue

        if (key, model_id) in _BAD_KEY_MODEL:
            # this key's organisation cannot serve this model/request size
            tried.add(key)
            if len({k for k, m in _BAD_KEY_MODEL if m == model_id}) >= len(pool):
                raise RuntimeError(f"no key in the pool can serve {model_id}")
            if len(tried) >= len(pool):
                tried.clear()
                time.sleep(1.0)
            continue

        if key in tried:
            # Been around the whole pool once this cycle with no success — the
            # available keys all just rate-limited. Wait for a cooldown, reset.
            wait_s = pool.seconds_until_available() + 0.5
            if waited + wait_s > MAX_TOTAL_WAIT:
                raise GroqPoolExhausted(
                    f"All Groq keys rate-limited beyond max wait. Pool: {pool.status()}"
                )
            time.sleep(wait_s)
            waited += wait_s
            tried.clear()
            continue

        tried.add(key)

        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **extra,
            )
            pool.mark_success(key)

            text = response.choices[0].message.content or ""
            # Strip reasoning tags defensively
            import re
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
            return text.strip()

        except RateLimitError:
            pool.mark_rate_limited(key)
            # Loop again — get_client() will skip this key until cooldown expires
            continue

        except Exception as e:
            if _is_auth_error(e):
                # Dead/invalid key — quarantine it (long cooldown) and try the
                # next key instead of failing the whole call.
                pool.mark_dead(key)
                continue
            status = getattr(e, "status_code", None)
            msg = str(e).lower()
            if status == 403 and "blocked" in msg:
                # model disabled for this key's organisation -> never use this pair again
                _BAD_KEY_MODEL.add((key, model_id))
                continue
            if status == 413 and "tokens per minute" in msg:
                # this organisation's per-request TPM cap is too small for this request;
                # other organisations in the pool may have higher caps
                _BAD_KEY_MODEL.add((key, model_id))
                continue
            # Model not found, network error, etc. — don't retry, raise
            raise
