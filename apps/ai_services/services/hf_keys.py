"""
Hugging Face API key rotation with quota / rate-limit failover.

Loads up to 4 tokens from Django settings or environment variables and
rotates to the next key when a call fails due to 429 / credit / quota errors.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Iterable

logger = logging.getLogger(__name__)

# Shared across requests in this process so a depleted key is skipped next time.
_lock = threading.Lock()
_active_index = 0


def _unique_preserve(tokens: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tokens:
        token = (raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def load_hf_tokens() -> list[str]:
    """
    Resolve Hugging Face tokens (max 4) from:
      1) Django settings.HF_TOKENS
      2) HF_TOKENS comma-separated env
      3) HF_TOKEN / HF_TOKEN_1 … HF_TOKEN_4
      4) Legacy HUGGINGFACEHUB_API_TOKEN / HUGGING_FACE_HUB_TOKEN
    """
    tokens: list[str] = []

    try:
        from django.conf import settings

        configured = getattr(settings, "HF_TOKENS", None)
        if configured:
            tokens.extend(configured)
    except Exception:
        pass

    if not tokens:
        csv = os.getenv("HF_TOKENS", "").strip()
        if csv:
            tokens.extend(part.strip() for part in csv.split(","))

    if not tokens:
        singles = [
            os.getenv("HF_TOKEN", ""),
            os.getenv("HF_TOKEN_1", ""),
            os.getenv("HF_TOKEN_2", ""),
            os.getenv("HF_TOKEN_3", ""),
            os.getenv("HF_TOKEN_4", ""),
            os.getenv("HUGGINGFACEHUB_API_TOKEN", ""),
            os.getenv("HUGGING_FACE_HUB_TOKEN", ""),
        ]
        tokens.extend(singles)

    return _unique_preserve(tokens)[:4]


def get_active_token_index() -> int:
    with _lock:
        return _active_index


def set_active_token_index(index: int) -> None:
    global _active_index
    with _lock:
        _active_index = max(0, index)


def get_active_token(tokens: list[str] | None = None) -> str:
    keys = tokens if tokens is not None else load_hf_tokens()
    if not keys:
        return ""
    with _lock:
        idx = _active_index % len(keys)
        return keys[idx]


def rotate_to_next_token(
    tokens: list[str] | None = None,
    *,
    tried_indices: set[int] | None = None,
) -> tuple[str, int] | None:
    """
    Advance to the next unused token.

    Returns (token, index) or None if every key was already tried.
    """
    keys = tokens if tokens is not None else load_hf_tokens()
    if not keys:
        return None

    global _active_index
    with _lock:
        n = len(keys)
        start = _active_index % n
        for offset in range(1, n + 1):
            idx = (start + offset) % n
            if tried_indices is not None and idx in tried_indices:
                continue
            _active_index = idx
            logger.warning(
                "HF API key rotated to index %d/%d due to quota/rate limit",
                idx + 1,
                n,
            )
            return keys[idx], idx
    return None


def http_status(exc: Exception) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    return None


def is_quota_or_rate_limit_error(exc: Exception) -> bool:
    """
    True for 429 / credit / quota / monthly limit style failures that warrant
    switching to the next Hugging Face API key immediately.
    """
    status = http_status(exc)
    if status == 429:
        return True
    if status == 402:  # Payment required / credits exhausted on some providers
        return True

    message = str(exc).lower()
    markers = (
        "429",
        "rate limit",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "quota",
        "exceeded your current quota",
        "quota exceeded",
        "credit",
        "credits",
        "out of credits",
        "insufficient credits",
        "insufficient_quota",
        "monthly limit",
        "usage limit",
        "limit exceeded",
        "payment required",
        "402",
        "budget",
    )
    return any(token in message for token in markers)
