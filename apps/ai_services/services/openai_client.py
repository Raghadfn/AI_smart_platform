"""
عميل Hugging Face الموحد
Unified Hugging Face Inference client (official hf-inference provider,
wait_for_model + fast fallback models + multi-key quota rotation)
"""
from __future__ import annotations

import logging
import time

from django.conf import settings
from huggingface_hub import InferenceClient

from apps.ai_services.exceptions import HFNotConfiguredError, HFRateLimitExhaustedError
from apps.ai_services.services.hf_keys import (
    get_active_token,
    get_active_token_index,
    is_quota_or_rate_limit_error,
    load_hf_tokens,
    rotate_to_next_token,
)

logger = logging.getLogger(__name__)

_clients: dict[str, InferenceClient] = {}

HF_MAX_RETRIES = 3
HF_RETRY_BASE_SECONDS = 2.0


def _client_cache_key(token: str, provider: str) -> str:
    # Fingerprint token so rotation rebuilds the client without logging secrets.
    return f"{provider or 'auto'}:{token[:8]}:{len(token)}"


def _build_client(token: str) -> InferenceClient:
    provider = (getattr(settings, "HF_PROVIDER", None) or "auto").strip()
    cache_key = _client_cache_key(token, provider)
    if cache_key in _clients:
        return _clients[cache_key]

    kwargs = {
        "token": token,
        "timeout": float(getattr(settings, "HF_TIMEOUT", 120)),
        "headers": {"X-Wait-For-Model": "true"},  # wait_for_model=True
    }
    if provider and provider != "auto":
        kwargs["provider"] = provider
    try:
        client = InferenceClient(**kwargs)
    except Exception as exc:
        logger.warning("HF provider '%s' rejected (%s) — auto routing", provider, exc)
        kwargs.pop("provider", None)
        client = InferenceClient(**kwargs)
    _clients[cache_key] = client
    return client


def _get_client() -> InferenceClient:
    """عميل HF مع المزوّد الرسمي و wait_for_model=True"""
    tokens = load_hf_tokens()
    token = get_active_token(tokens)
    if not token:
        raise HFNotConfiguredError()
    return _build_client(token)


def get_hf_client() -> InferenceClient:
    return _get_client()


# توافق مع الاستدعاءات القديمة
def get_groq_client() -> InferenceClient:
    return _get_client()


def _models_chain() -> list[str]:
    primary = getattr(settings, "HF_MODEL", None) or "meta-llama/Meta-Llama-3-8B-Instruct"
    fallbacks = list(
        getattr(settings, "HF_FALLBACK_MODELS", None)
        or ["meta-llama/Llama-3.2-3B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"]
    )
    chain = [primary]
    for fb in fallbacks:
        if fb and fb not in chain:
            chain.append(fb)
    return chain


def _is_model_unavailable(exc: Exception) -> bool:
    """النموذج غير متاح لدى المزوّد — جرّب النموذج الاحتياطي مباشرة"""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    if status == 404:
        return True
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "model not supported",
            "not supported by provider",
            "doesn't support task",
            "does not support task",
            "404 client error",
            "not found for url",
            "model_not_found",
        )
    )


def _is_retriable(exc: Exception) -> bool:
    if is_quota_or_rate_limit_error(exc):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    if status in (429, 503, 502, 504):
        return True
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "503",
            "429",
            "model is currently loading",
            "model is busy",
            "this model is busy",
            "please try again later",
            "completion_error",
            "server_error",
            "rate limit",
            "too many requests",
            "overloaded",
            "temporarily unavailable",
            "service unavailable",
            "timeout",
        )
    )


def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> tuple[str, int]:
    """
    إرسال طلب محادثة إلى Hugging Face مع إعادة محاولة + نماذج احتياطية + تدوير مفاتيح
    Returns: (response_text, tokens_used)
    """
    tokens = load_hf_tokens()
    if not tokens:
        raise HFNotConfiguredError()

    safe_messages = list(messages)
    if response_format and safe_messages:
        if safe_messages[0].get("role") == "system":
            safe_messages[0] = {
                **safe_messages[0],
                "content": (
                    str(safe_messages[0].get("content") or "")
                    + "\n\nReturn a valid JSON object only. No markdown fences or commentary."
                ),
            }
        else:
            safe_messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Return a valid JSON object only. No markdown fences or commentary.",
                },
            )

    last_error: Exception | None = None
    client = _get_client()

    for model in _models_chain():
        tried_key_indices: set[int] = {get_active_token_index() % len(tokens)}
        attempt = 1
        while attempt <= HF_MAX_RETRIES:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=safe_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                used = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
                return text, used
            except Exception as exc:
                last_error = exc
                if _is_model_unavailable(exc):
                    logger.warning(
                        "HF model %s unavailable (%s) — trying fallback", model, exc
                    )
                    break  # النموذج الاحتياطي التالي فوراً

                if is_quota_or_rate_limit_error(exc) and len(tokens) > 1:
                    rotated = rotate_to_next_token(
                        tokens, tried_indices=tried_key_indices
                    )
                    if rotated:
                        new_token, idx = rotated
                        tried_key_indices.add(idx)
                        client = _build_client(new_token)
                        logger.warning(
                            "HF quota/rate-limit — immediate retry with key %d/%d",
                            idx + 1,
                            len(tokens),
                        )
                        continue

                if not _is_retriable(exc):
                    logger.error("HF chat_completion failed on %s: %s", model, exc)
                    raise

                if attempt < HF_MAX_RETRIES:
                    delay = HF_RETRY_BASE_SECONDS * attempt
                    logger.warning(
                        "HF %s busy (attempt %d/%d), sleeping %.1fs: %s",
                        model,
                        attempt,
                        HF_MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    attempt += 1
                else:
                    logger.warning("HF %s exhausted — trying fallback model", model)
                    break

    raise HFRateLimitExhaustedError() from last_error


def create_embedding(text: str) -> list[float]:
    """لا نستخدم embeddings خارجية حالياً — البحث النصي في RAG كافٍ"""
    raise NotImplementedError(
        "Embeddings are not configured. Use keyword RAG search."
    )
