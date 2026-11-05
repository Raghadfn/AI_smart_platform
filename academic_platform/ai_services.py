"""
خدمات الذكاء الاصطناعي المركزية للمنصة الأكاديمية
Centralized AI services via Hugging Face Inference API (Llama-3-8B-Instruct)

الاستخدام:
    from academic_platform.ai_services import AcademicAIService

    ai = AcademicAIService()
    result = ai.translate("Hello world", target_lang="ar")
    result = ai.summarize(lecture_text, length="medium")
    result = ai.ask_question("ما هي البرمجة؟", context=lecture_text)
    result = ai.generate_exam(lecture_text, types=["mcq", "true_false"], count=5)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

DEFAULT_HF_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
DEFAULT_HF_PROVIDER = "auto"
DEFAULT_HF_FALLBACK_MODELS = (
    "meta-llama/Llama-3.2-3B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
)
HF_MAX_RETRIES = 3          # محاولات لكل نموذج قبل الانتقال للنموذج الاحتياطي
HF_RETRY_BASE_SECONDS = 2.0
HF_WAIT_FOR_MODEL_HEADER = {"X-Wait-For-Model": "true"}  # wait_for_model=True

FRIENDLY_HF_BUSY_AR = (
    "المساعد يُعالج العديد من الطلبات حالياً. "
    "يرجى الانتظار قليلاً قبل طرح سؤالك التالي."
)
# توافق مع الأسماء القديمة
FRIENDLY_GROQ_BUSY_AR = FRIENDLY_HF_BUSY_AR

# تعليمات ثنائية اللغة الأساسية لكل موجهات النظام
BILINGUAL_SYSTEM_CORE = (
    "You are a bilingual academic assistant fluent in both Arabic and English. "
    "You must analyze the provided lecture context in whichever language it is written "
    "(Arabic or English) and respond accurately. "
    "Always reply in the same language the student uses to ask their question."
)

BILINGUAL_MIXED_CONTEXT_RULES = (
    "The lecture context may be Arabic-only, English-only, or mixed "
    "(Arabic explanations with English technical terms). "
    "Treat Arabic and English content as equally authoritative. "
    "Preserve English technical terms when they appear in Arabic explanations, "
    "and preserve Arabic terms when they appear in English explanations."
)

# تطابق كلمات عربية/لاتينية/أرقام دون قصّ الحروف العربية عبر مرشحات ASCII
_BILINGUAL_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*|"
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
    re.UNICODE,
)

_ARABIC_CHAR_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]",
    re.UNICODE,
)

_LATIN_CHAR_RE = re.compile(r"[A-Za-z]", re.UNICODE)

_BILINGUAL_STOP_WORDS = frozenset({
    # Arabic
    "ما", "ماذا", "هل", "من", "في", "على", "إلى", "الى", "عن", "هو", "هي",
    "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "الذين", "ان", "إن", "أن",
    "كان", "كانت", "يكون", "مع", "او", "أو", "ثم", "قد", "لم", "لن", "لا",
    "بين", "بعد", "قبل", "عند", "كيف", "لماذا", "متى", "اين", "أين",
    # English
    "the", "is", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "with", "as", "by", "from", "at", "be", "are", "was", "were", "been",
    "what", "how", "why", "when", "where", "who", "which", "this", "that",
    "these", "those", "it", "its", "do", "does", "did", "can", "could",
    "would", "should", "please", "explain", "about",
})

# أنواع اللغات المدعومة
SupportedLanguage = Literal["ar", "en"]
SummaryLength = Literal["short", "medium", "detailed"]
ExamType = Literal["mcq", "true_false", "essay"]
PrimaryLanguage = Literal["ar", "en", "mixed"]



@dataclass
class AIResponse:
    """استجابة موحدة لجميع خدمات الذكاء الاصطناعي"""

    success: bool
    data: dict[str, Any]
    tokens_used: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "success": self.success,
            "data": self.data,
            "tokens_used": self.tokens_used,
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class AcademicAIService:
    """
    خدمة الذكاء الاصطناعي الأكاديمية
    Academic AI service powered by Hugging Face (Meta-Llama-3-8B-Instruct)

    توفر:
    - ترجمة احترافية (عربي / إنجليزي)
    - تلخيص مرن (قصير / متوسط / مفصل)
    - إجابة على الأسئلة بناءً على سياق المحاضرة (RAG)
    - إنشاء أسئلة امتحان بصيغة JSON منظمة
    """

    api_key: str | None = None
    api_keys: list[str] | None = None
    model: str = DEFAULT_HF_MODEL
    provider: str = DEFAULT_HF_PROVIDER
    fallback_models: list[str] | None = None
    max_content_chars: int = 4500
    rag_max_chars: int = 3500
    _client: InferenceClient | None = field(default=None, repr=False)
    _fallback_clients: dict[str, InferenceClient] = field(
        default_factory=dict, repr=False
    )

    # أسماء اللغات بالعربية
    LANGUAGE_NAMES: dict[str, str] = field(
        default_factory=lambda: {
            "ar": "العربية",
            "en": "الإنجليزية",
        }
    )

    # تعليمات التلخيص حسب الطول (محايدة لغوياً؛ اللغة تُحدد ديناميكياً)
    SUMMARY_INSTRUCTIONS: dict[str, str] = field(
        default_factory=lambda: {
            "short": (
                "Write a very short summary (3-5 sentences) suitable for flashcards. "
                "Focus only on the most important points. "
                "اكتب ملخصاً قصيراً جداً (3-5 جمل) مناسباً للبطاقات التعليمية، "
                "وركّز على أهم النقاط فقط."
            ),
            "medium": (
                "Write a medium-length summary (two to three paragraphs) covering the main points clearly. "
                "اكتب ملخصاً متوسط الطول (فقرتان إلى ثلاث) يغطي النقاط الرئيسية بأسلوب واضح."
            ),
            "detailed": (
                "Write a detailed, well-structured summary with main and sub points and brief explanations. "
                "اكتب ملخصاً مفصلاً ومنظماً بنقاط رئيسية وفرعية مع شرح موجز لكل مفهوم."
            ),
        }
    )

    # مخطط JSON لأسئلة الامتحان (للواجهة الأمامية)
    EXAM_JSON_SCHEMA: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "exam_title": {"type": "string"},
                "total_questions": {"type": "integer"},
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "type": {"type": "string", "enum": ["mcq", "true_false", "essay"]},
                            "question": {"type": "string"},
                            "options": {
                                "type": ["array", "null"],
                                "items": {"type": "string"},
                            },
                            "correct_answer": {"type": "string"},
                            "explanation": {"type": "string"},
                            "points": {"type": "integer"},
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"],
                            },
                        },
                        "required": ["id", "type", "question", "correct_answer"],
                    },
                },
            },
            "required": ["exam_title", "total_questions", "questions"],
        }
    )

    def __post_init__(self) -> None:
        """تهيئة الإعدادات من Django أو متغيرات البيئة"""
        if self.api_keys is None:
            self.api_keys = self._resolve_api_keys()
        if self.api_key is None:
            from apps.ai_services.services.hf_keys import get_active_token

            self.api_key = get_active_token(self.api_keys) or (
                self.api_keys[0] if self.api_keys else ""
            )
        if not self.model or self.model in ("llama3-70b-8192", DEFAULT_HF_MODEL):
            self.model = self._resolve_setting("HF_MODEL", DEFAULT_HF_MODEL)
        if not self.provider or self.provider == DEFAULT_HF_PROVIDER:
            self.provider = self._resolve_setting("HF_PROVIDER", DEFAULT_HF_PROVIDER)
        if self.fallback_models is None:
            try:
                from django.conf import settings

                self.fallback_models = list(
                    getattr(settings, "HF_FALLBACK_MODELS", None)
                    or DEFAULT_HF_FALLBACK_MODELS
                )
            except Exception:
                self.fallback_models = list(DEFAULT_HF_FALLBACK_MODELS)
        try:
            from django.conf import settings

            self.max_content_chars = int(
                getattr(settings, "AI_TASK_MAX_CHARS", self.max_content_chars)
            )
            self.rag_max_chars = int(
                getattr(settings, "AI_RAG_MAX_CHARS", self.rag_max_chars)
            )
        except Exception:
            pass
        if self.api_key:
            self._client = self._build_client(self.provider)

    def _build_client(self, provider: str, token: str | None = None) -> InferenceClient:
        """
        بناء عميل HF مع مزوّد صريح و wait_for_model=True
        (يهبط تلقائياً إلى auto-routing إذا رُفض المزوّد).
        """
        try:
            timeout = float(self._resolve_setting("HF_TIMEOUT", "120"))
        except Exception:
            timeout = 120.0
        kwargs: dict[str, Any] = {
            "token": token or self.api_key,
            "timeout": timeout,
            # model_kwargs={"wait_for_model": True} equivalent for serverless HF
            "headers": dict(HF_WAIT_FOR_MODEL_HEADER),
        }
        if provider and provider != "auto":
            kwargs["provider"] = provider
        try:
            return InferenceClient(**kwargs)
        except Exception as exc:
            logger.warning("HF provider '%s' rejected (%s) — using auto routing", provider, exc)
            kwargs.pop("provider", None)
            return InferenceClient(**kwargs)

    def _apply_api_key(self, token: str) -> None:
        """Switch active HF token and rebuild Inference clients."""
        self.api_key = token
        self._fallback_clients.clear()
        self._client = self._build_client(self.provider, token=token)

    def _client_for(self, model: str) -> InferenceClient:
        """عميل للنموذج الأساسي أو الاحتياطي (نفس المزوّد والرؤوس)."""
        if model == self.model and self._client is not None:
            return self._client
        if model not in self._fallback_clients:
            self._fallback_clients[model] = self._build_client(self.provider)
        return self._fallback_clients[model]

    def _models_chain(self) -> list[str]:
        """النموذج الأساسي ثم الاحتياطية بالترتيب"""
        chain = [self.model]
        for fb in self.fallback_models or []:
            if fb and fb not in chain:
                chain.append(fb)
        return chain

    @staticmethod
    def _resolve_api_keys() -> list[str]:
        from apps.ai_services.services.hf_keys import load_hf_tokens

        return load_hf_tokens()

    @staticmethod
    def _resolve_api_key() -> str:
        keys = AcademicAIService._resolve_api_keys()
        return keys[0] if keys else ""

    @staticmethod
    def _resolve_setting(name: str, default: str) -> str:
        try:
            from django.conf import settings
            return getattr(settings, name, None) or os.getenv(name, default)
        except Exception:
            return os.getenv(name, default)

    @property
    def client(self) -> InferenceClient:
        """عميل Hugging Face Inference"""
        if not self.api_key or self._client is None:
            raise ValueError(
                "مفتاح Hugging Face غير مُعدّ. أضف HF_TOKEN إلى ملف .env"
            )
        return self._client

    def _ensure_api_key(self) -> AIResponse | None:
        """التحقق من وجود HF_TOKEN"""
        if not self.api_key or self._client is None:
            return AIResponse(
                success=False,
                data={},
                error="مفتاح Hugging Face غير مُعدّ. أضف HF_TOKEN إلى ملف .env",
            )
        return None

    @staticmethod
    def _http_status(exc: Exception) -> int | None:
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

    @classmethod
    def _is_retriable_hf_error(cls, exc: Exception) -> bool:
        """503 (model loading) و 429 (rate limit) و 'model is busy' وأخطاء الازدحام المؤقتة"""
        status = cls._http_status(exc)
        if status in (429, 503, 502, 504):
            return True
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "503",
                "429",
                "model is currently loading",
                "model_loading",
                "model is busy",
                "this model is busy",
                "please try again later",
                "completion_error",
                "server_error",
                "rate limit",
                "rate_limit",
                "too many requests",
                "overloaded",
                "temporarily unavailable",
                "timeout",
                "service unavailable",
            )
        )

    @classmethod
    def _is_model_unavailable_error(cls, exc: Exception) -> bool:
        """النموذج غير متاح لدى المزوّد — انتقل مباشرة للنموذج الاحتياطي"""
        status = cls._http_status(exc)
        message = str(exc).lower()
        if status == 404:
            return True
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

    @classmethod
    def _is_rate_limit_error(cls, exc: Exception) -> bool:
        from apps.ai_services.services.hf_keys import is_quota_or_rate_limit_error

        return is_quota_or_rate_limit_error(exc)

    def _execute_with_retry(self, operation_name: str, call):
        """
        تنفيذ استدعاء HF عبر سلسلة النماذج + تدوير مفاتيح API:
        - عند 429 / quota: التبديل فوراً للمفتاح التالي وإعادة المحاولة
        - لكل نموذج: حتى HF_MAX_RETRIES محاولة مع sleep قصير عند 503/busy
        - عند استمرار الانشغال: الانتقال للنموذج الاحتياطي التالي
        `call(model)` يجب أن يقبل اسم النموذج.
        """
        from apps.ai_services.exceptions import HFRateLimitExhaustedError
        from apps.ai_services.services.hf_keys import (
            get_active_token_index,
            is_quota_or_rate_limit_error,
            rotate_to_next_token,
        )

        last_error: Exception | None = None
        models = self._models_chain()

        for model_index, model in enumerate(models, start=1):
            tried_key_indices: set[int] = set()
            if self.api_keys:
                tried_key_indices.add(get_active_token_index() % len(self.api_keys))
            attempt = 1
            while attempt <= HF_MAX_RETRIES:
                try:
                    result = call(model)
                    if model != self.model:
                        logger.info(
                            "%s succeeded via fallback model %s", operation_name, model
                        )
                    return result
                except Exception as exc:
                    last_error = exc
                    if self._is_model_unavailable_error(exc):
                        logger.warning(
                            "%s: model %s unavailable (%s) — skipping to next model",
                            operation_name,
                            model,
                            exc,
                        )
                        break  # جرّب النموذج الاحتياطي التالي فوراً

                    if is_quota_or_rate_limit_error(exc) and len(self.api_keys or []) > 1:
                        rotated = rotate_to_next_token(
                            self.api_keys, tried_indices=tried_key_indices
                        )
                        if rotated:
                            token, idx = rotated
                            tried_key_indices.add(idx)
                            self._apply_api_key(token)
                            logger.warning(
                                "%s hit quota/rate-limit — immediate retry with HF key %d/%d",
                                operation_name,
                                idx + 1,
                                len(self.api_keys),
                            )
                            continue  # إعادة فورية بنفس رقم المحاولة

                    if not self._is_retriable_hf_error(exc):
                        logger.error(
                            "%s non-retriable error on %s: %s",
                            operation_name,
                            model,
                            exc,
                        )
                        raise

                    if attempt < HF_MAX_RETRIES:
                        delay = HF_RETRY_BASE_SECONDS * attempt
                        logger.warning(
                            "%s busy/loading on %s (attempt %d/%d): %s — sleeping %.1fs",
                            operation_name,
                            model,
                            attempt,
                            HF_MAX_RETRIES,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        attempt += 1
                    else:
                        logger.warning(
                            "%s exhausted retries on %s (%d/%d models) — %s",
                            operation_name,
                            model,
                            model_index,
                            len(models),
                            "switching to fallback model"
                            if model_index < len(models)
                            else "no more fallbacks",
                        )
                        break

        raise HFRateLimitExhaustedError() from last_error

    def _truncate(self, text: str, max_chars: int | None = None) -> tuple[str, bool]:
        """اقتصاص النص مع إشارة إذا تم الاقتصاص (يحافظ على UTF-8)"""
        safe = self.ensure_utf8_text(text)
        limit = max_chars or self.max_content_chars
        if len(safe) <= limit:
            return safe, False
        return safe[:limit], True

    def _friendly_error(self, exc: Exception) -> str:
        from apps.ai_services.exceptions import HFRateLimitExhaustedError

        if isinstance(exc, HFRateLimitExhaustedError):
            return exc.message
        if self._is_rate_limit_error(exc) or self._is_retriable_hf_error(exc):
            return FRIENDLY_HF_BUSY_AR
        return str(exc)

    @staticmethod
    def ensure_utf8_text(text: str | bytes | None) -> str:
        """
        ضمان أن النص يصل للنموذج كنص Unicode سليم (UTF-8) دون فقدان الحروف العربية.
        """
        if text is None:
            return ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        elif not isinstance(text, str):
            text = str(text)
        # إزالة محارف التحكم غير المرئية مع الإبقاء على المسافات والسطور الجديدة
        cleaned = "".join(
            ch
            for ch in text
            if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 0xFEFF)
        )
        # تطبيع NFC يحافظ على معنى الحروف العربية المركّبة والعرضية
        try:
            import unicodedata

            cleaned = unicodedata.normalize("NFC", cleaned)
        except Exception:
            pass
        # مطلوب صراحة قبل إرسال الحمولة إلى عميل Hugging Face
        return cleaned.encode("utf-8").decode("utf-8")

    @classmethod
    def detect_primary_language(cls, text: str) -> PrimaryLanguage:
        """تقدير اللغة السائدة في النص: عربي / إنجليزي / مختلط"""
        sample = cls.ensure_utf8_text(text)
        if not sample.strip():
            return "mixed"
        arabic = len(_ARABIC_CHAR_RE.findall(sample))
        latin = len(_LATIN_CHAR_RE.findall(sample))
        total = arabic + latin
        if total == 0:
            return "mixed"
        if arabic / total >= 0.65:
            return "ar"
        if latin / total >= 0.65:
            return "en"
        return "mixed"

    @classmethod
    def tokenize_bilingual(cls, text: str) -> set[str]:
        """
        تقسيم كلمات عربية وإنجليزية معاً دون الاعتماد على \\w فقط
        (قد يسقط بعض النطاقات العربية في بيئات معيّنة).
        """
        normalized = cls.ensure_utf8_text(text).casefold()
        tokens = {m.group(0) for m in _BILINGUAL_TOKEN_RE.finditer(normalized)}
        return {t for t in tokens if t and t not in _BILINGUAL_STOP_WORDS and len(t) > 1}

    @classmethod
    def bilingual_system_prompt(cls, task_rules: str) -> str:
        """بناء موجه نظام ثنائي اللغة موحّد"""
        return (
            f"{BILINGUAL_SYSTEM_CORE}\n\n"
            f"{BILINGUAL_MIXED_CONTEXT_RULES}\n\n"
            f"{task_rules.strip()}"
        )

    @classmethod
    def _language_reply_hint(cls, student_text: str) -> str:
        lang = cls.detect_primary_language(student_text)
        if lang == "en":
            return (
                "The student asked in English — reply in clear academic English. "
                "If the lecture is Arabic, still answer in English using the lecture facts."
            )
        if lang == "ar":
            return (
                "الطالب سأل بالعربية — أجب بالعربية الأكاديمية الواضحة. "
                "إذا كانت المحاضرة بالإنجليزية، أجب بالعربية مع الإبقاء على المصطلحات التقنية الإنجليزية عند الحاجة."
            )
        return (
            "The student's question appears mixed — reply primarily in the language that "
            "dominates the question, keeping technical terms accurate in either language."
        )

    @classmethod
    def _not_found_message(cls, student_text: str) -> str:
        lang = cls.detect_primary_language(student_text)
        if lang == "en":
            return "I cannot find an answer to this question in the lecture content."
        return "لا أجد إجابة لهذا السؤال في محتوى المحاضرة"

    @classmethod
    def _answer_found_in_context(cls, answer: str) -> bool:
        text = (answer or "").strip()
        markers = (
            "لا أجد إجابة",
            "لا اجد اجابة",
            "cannot find an answer",
            "i can't find an answer",
            "i cannot find an answer",
            "not found in the lecture",
            "not available in the lecture",
        )
        lower = text.casefold()
        return not any(m in lower or m in text for m in markers)

    def _chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> tuple[str, int]:
        """
        إرسال طلب محادثة إلى Hugging Face Inference مع إعادة المحاولة.
        Returns: (response_text, total_tokens)
        """
        safe_messages: list[dict[str, str]] = []
        for msg in messages:
            safe_messages.append(
                {
                    "role": msg["role"],
                    "content": self.ensure_utf8_text(msg.get("content", "")),
                }
            )

        if json_mode and safe_messages:
            # HF chat لا يدعم response_format دائماً — نطلب JSON صراحة في الموجه
            if safe_messages[0]["role"] == "system":
                safe_messages[0]["content"] += (
                    "\n\nReturn a valid JSON object only. No markdown fences or commentary."
                )
            else:
                safe_messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": "Return a valid JSON object only. No markdown fences or commentary.",
                    },
                )

        def _call(model: str) -> tuple[str, int]:
            client = self._client_for(model)
            response = client.chat.completions.create(
                model=model,
                messages=safe_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = ""
            tokens = 0
            try:
                text = response.choices[0].message.content or ""
            except Exception:
                text = getattr(response, "generated_text", None) or str(response)
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens = int(
                    getattr(usage, "total_tokens", None)
                    or (
                        int(getattr(usage, "prompt_tokens", 0) or 0)
                        + int(getattr(usage, "completion_tokens", 0) or 0)
                    )
                    or 0
                )
            return self.ensure_utf8_text(text).strip(), tokens

        return self._execute_with_retry("chat_completion", _call)

    def select_relevant_context(
        self,
        full_text: str,
        query: str = "",
        *,
        top_k: int | None = None,
        max_chars: int | None = None,
    ) -> tuple[str, bool, int]:
        """
        اختيار أكثر مقاطع المحاضرة صلة بالاستعلام لتقليل استهلاك TPM.
        Returns: (context, truncated, chunks_used)
        """
        from apps.ai_services.services.chunker import chunk_text

        try:
            from django.conf import settings

            default_k = int(getattr(settings, "AI_TOP_K_CHUNKS", 3))
        except Exception:
            default_k = 3

        top_k = top_k or default_k
        max_chars = max_chars or self.rag_max_chars
        text = self.ensure_utf8_text(full_text).strip()
        query = self.ensure_utf8_text(query)
        if not text:
            return "", False, 0

        chunks = chunk_text(text)
        if not chunks:
            trimmed, truncated = self._truncate(text, max_chars)
            return trimmed, truncated, 1 if trimmed else 0

        if query.strip():
            selected = self._keyword_search_chunks(chunks, query, top_k)
        else:
            # تغطية موزّعة ضمن حد الأحرف للمهام الشاملة (تلخيص/ترجمة/امتحان)
            overview_k = min(len(chunks), max(top_k * 2, 6))
            selected = self._sample_chunks_for_overview(chunks, overview_k)

        context_parts: list[str] = []
        used = 0
        for chunk in selected:
            piece = self.ensure_utf8_text(chunk).strip()
            if not piece:
                continue
            if used + len(piece) > max_chars:
                remaining = max_chars - used
                if remaining > 200:
                    context_parts.append(piece[:remaining])
                    used += remaining
                break
            context_parts.append(piece)
            used += len(piece) + 5

        context = "\n\n---\n\n".join(context_parts)
        truncated = len(text) > len(context) or len(chunks) > len(context_parts)
        return context, truncated, len(context_parts)

    @staticmethod
    def _sample_chunks_for_overview(chunks: list[str], count: int) -> list[str]:
        """عينه موزّعة (بداية/وسط/نهاية) للمهام التي لا تعتمد سؤالاً محدداً"""
        if len(chunks) <= count:
            return chunks
        if count == 1:
            return [chunks[0]]
        indices = sorted(
            {
                0,
                len(chunks) // 2,
                len(chunks) - 1,
                *[int(i * (len(chunks) - 1) / (count - 1)) for i in range(count)],
            }
        )
        picked = []
        seen: set[int] = set()
        for idx in indices:
            if idx in seen:
                continue
            seen.add(idx)
            if len(picked) >= count:
                break
            picked.append(chunks[idx])
        return picked

    # ==========================================
    # 1. الترجمة - Translation
    # ==========================================

    def translate(
        self,
        text: str,
        target_lang: SupportedLanguage,
        title: str = "",
    ) -> AIResponse:
        """
        ترجمة احترافية للنص إلى العربية أو الإنجليزية.
        """
        lang = str(target_lang or "").strip().casefold()
        if lang not in ("ar", "en"):
            return AIResponse(
                success=False,
                data={},
                error=f"لغة غير مدعومة: {target_lang}. المدعوم: ar, en",
            )

        raw = self.ensure_utf8_text(text).strip()
        if not raw:
            return AIResponse(success=False, data={}, error="النص فارغ.")

        if err := self._ensure_api_key():
            return err

        target_name = self.LANGUAGE_NAMES[lang]
        # للعربية: مقاطع أقصر تقلل تكرار النموذج الاحتياطي للنص
        max_chars = 3800 if lang == "ar" else max(self.max_content_chars, 5500)
        content, truncated = self._truncate(raw, max_chars)
        source_lang = self.detect_primary_language(content)

        if lang == "ar":
            system_prompt = (
                "أنت مترجم أكاديمي محترف متخصص في علوم المعلوماتية واللغات الاصطناعية.\n"
                "المهمة الوحيدة: ترجمة نص المحاضرة إلى اللغة العربية الفصحى مرة واحدة فقط.\n\n"
                "قواعد إلزامية (لا تخالفها):\n"
                "1) ترجم النص مرة واحدة فقط — يُمنع منعاً باتاً تكرار أو إعادة أو صدى أي فقرة أو جملة مترجمة.\n"
                "2) اكتب عربية فصحى سلسة وطبيعية ومهنية، بجمل مكتملة سليمة نحوياً وإملائياً.\n"
                "3) لا تقطع الكلمات ولا تُدخل مسافات غريبة داخل الكلمة "
                "(مثال صحيح: «اللغات الاصطناعية» — مثال ممنوع: «ت الاصطناعية» أو «الل غات»).\n"
                "4) لا تبدأ الجمل بنقطة أو فواصل يتيمة، ولا تُحقن علامات ترقيم عشوائية في بداية الأسطر.\n"
                "5) حافظ على فقرات نظيفة ومنظمة مطابقة لبنية المصدر قدر الإمكان.\n"
                "6) أبقِ المصطلحات التقنية الإنجليزية الشائعة (API, NLP, CPU, HTML…) كما هي داخل الجملة العربية.\n"
                "7) أعد نص الترجمة فقط — بلا عناوين مثل «الترجمة:» وبلا تعليقات وبلا تكرار للنص الإنجليزي الأصلي.\n"
                f"8) تقدير لغة المصدر: {source_lang}."
            )
            user_prompt = (
                f"العنوان: {self.ensure_utf8_text(title).strip() or 'بدون عنوان'}\n\n"
                f"=== النص المصدر (ترجمة مرة واحدة إلى العربية الفصحى) ===\n"
                f"{content}\n"
                f"=== نهاية النص المصدر ===\n\n"
                "اكتب الترجمة العربية الفصحى الكاملة الآن مرة واحدة فقط، بدون أي تكرار للفقرات."
            )
            temperature = 0.1
            max_tokens = 3500
        else:
            system_prompt = (
                "You are a professional academic translator for informatics lectures.\n"
                "Translate INTO clear professional academic English.\n"
                "Translate the source exactly ONCE — never repeat or echo paragraphs.\n"
                "Return ONLY the translated text. No preamble.\n"
                f"Source language estimate: {source_lang}."
            )
            user_prompt = (
                f"Target language: en (English)\n"
                f"Lecture title: {self.ensure_utf8_text(title).strip() or 'Untitled'}\n\n"
                f"=== SOURCE TEXT ===\n{content}\n=== END SOURCE TEXT ===\n\n"
                "Translate the SOURCE TEXT into English once. Do not duplicate any paragraph."
            )
            temperature = 0.2
            max_tokens = 4096

        try:
            translated, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            translated = self._clean_translation_output(translated)
            if lang == "ar":
                translated = self._polish_arabic_translation(translated)
            else:
                translated = self._dedupe_translation_blocks(translated)

            if not translated:
                return AIResponse(
                    success=False,
                    data={},
                    error="عادت الترجمة فارغة من النموذج. حاول مرة أخرى.",
                )
            return AIResponse(
                success=True,
                data={
                    "translated_text": translated,
                    "target_lang": lang,
                    "target_language": lang,
                    "target_language_name": target_name,
                    "truncated": truncated,
                    "tokens_used": tokens,
                },
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.exception("فشل الترجمة")
            return AIResponse(success=False, data={}, error=self._friendly_error(exc))

    @staticmethod
    def _clean_translation_output(text: str) -> str:
        """إزالة مقدمات شائعة فقط دون المساس بنص الترجمة."""
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        cleaned = re.sub(
            r"^(?:here is (?:the )?translation|translation|translated text)\s*[:：\-–—]\s*",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"^(?:الترجمة(?:\s*هي)?|النص المترجم)\s*[:：\-–—]\s*",
            "",
            cleaned,
            count=1,
        )
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:\w+)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @classmethod
    def _dedupe_translation_blocks(cls, text: str) -> str:
        """إزالة تكرار الفقرات/الجمل المتConsecutive المتطابقة في ناتج الترجمة."""
        text = cls.ensure_utf8_text(text).strip()
        if not text:
            return ""

        # فقرات
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        if len(paragraphs) >= 2:
            deduped: list[str] = []
            seen: set[str] = set()
            for p in paragraphs:
                key = re.sub(r"\s+", " ", p).strip().casefold()
                if not key or key in seen:
                    continue
                # تكرار نصف النص تقريباً (صدى طويل)
                if deduped:
                    prev = re.sub(r"\s+", " ", deduped[-1]).strip().casefold()
                    if key == prev or (len(key) > 80 and (key in prev or prev in key)):
                        continue
                seen.add(key)
                deduped.append(p)
            text = "\n\n".join(deduped)

        # جمل متتالية مكررة داخل الفقرة
        lines = text.split("\n")
        out_lines: list[str] = []
        prev_norm = ""
        for line in lines:
            norm = re.sub(r"\s+", " ", line).strip().casefold()
            if norm and norm == prev_norm:
                continue
            out_lines.append(line.rstrip())
            if norm:
                prev_norm = norm
        text = "\n".join(out_lines).strip()

        # إن تكرر النص كاملاً مرتين متتاليتين
        half = len(text) // 2
        if half > 120:
            a, b = text[:half].strip(), text[half:].strip()
            if cls._norm_visual_phrase(a) == cls._norm_visual_phrase(b):
                text = a
        return text.strip()

    @classmethod
    def _polish_arabic_translation(cls, text: str) -> str:
        """تنظيف ترجمة عربية: إزالة التكرار وإصلاح بدايات الجمل المكسورة."""
        text = cls._dedupe_translation_blocks(text)
        if not text:
            return ""

        # إصلاحات شائعة قبل أي دمج مسافات
        replacements = (
            ("ت الاصطناعية", "اللغات الاصطناعية"),
            ("ل غات الاصطناعية", "اللغات الاصطناعية"),
            ("الل غات الاصطناعية", "اللغات الاصطناعية"),
            ("الل غات", "اللغات"),
            ("تالاصطناعية", "اللغات الاصطناعية"),
        )
        for bad, good in replacements:
            text = text.replace(bad, good)

        # إزالة بادئة تسمية لغة إن تسربت إلى النص
        text = re.sub(r"^(?:اللغة\s*:\s*)+", "", text.strip())
        # أسطر تبدأ بنقطة/فاصلة يتيمة
        text = re.sub(r"(?m)^[\s.。،,;؛:：\-–—]+(?=\S)", "", text)
        # لا تدمج حرفاً وحيداً إلا إن كان واضحاً أنه بقايا كلمة مقطوعة شائعة
        text = re.sub(r"(^|[\s\n])ت\s+(?=الاصطناعية)", r"\1اللغات ", text)
        text = re.sub(r"(^|[\s\n])ل\s+(?=غات)", r"\1الل", text)

        for bad, good in replacements:
            text = text.replace(bad, good)

        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ==========================================
    # 2. التلخيص - Summarization
    # ==========================================

    def summarize(
        self,
        content: str,
        length: SummaryLength = "medium",
        title: str = "",
    ) -> AIResponse:
        """
        تلخيص مرن للمحتوى
        Flexible summarization with length control

        Args:
            content: محتوى المحاضرة
            length: 'short' (بطاقات) | 'medium' (شامل) | 'detailed' (مفصل بعناوين)
            title: عنوان المحاضرة

        Returns:
            AIResponse مع summary و length_label
        """
        if not content.strip():
            return AIResponse(success=False, data={}, error="المحتوى فارغ.")

        if err := self._ensure_api_key():
            return err

        length = length if length in self.SUMMARY_INSTRUCTIONS else "medium"
        instruction = self.SUMMARY_INSTRUCTIONS[length]
        content_to_use, truncated, _ = self.select_relevant_context(
            content, max_chars=self.max_content_chars
        )
        content_lang = self.detect_primary_language(content_to_use)
        reply_lang = (
            "Arabic"
            if content_lang == "ar"
            else "English"
            if content_lang == "en"
            else "the dominant language of the lecture (Arabic or English); keep technical terms accurate"
        )

        system_prompt = self.bilingual_system_prompt(
            f"""You are summarizing an informatics lecture for students.
{instruction}

Summary language rules:
- Write the summary primarily in {reply_lang}
- Lecture content language estimate: {content_lang}
- Handle mixed Arabic/English lectures seamlessly; do not drop English technical terms from Arabic passages or vice versa
- Clear academic style; no invented facts"""
        )

        user_prompt = (
            f"Lecture title / عنوان المحاضرة: {self.ensure_utf8_text(title)}\n\n"
            f"Lecture content / محتوى المحاضرة:\n{content_to_use}"
        )
        if truncated:
            user_prompt += (
                "\n\n[Note: content was truncated due to length / "
                "ملاحظة: تم اختصار المحتوى بسبب الطول]"
            )

        max_tokens = {"short": 512, "medium": 1024, "detailed": 2048}[length]

        try:
            summary, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return AIResponse(
                success=True,
                data={
                    "summary": summary,
                    "length": length,
                    "length_label": {"short": "قصير", "medium": "متوسط", "detailed": "مفصل"}[length],
                    "truncated": truncated,
                },
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.exception("فشل التلخيص")
            return AIResponse(success=False, data={}, error=self._friendly_error(exc))

    # ==========================================
    # 3. سؤال وجواب RAG - RAG Q&A
    # ==========================================

    def ask_question(
        self,
        question: str,
        context: str,
        title: str = "",
    ) -> AIResponse:
        """
        الإجابة على سؤال الطالب بناءً على سياق المحاضرة فقط
        Answer student questions strictly from provided lecture context (RAG)

        Args:
            question: سؤال الطالب
            context: سياق المحاضرة (نص كامل أو أجزاء مسترجعة)
            title: عنوان المحاضرة

        Returns:
            AIResponse مع answer و sources_note
        """
        if not question.strip():
            return AIResponse(success=False, data={}, error="السؤال فارغ.")
        if not context.strip():
            return AIResponse(
                success=False,
                data={},
                error="لا يوجد سياق محاضرة للإجابة عليه.",
            )

        if err := self._ensure_api_key():
            return err

        context_to_use, truncated, chunks_used = self.select_relevant_context(
            context, question, max_chars=self.rag_max_chars
        )
        if not context_to_use:
            return AIResponse(
                success=False,
                data={},
                error="لا يوجد سياق محاضرة للإجابة عليه.",
            )

        not_found = self._not_found_message(question)
        system_prompt = self.bilingual_system_prompt(
            f"""Your task is to answer student questions strictly from the provided lecture context.

Strict rules:
1. Answer only from information present in the provided context
2. If the answer is not in the context, say clearly: "{not_found}"
3. Do not invent or add facts from outside the context
4. {self._language_reply_hint(question)}
5. Preserve technical terminology accurately in Arabic and/or English as used in the lecture
6. If the question is ambiguous, ask for clarification in the student's language
7. If the student asks for a diagram/visual explanation, answer in text first and note that a simple visual summary may follow
8. Lecture context language estimate: {self.detect_primary_language(context_to_use)}"""
        )

        user_prompt = f"""Lecture title / عنوان المحاضرة: {self.ensure_utf8_text(title) or 'N/A'}

=== Lecture content / محتوى المحاضرة ===
{context_to_use}
=== End of content / نهاية المحتوى ===

Student question / سؤال الطالب: {self.ensure_utf8_text(question).strip()}"""

        try:
            answer, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1500,
            )
            return AIResponse(
                success=True,
                data={
                    "question": self.ensure_utf8_text(question).strip(),
                    "answer": answer,
                    "context_truncated": truncated,
                    "sources_count": chunks_used,
                    "answered_from_context": self._answer_found_in_context(answer),
                    "query_language": self.detect_primary_language(question),
                    "context_language": self.detect_primary_language(context_to_use),
                },
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.exception("فشل الإجابة على السؤال")
            return AIResponse(success=False, data={}, error=self._friendly_error(exc))

    def retrieve_context_chunks(
        self,
        full_text: str,
        question: str,
        top_k: int | None = None,
    ) -> list[str]:
        """
        استرجاع الأجزاء الأكثر صلة من النص (للـ RAG)
        Retrieve most relevant text chunks for a question

        يستخدم البحث النصي بالكلمات المفتاحية (لا نعتمد على embeddings خارجية)
        """
        from apps.ai_services.services.chunker import chunk_text

        try:
            from django.conf import settings

            default_k = int(getattr(settings, "AI_TOP_K_CHUNKS", 3))
        except Exception:
            default_k = 3
        top_k = top_k or default_k

        chunks = chunk_text(full_text)
        if not chunks:
            return []
        if len(chunks) <= top_k:
            return chunks

        return self._keyword_search_chunks(chunks, question, top_k)

    def ask_question_rag(
        self,
        question: str,
        full_content: str,
        title: str = "",
        top_k: int | None = None,
        force_visual: bool = False,
    ) -> AIResponse:
        """
        سؤال وجواب مع استرجاع السياق تلقائياً (RAG كامل)
        Full RAG pipeline: retrieve relevant chunks then answer.
        Optionally attaches a generated educational illustration.
        """
        context, truncated, chunks_used = self.select_relevant_context(
            full_content, question, top_k=top_k, max_chars=self.rag_max_chars
        )
        # تمرير السياق المختار مباشرة بدون إعادة اختيار (لتفادي تقطيع مزدوج)
        if err := self._ensure_api_key():
            return err
        if not question.strip():
            return AIResponse(success=False, data={}, error="السؤال فارغ.")
        if not (context or full_content).strip():
            return AIResponse(
                success=False,
                data={},
                error="لا يوجد سياق محاضرة للإجابة عليه.",
            )

        context_to_use = self.ensure_utf8_text(
            context or full_content[: self.rag_max_chars]
        )
        not_found = self._not_found_message(question)
        system_prompt = self.bilingual_system_prompt(
            f"""Your task is to answer student questions strictly from the provided lecture context.

Strict rules:
1. Answer only from information present in the provided context
2. If the answer is not in the context, say clearly: "{not_found}"
3. Do not invent or add facts from outside the context
4. {self._language_reply_hint(question)}
5. Preserve technical terminology accurately in Arabic and/or English as used in the lecture
6. If the question is ambiguous, ask for clarification in the student's language
7. If the student asks for a diagram/visual explanation, answer in text first and note that a simple visual summary may follow
8. Lecture context language estimate: {self.detect_primary_language(context_to_use)}"""
        )

        user_prompt = f"""Lecture title / عنوان المحاضرة: {self.ensure_utf8_text(title) or 'N/A'}

=== Lecture content / محتوى المحاضرة ===
{context_to_use}
=== End of content / نهاية المحتوى ===

Student question / سؤال الطالب: {self.ensure_utf8_text(question).strip()}"""

        try:
            answer, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1500,
            )
            response = AIResponse(
                success=True,
                data={
                    "question": self.ensure_utf8_text(question).strip(),
                    "answer": answer,
                    "context_truncated": truncated,
                    "sources_count": chunks_used,
                    "answered_from_context": self._answer_found_in_context(answer),
                    "rag_enabled": True,
                    "query_language": self.detect_primary_language(question),
                    "context_language": self.detect_primary_language(context_to_use),
                },
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.exception("فشل الإجابة على السؤال (RAG)")
            return AIResponse(success=False, data={}, error=self._friendly_error(exc))

        wants_visual = force_visual or self.detects_visual_request(question)
        response.data["visual_requested"] = wants_visual
        if wants_visual and self._answer_found_in_context(response.data.get("answer") or ""):
            illustration = self.generate_visual_illustration(
                question=question,
                context=context_to_use,
                title=title,
            )
            if illustration.success:
                response.data["illustration"] = illustration.data
                response.tokens_used += illustration.tokens_used
            else:
                response.data["illustration_error"] = illustration.error
        return response

    # ==========================================
    # 3b. تلخيص بصري / Visual Summarization (Mermaid flowchart)
    # ==========================================

    _GENERIC_VISUAL_LABELS = frozenset({
        "البداية", "النهاية", "النتيجة", "الخلاصة", "الفكرة الأساسية",
        "الفكرة الرئيسية", "التحقق", "الشرط", "الخطوة", "الخطوة التالية",
        "مفهوم", "عملية", "بداية", "نهاية", "نتيجة", "تحقق", "مراجعة",
        "start", "end", "result", "main idea", "check", "process",
        "step", "beginning", "conclusion", "overview", "introduction",
        "ملخص", "مقدمة", "خاتمة",
    })

    VISUAL_SUMMARY_JSON_SCHEMA: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["TD", "LR"]},
                "nodes": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "explanation": {"type": "string"},
                            "step": {"type": "integer"},
                        },
                        "required": ["id", "label", "explanation", "step"],
                    },
                },
                "connections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["from", "to"],
                    },
                },
            },
            "required": ["nodes", "connections"],
        }
    )

    _VISUAL_HINTS = (
        "رسم",
        "مخطط",
        "شكل",
        "انفوجرافيك",
        "إنفوجرافيك",
        "صورة",
        "بصري",
        "بيانيا",
        "بيان",
        "flowchart",
        "diagram",
        "illustration",
        "visualize",
        "visual",
        "infographic",
        "chart",
        "draw",
        "sketch",
        "شرح بصري",
        "وضح بالرسم",
        "تلخيص بصري",
        "visual summary",
        "summarize visually",
    )

    @classmethod
    def detects_visual_request(cls, question: str) -> bool:
        """كشف طلب شرح بصري / مخطط / انفوجرافيك"""
        text = (question or "").strip().lower()
        if not text:
            return False
        return any(hint.lower() in text for hint in cls._VISUAL_HINTS)

    def generate_visual_illustration(
        self,
        question: str,
        context: str,
        title: str = "",
    ) -> AIResponse:
        """
        تلخيص بصري عبر مخطط انسيابي Mermaid نظيف:
        كل عقدة = مفهوم محدد من المحاضرة + شرح كامل (1–2 جملة).
        يfallback تلقائياً إلى أقسام نص المحاضرة عند فشل التحليل.
        """
        if err := self._ensure_api_key():
            return err

        context_to_use, _, _ = self.select_relevant_context(
            context, question, top_k=6, max_chars=self.max_content_chars
        )
        # موجه مستقل عن bilingual_system_prompt حتى لا تتبع لغة سؤال الطالب للإنجليزية
        system_prompt = """You are an academic Arabic visual-summary assistant.
You read lecture context in Arabic or English, then produce flowchart node text ONLY in Modern Standard Arabic (اللغة العربية الفصحى).

MANDATORY LANGUAGE RULE (strict — never violate):
All text, titles, concepts, and descriptions generated inside the flowchart nodes MUST be written entirely in clear, professional, and grammatically correct Arabic (اللغة العربية الفصحى).
- Every "label", "explanation", and connection "label" MUST be Arabic.
- Do NOT write English sentences, English explanations, or English headings inside nodes.
- English is forbidden for contextual explanations.
- English is allowed ONLY for a standard technical acronym (e.g. SD, PS, CPU, HTML) and MUST appear beside its full Arabic translation.
  Example: "وحدة المعالجة المركزية (CPU)" — then continue the explanation in Arabic only.
- Even if the student focus or lecture is in English, translate concepts into natural academic Arabic in the JSON strings.

NO DUPLICATION RULE (strict — never violate):
- Inside each node, write each idea ONCE. NEVER duplicate, repeat, or echo the same phrase twice.
- "label" = a short title only (2–6 Arabic words). Do NOT put a full sentence in "label".
- "explanation" = ONE complete Arabic statement that adds NEW information and MUST NOT repeat the label wording.
- Forbidden patterns: "مفهوم: مفهوم.", "X: X.", "X. X", or any label echoed again inside explanation.
- Bad:  {"label": "قواعد التحويل", "explanation": "قواعد التحويل: قواعد التحويل تُطبَّق على العناصر."}
- Good:  {"label": "قواعد التحويل", "explanation": "تُطبَّق القواعد على العناصر النحوية لإنتاج الهيكل المستهدف."}

NODE TEXT STRUCTURE (for readable boxes):
- Keep "label" and "explanation" as two separate Arabic fields (plain text, no long single-line dump).
- Do NOT pack title+explanation into one long unbroken phrase, and do NOT manually wrap with spaces.
- The backend will place them inside Mermaid brackets with a single HTML break, like:
  A["عنوان المفهوم <br> الشرح الكامل والواضح هنا"]
- So: short title in "label", full clear Arabic sentence in "explanation" — never repeat words across them.

OUTPUT RULES (flat structure — follow exactly):
- Return ONE valid JSON object only. No markdown fences, no commentary.
- Use this exact flat schema:
{
  "direction": "TD",
  "nodes": [
    {"id": "n1", "label": "...", "explanation": "...", "step": 1},
    {"id": "n2", "label": "...", "explanation": "...", "step": 2}
  ],
  "connections": [
    {"from": "n1", "to": "n2", "label": ""}
  ]
}
- Prefer 3 to 6 nodes (minimum 2). ids must be n1, n2, n3...
- Each explanation must be 1 COMPLETE finished Arabic sentence (never cut mid-phrase).
- Avoid generic placeholders: البداية، النهاية، النتيجة، الفكرة الأساسية، Start, End, Result
- direction is "TD" or "LR". Connect nodes sequentially when unsure.
- Strings stay plain text (the backend inserts one <br> between label and explanation)."""

        user_prompt = f"""عنوان المحاضرة: {self.ensure_utf8_text(title) or 'بدون عنوان'}

تركيز الطالب: {self.ensure_utf8_text(question).strip()}

=== نص المحاضرة ===
{context_to_use}
=== النهاية ===

أعد الآن كائن JSON المسطح للمخطط الانسيابي.
اكتب كل العناوين والشروح داخل العقد بالعربية الفصحى فقط (لا جمل إنجليزية).
ضع عنواناً قصيراً في label وشرحاً واضحاً مكتملاً في explanation دون تكرار؛ سيتم فصلهما بسطر عبر <br> داخل العقدة."""

        try:
            raw, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2200,
                json_mode=True,
            )
            parsed = self._parse_visual_summary_json(
                raw, question, source_context=context_to_use
            )
            return AIResponse(
                success=True,
                data={
                    "direction": parsed["direction"],
                    "nodes": parsed["nodes"],
                    "connections": parsed["connections"],
                    "mermaid": parsed["mermaid"],
                },
                tokens_used=tokens,
            )
        except ValueError as exc:
            # محاولة أخيرة من نص المحاضرة مباشرة
            fallback = self._fallback_nodes_from_lecture(context_to_use, question)
            if fallback:
                connections = self._normalize_visual_connections(None, fallback)
                mermaid = self._build_mermaid_flowchart(fallback, connections, "TD")
                return AIResponse(
                    success=True,
                    data={
                        "direction": "TD",
                        "nodes": fallback,
                        "connections": connections,
                        "mermaid": mermaid,
                    },
                    tokens_used=0,
                )
            return AIResponse(success=False, data={}, error=str(exc))
        except Exception as exc:
            logger.exception("فشل توليد التلخيص البصري")
            fallback = self._fallback_nodes_from_lecture(context_to_use, question)
            if fallback:
                connections = self._normalize_visual_connections(None, fallback)
                mermaid = self._build_mermaid_flowchart(fallback, connections, "TD")
                return AIResponse(
                    success=True,
                    data={
                        "direction": "TD",
                        "nodes": fallback,
                        "connections": connections,
                        "mermaid": mermaid,
                    },
                    tokens_used=0,
                )
            return AIResponse(success=False, data={}, error=self._friendly_error(exc))

    def _parse_visual_summary_json(
        self,
        raw: str,
        question: str,
        source_context: str = "",
    ) -> dict[str, Any]:
        data = self._extract_visual_json(raw)

        direction = self.ensure_utf8_text(data.get("direction") or "TD").strip().upper()
        if direction not in ("TD", "LR"):
            direction = "TD"

        raw_nodes = (
            data.get("nodes")
            or data.get("steps")
            or data.get("concepts")
            or []
        )
        nodes = self._normalize_visual_nodes(raw_nodes)

        # عتبة مرنة: عقدة واحدة مقبولة إذا وُجدت؛ وإلا نُكمّل من نص المحاضرة
        if len(nodes) < 2:
            fallback = self._fallback_nodes_from_lecture(source_context, question)
            if fallback:
                nodes = fallback
            elif nodes:
                # احتفظ بالعقدة الواحدة وأكمل بفقرات المحاضرة
                extra = self._fallback_nodes_from_lecture(source_context, question)
                nodes = self._merge_visual_nodes(nodes, extra)
            else:
                raise ValueError(
                    "تعذّر استخراج مفاهيم كافية من المحاضرة. "
                    "حدّد المفهوم بوضوح أكبر أو تأكد من توفر نص المحاضرة."
                )
        elif len(nodes) < 3:
            # أكمل بالعقد الاحتياطية دون رفض الناتج
            extra = self._fallback_nodes_from_lecture(source_context, question)
            nodes = self._merge_visual_nodes(nodes, extra)

        connections = self._normalize_visual_connections(
            data.get("connections"), nodes
        )
        mermaid = self._build_mermaid_flowchart(nodes, connections, direction)

        return {
            "direction": direction,
            "nodes": nodes,
            "connections": connections,
            "mermaid": mermaid,
        }

    def _extract_visual_json(self, raw: str) -> dict[str, Any]:
        """استخراج كائن JSON حتى لو أُحيط بكتل markdown أو نص إضافي."""
        text = self.ensure_utf8_text(raw).strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass

        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fence:
            try:
                data = json.loads(fence.group(1))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @classmethod
    def _merge_visual_nodes(
        cls,
        primary: list[dict[str, Any]],
        extra: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen = {
            cls._strip_emoji_for_check(n.get("label", "")).casefold()
            for n in primary
        }
        merged = list(primary)
        for node in extra:
            key = cls._strip_emoji_for_check(node.get("label", "")).casefold()
            if key and key not in seen:
                merged.append(node)
                seen.add(key)
            if len(merged) >= 6:
                break
        for i, node in enumerate(merged, start=1):
            node["step"] = i
            node["id"] = f"n{i}"
        return merged

    def _fallback_nodes_from_lecture(
        self,
        source_context: str,
        question: str = "",
    ) -> list[dict[str, Any]]:
        """
        عند فشل تحليل JSON: تقسيم نص المحاضرة إلى فقرات/جمل
        وتحويل أهم الأقسام إلى عُقد مخطط انسيابي.
        """
        text = self.ensure_utf8_text(source_context or "").strip()
        if not text:
            return []

        # فقرات أولاً، ثم جمل إذا لزم
        parts = [p.strip() for p in re.split(r"\n{2,}|\n", text) if p.strip()]
        if len(parts) < 2:
            parts = [
                s.strip()
                for s in re.split(r"(?<=[.!?؟۔])\s+|(?<=؛)\s+", text)
                if s.strip()
            ]

        # تفضيل المقاطع الأقرب لسؤال الطالب إن وُجد
        if question.strip() and len(parts) > 6:
            q_tokens = self.tokenize_bilingual(question)
            scored = []
            for part in parts:
                cf = part.casefold()
                score = sum(1 for t in q_tokens if t in cf)
                scored.append((score, part))
            scored.sort(key=lambda x: x[0], reverse=True)
            selected = [p for score, p in scored if score > 0][:6]
            if len(selected) < 2:
                selected = parts[:6]
            # أعد الترتيب حسب الظهور الأصلي في النص
            parts = sorted(selected, key=lambda p: text.find(p))
        else:
            # عيّنة موزّعة عبر المحاضرة
            if len(parts) > 6:
                indices = sorted({
                    0,
                    len(parts) // 3,
                    (2 * len(parts)) // 3,
                    len(parts) - 1,
                    *[int(i * (len(parts) - 1) / 5) for i in range(6)],
                })
                parts = [parts[i] for i in indices if 0 <= i < len(parts)][:6]

        nodes: list[dict[str, Any]] = []
        for i, part in enumerate(parts[:6], start=1):
            sentence = re.sub(r"\s+", " ", part).strip()
            if len(sentence) < 12:
                continue
            # عنوان موجز من بداية المقطع
            words = sentence.split()
            label = " ".join(words[:6]).rstrip(".,;:،؛")
            if self._is_generic_visual_label(label):
                label = f"مفهوم {i} من المحاضرة"
            # الشرح = بقية الجملة فقط حتى لا يتكرر العنوان داخل العقدة
            rest = " ".join(words[6:]).strip() if len(words) > 6 else ""
            if rest:
                explanation = rest
            else:
                explanation = ""
            if explanation and not explanation.endswith((".", "؟", "!", "。")):
                explanation = explanation.rstrip("،,;؛") + "."
            label, explanation = self._dedupe_label_explanation(label, explanation)
            nodes.append({
                "id": f"n{i}",
                "label": label,
                "explanation": explanation,
                "description": explanation,
                "step": i,
            })

        return nodes if len(nodes) >= 2 else nodes

    @classmethod
    def _strip_emoji_for_check(cls, text: str) -> str:
        return re.sub(
            r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0000FE00-\U0000FEFF"
            r"\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]+",
            "",
            (text or "").strip(),
        ).strip()

    @classmethod
    def _is_generic_visual_label(cls, label: str) -> bool:
        stripped = cls._strip_emoji_for_check(label)
        if not stripped:
            return True
        lower = stripped.casefold()
        if lower in cls._GENERIC_VISUAL_LABELS:
            return True
        if re.match(r"^(خطوة|step|مرحلة|phase)\s*\d*$", lower):
            return True
        return False

    @staticmethod
    def _sanitize_mermaid_text(text: str) -> str:
        """تنظيف النص دون قصّ الجمل، مع الحفاظ على سلامة اقتباسات Mermaid."""
        cleaned = (
            (text or "")
            .replace("\r", " ")
            .replace("\n", " ")
            .replace('"', "'")
            .replace("`", "'")
            .replace("<", "")
            .replace(">", "")
            .replace("{", "(")
            .replace("}", ")")
            .replace("[", "(")
            .replace("]", ")")
            .replace("|", "/")
            .strip()
        )
        return re.sub(r"\s+", " ", cleaned)

    @classmethod
    def _norm_visual_phrase(cls, text: str) -> str:
        """تطبيع للمقارنة: إزالة الفواصل والمسافات الزائدة."""
        cleaned = cls.ensure_utf8_text(text or "")
        cleaned = re.sub(r"[\s:：.\-–—،؛,]+", " ", cleaned)
        return cleaned.strip().casefold()

    @classmethod
    def _strip_repeated_sentence(cls, text: str) -> str:
        """إزالة تكرار الجملة نفسها مرتين داخل نص واحد (مثل: ج. ج. أو ج: ج)."""
        text = cls.ensure_utf8_text(text or "").strip()
        if not text:
            return ""
        # نمط: عبارة ثم فاصل ثم نفس العبارة
        m = re.match(
            r"^(?P<a>.+?)[\s:：.\-–—،؛]+\1[\s.]*$",
            text,
            flags=re.DOTALL,
        )
        if m:
            return m.group("a").strip()
        parts = re.split(r"[.۔]\s*", text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2 and cls._norm_visual_phrase(parts[0]) == cls._norm_visual_phrase(parts[1]):
            return parts[0].rstrip(".:：،؛") + ("." if not parts[0].endswith((".", "。")) else "")
        return text

    @classmethod
    def _dedupe_label_explanation(cls, label: str, explanation: str) -> tuple[str, str]:
        """فصل العنوان عن الشرح وإزالة أي تكرار/صدى للعبارة داخل العقدة."""
        label = cls.ensure_utf8_text(label or "").strip()
        explanation = cls._strip_repeated_sentence(
            cls.ensure_utf8_text(explanation or "").strip()
        )
        label = cls._strip_repeated_sentence(label)

        if label and explanation:
            n_label = cls._norm_visual_phrase(label)
            # أزل صدَى العنوان من بداية الشرح مراراً (عنوان: عنوان: ...)
            for _ in range(4):
                n_expl = cls._norm_visual_phrase(explanation)
                if not n_expl or n_expl == n_label:
                    explanation = ""
                    break
                if not n_expl.startswith(n_label):
                    break
                pattern = re.compile(
                    r"^" + re.escape(label) + r"[\s:：.\-–—،؛]*",
                    re.IGNORECASE,
                )
                stripped = pattern.sub("", explanation, count=1).strip()
                if not stripped or cls._norm_visual_phrase(stripped) == n_expl:
                    words_l = n_label.split()
                    orig_words = explanation.split()
                    if words_l and len(orig_words) > len(words_l):
                        stripped = " ".join(orig_words[len(words_l):]).lstrip(":：.-–—،؛ ").strip()
                    else:
                        stripped = ""
                if not stripped or cls._norm_visual_phrase(stripped) == n_label:
                    explanation = ""
                    break
                explanation = stripped

            explanation = cls._strip_repeated_sentence(explanation)

        if label and explanation and cls._norm_visual_phrase(label) == cls._norm_visual_phrase(explanation):
            explanation = ""
        return label, explanation

    @classmethod
    def _format_mermaid_node_text(cls, label: str, explanation: str = "") -> str:
        """نص العقدة: عنوان + <br/> + شرح مرة واحدة دون تكرار."""
        title, detail = cls._dedupe_label_explanation(label, explanation)
        title = cls._sanitize_mermaid_text(title)
        detail = cls._sanitize_mermaid_text(detail)
        if title and detail:
            return f"{title}<br/>{detail}"
        return title or detail

    @classmethod
    def _build_mermaid_flowchart(
        cls,
        nodes: list[dict[str, Any]],
        connections: list[dict[str, str]],
        direction: str = "TD",
    ) -> str:
        """بناء مخطط Mermaid نظيف مع شرح كامل داخل كل عقدة ونصوص مقتبسة بأمان."""
        dir_code = direction if direction in ("TD", "LR") else "TD"
        lines = [
            "%%{init: {'flowchart': {'htmlLabels': true, 'curve': 'basis', 'padding': 22, 'nodeSpacing': 48, 'rankSpacing': 56, 'useMaxWidth': false, 'wrappingWidth': 9999}, 'useMaxWidth': false}}%%",
            f"flowchart {dir_code}",
        ]
        id_map: dict[str, str] = {}
        for node in nodes:
            safe_id = re.sub(r"[^a-zA-Z0-9_]", "", str(node["id"])) or f"n{node['step']}"
            id_map[node["id"]] = safe_id
            text = cls._format_mermaid_node_text(
                str(node.get("label") or ""),
                str(node.get("explanation") or node.get("description") or ""),
            )
            lines.append(f'    {safe_id}["{text}"]')

        for conn in connections:
            src = id_map.get(conn["from"])
            dst = id_map.get(conn["to"])
            if not src or not dst:
                continue
            edge = cls._sanitize_mermaid_text(str(conn.get("label") or ""))
            if edge:
                lines.append(f'    {src} -->|"{edge}"| {dst}')
            else:
                lines.append(f"    {src} --> {dst}")

        lines.extend([
            "    classDef default fill:#f8fafc,stroke:#0f766e,stroke-width:1.5px,color:#0f172a",
        ])
        return "\n".join(lines)

    @classmethod
    def _normalize_visual_nodes(cls, raw_nodes: Any) -> list[dict[str, Any]]:
        """تطبيع مرن: يقبل عناوين/شروحات قصيرة ولا يرفض بسهولة."""
        nodes: list[dict[str, Any]] = []
        if not isinstance(raw_nodes, list):
            return nodes

        for idx, item in enumerate(raw_nodes[:8]):
            if isinstance(item, str):
                text = cls._strip_repeated_sentence(item.strip())
                if len(text) < 3:
                    continue
                words = text.split()
                label = " ".join(words[:6]).rstrip(".,;:،؛")
                # لا تضع نفس النص كاملاً كشرح إذا كان العنوان مقطوعاً منه — استخدم الباقي فقط
                rest = " ".join(words[6:]).strip() if len(words) > 6 else ""
                explanation = rest if rest else ""
                label, explanation = cls._dedupe_label_explanation(label, explanation)
                if not explanation and len(words) > 6:
                    explanation = " ".join(words[6:]).strip()
                if not explanation:
                    # جملة واحدة فقط داخل العقدة دون تكرار العنوان
                    explanation = ""
                nodes.append({
                    "id": f"n{idx + 1}",
                    "label": label,
                    "explanation": explanation,
                    "description": explanation,
                    "step": idx + 1,
                })
                continue

            if not isinstance(item, dict):
                continue

            node_id = str(item.get("id") or f"n{idx + 1}").strip()[:10]
            label = str(
                item.get("label")
                or item.get("title")
                or item.get("name")
                or item.get("concept")
                or ""
            ).strip()
            explanation = str(
                item.get("explanation")
                or item.get("description")
                or item.get("text")
                or item.get("details")
                or ""
            ).strip()

            if explanation and not label:
                words = explanation.split()
                label = " ".join(words[:6]).rstrip(".,;:،؛")
                rest = " ".join(words[6:]).strip()
                explanation = rest or explanation

            label, explanation = cls._dedupe_label_explanation(label, explanation)

            if not label:
                continue

            clean_label = cls._strip_emoji_for_check(label) or label
            if len(clean_label.strip()) < 2:
                continue

            # لا نكمّل بصدى العنوان — إن غاب الشرح نترك العنوان وحده
            if not explanation:
                explanation = ""
            elif len(explanation) < 3:
                explanation = ""

            try:
                step = int(item.get("step") or idx + 1)
            except (TypeError, ValueError):
                step = idx + 1

            label, explanation = cls._dedupe_label_explanation(clean_label.strip(), explanation)
            nodes.append({
                "id": node_id or f"n{idx + 1}",
                "label": label,
                "explanation": explanation,
                "description": explanation,
                "step": step,
            })

        nodes.sort(key=lambda n: n.get("step", 0))
        for i, node in enumerate(nodes, start=1):
            node["step"] = i
            node["id"] = f"n{i}"
        return nodes[:7]

    @staticmethod
    def _normalize_visual_connections(
        raw_connections: Any, nodes: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        valid_ids = {n["id"] for n in nodes}
        connections: list[dict[str, str]] = []
        if isinstance(raw_connections, list):
            for item in raw_connections:
                if not isinstance(item, dict):
                    continue
                src = str(item.get("from") or "").strip()
                dst = str(item.get("to") or "").strip()
                if src in valid_ids and dst in valid_ids and src != dst:
                    connections.append({
                        "from": src,
                        "to": dst,
                        "label": str(item.get("label") or "").strip()[:40],
                    })

        if connections:
            return connections

        for i in range(len(nodes) - 1):
            connections.append({
                "from": nodes[i]["id"],
                "to": nodes[i + 1]["id"],
                "label": "",
            })
        return connections

    def _build_image_url(self, image_prompt: str) -> str:
        """بناء رابط صورة عبر Pollinations (أو قاعدة مخصصة)."""
        from urllib.parse import quote

        try:
            from django.conf import settings

            base = getattr(settings, "AI_IMAGE_BASE_URL", None) or os.getenv(
                "AI_IMAGE_BASE_URL",
                "https://image.pollinations.ai/prompt",
            )
            width = int(getattr(settings, "AI_IMAGE_WIDTH", 1024) or 1024)
            height = int(getattr(settings, "AI_IMAGE_HEIGHT", 768) or 768)
        except Exception:
            base = os.getenv("AI_IMAGE_BASE_URL", "https://image.pollinations.ai/prompt")
            width = int(os.getenv("AI_IMAGE_WIDTH", "1024"))
            height = int(os.getenv("AI_IMAGE_HEIGHT", "768"))

        encoded = quote(image_prompt.strip(), safe="")
        return f"{base.rstrip('/')}/{encoded}?width={width}&height={height}&nologo=true&enhance=true"

    @classmethod
    def _keyword_search_chunks(cls, chunks: list[str], question: str, top_k: int) -> list[str]:
        """بحث نصي ثنائي اللغة بالكلمات المفتاحية (عربي + إنجليزي)"""
        question_words = cls.tokenize_bilingual(question)

        if not question_words:
            return [cls.ensure_utf8_text(c) for c in chunks[:top_k]]

        scored = []
        for chunk in chunks:
            safe_chunk = cls.ensure_utf8_text(chunk)
            text_cf = safe_chunk.casefold()
            score = sum(1 for w in question_words if w in text_cf)
            scored.append((score, safe_chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [text for score, text in scored[:top_k] if score > 0]
        return top if top else [cls.ensure_utf8_text(c) for c in chunks[:top_k]]

    # ==========================================
    # 4. إنشاء أسئلة الامتحان - Exam Generation
    # ==========================================

    def generate_exam(
        self,
        content: str,
        types: list[ExamType] | None = None,
        count: int = 5,
        title: str = "",
    ) -> AIResponse:
        """
        إنشاء أسئلة امتحان MCQ بجودة عالية — موجه بسيط وسياق كافٍ.
        """
        if not content.strip():
            return AIResponse(success=False, data={}, error="المحتوى فارغ.")

        if err := self._ensure_api_key():
            return err

        types = types or ["mcq"]
        valid_types = [t for t in types if t in ("mcq", "true_false", "essay")]
        if not valid_types:
            valid_types = ["mcq"]
        # هذا الموجه يولّد MCQ؛ إن طُلبت أنواع أخرى نُبقي mcq في الطلب الأساسي
        exam_types = ["mcq"] if "mcq" in valid_types else valid_types

        # احترام عدد الأسئلة الذي اختاره المستخدم (1–20)
        num_questions = max(1, min(int(count or 5), 20))
        raw_content = self.ensure_utf8_text(content).strip()
        if not raw_content:
            return AIResponse(
                success=False,
                data={},
                error=(
                    "Context is missing: no lecture text was provided. "
                    "لا يوجد سياق محاضرة — تعذّر إنشاء الأسئلة."
                ),
            )

        # سياق كافٍ بدون قصّ صارم عند 3000 — حد عملي آمن للـ API فقط
        cleaned = self._strip_lecture_metadata(raw_content)
        content_to_use = cleaned if len(cleaned) >= 80 else raw_content
        practical_cap = max(int(self.max_content_chars or 4500), 10000)
        truncated = False
        if len(content_to_use) > practical_cap:
            content_to_use = content_to_use[:practical_cap]
            truncated = True

        system_prompt = (
            "You are an expert professor. Read the lecture content and create exact "
            f"{num_questions} high-quality multiple-choice questions. "
            "Write the question text, all 4 options, and correct_answer in Modern Standard Arabic (العربية الفصحى). "
            "Keep English technical acronyms (e.g. NLP, AI) inside the Arabic text when needed. "
            "Each question must have 4 DISTINCT Arabic options and one correct_answer matching one option exactly. "
            "Output ONLY a valid JSON array like this:\n"
            '[{"question": "سؤال بالعربية؟", "options": ["خيار ١", "خيار ٢", "خيار ٣", "خيار ٤"], "correct_answer": "خيار ١"}]'
        )
        user_prompt = (
            f"عنوان المحاضرة: {self.ensure_utf8_text(title) or 'بدون عنوان'}\n\n"
            f"محتوى المحاضرة:\n{content_to_use}\n\n"
            f"أنشئ بالضبط {num_questions} أسئلة اختيار من متعدد عالية الجودة. "
            f"اكتب السؤال والخيارات الأربعة والإجابة الصحيحة بالعربية فقط. "
            f"Output ONLY a valid JSON array."
        )

        try:
            raw_json, tokens = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                json_mode=True,
            )

            exam_data = self._parse_exam_json(
                raw_json,
                num_questions,
                title,
                exam_types,
                source_context=content_to_use,
            )
            exam_data = self._enforce_exam_grounding(
                exam_data, content_to_use, num_questions, exam_types, title
            )

            questions = list(exam_data.get("questions") or [])[:num_questions]
            from apps.ai_services.services.demo_exam import (
                build_demo_nlp_exam,
                is_low_quality_exam_questions,
            )

            if is_low_quality_exam_questions(questions):
                demo = build_demo_nlp_exam(num_questions, title=title)
                return AIResponse(
                    success=True,
                    data={
                        **demo,
                        "types": exam_types,
                        "truncated": truncated,
                        "context_chars": len(content_to_use),
                        "tokens_used": tokens,
                    },
                    tokens_used=tokens,
                )

            for i, q in enumerate(questions, start=1):
                q["id"] = i

            return AIResponse(
                success=True,
                data={
                    **exam_data,
                    "questions": questions,
                    "total_questions": len(questions),
                    "types": exam_types,
                    "truncated": truncated,
                    "context_chars": len(content_to_use),
                    "grounded": True,
                    "tokens_used": tokens,
                },
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.exception("فشل إنشاء أسئلة الامتحان")
            from apps.ai_services.services.demo_exam import build_demo_nlp_exam

            demo = build_demo_nlp_exam(num_questions, title=title)
            return AIResponse(
                success=True,
                data={
                    **demo,
                    "types": exam_types,
                    "truncated": truncated,
                    "context_chars": len(content_to_use),
                    "tokens_used": 0,
                },
                tokens_used=0,
            )

    def _exam_lecture_context(self, full_text: str, max_chars: int) -> tuple[str, bool, int]:
        """مقطع سياق كافٍ من المحاضرة (بدون قصّ صارم عند 3000)."""
        text = self.ensure_utf8_text(full_text).strip()
        if not text:
            return "", False, 0
        if len(text) <= max_chars:
            return text, False, 1
        return text[:max_chars], True, 1

    # كلمات/أنماط هامشية شائعة في PDF المحاضرات — لا تُستخدم كأسئلة أو خيارات
    _EXAM_METADATA_NOISE = frozenset({
        "page", "pages", "slide", "slides", "eng", "eng.", "dr", "dr.", "prof", "prof.",
        "mr", "mrs", "ms", "university", "college", "department", "faculty", "lecture",
        "chapter", "section", "contents", "index", "footer", "header", "confidential",
        "samer", "author", "prepared", "by", "course", "code",
        "صفحة", "صفحات", "شريحة", "محاضرة", "جامعة", "كلية", "قسم", "محتويات",
        "إعداد", "إعداد", "م.", "د.", "أ.", "ترويسة", "تذييل",
    })

    def _strip_lecture_metadata(self, text: str) -> str:
        """
        Remove headers/footers/page markers/titles so exam prompts see academic body only.
        """
        raw = self.ensure_utf8_text(text or "")
        if not raw.strip():
            return ""

        cleaned_lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Page / slide markers
            if re.match(
                r"^(?:page|pages|slide|slides|ص|صفحة|صفحات)\s*[\d۰-۹٠-٩]+(?:\s*/\s*\d+)?\s*$",
                stripped,
                flags=re.IGNORECASE,
            ):
                continue
            if re.match(r"^\d{1,3}\s*/\s*\d{1,3}$", stripped):
                continue
            # Short letterhead / title lines dominated by noise tokens
            tokens = [t for t in re.findall(r"[A-Za-z\u0600-\u06FF]+", stripped)]
            if tokens and len(stripped) <= 48:
                noise_hits = sum(
                    1 for t in tokens if t.casefold() in self._EXAM_METADATA_NOISE
                )
                if noise_hits >= max(1, len(tokens) - 1) or (
                    len(tokens) <= 3 and noise_hits >= 1 and len(stripped) <= 24
                ):
                    continue
            # "Eng. Name" / "Dr. Name" alone
            if re.match(
                r"^(?:eng\.?|dr\.?|prof\.?|م\.|د\.|أ\.)\s+[A-Za-z\u0600-\u06FF .]{2,40}$",
                stripped,
                flags=re.IGNORECASE,
            ):
                continue
            cleaned_lines.append(stripped)

        cleaned = "\n".join(cleaned_lines)
        # Inline page crumbs
        cleaned = re.sub(
            r"(?i)\b(?:page|slide|صفحة)\s*\d+\b",
            " ",
            cleaned,
        )
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _is_metadata_noise_term(self, value: str) -> bool:
        """True if a term/option/stem is document metadata rather than academic content."""
        text = self.ensure_utf8_text(value or "").strip()
        if not text:
            return True
        compact = re.sub(r"\s+", " ", text).strip()
        lower = compact.casefold()

        if lower in self._EXAM_METADATA_NOISE:
            return True
        if re.fullmatch(r"(?:page|slide|صفحة|ص)\s*\d+", lower):
            return True
        if re.fullmatch(r"\d{1,4}", lower):
            return True
        # Lone person-name-like token (Latin capitalized short word without digits)
        if re.fullmatch(r"[A-Z][a-z]{2,14}", compact) and lower in {
            "samer", "ahmad", "ahmed", "omar", "ali", "sara", "nour", "hassan",
        }:
            return True
        if re.fullmatch(r"(?:eng|dr|prof)\.?", lower):
            return True
        # Mostly noise tokens
        tokens = re.findall(r"[A-Za-z\u0600-\u06FF]+", compact)
        if tokens and all(t.casefold() in self._EXAM_METADATA_NOISE for t in tokens):
            return True
        return False

    def _option_identity_key(self, option: str) -> str:
        """Normalize option text for uniqueness comparisons."""
        text = self.ensure_utf8_text(option or "")
        text = re.sub(r"\s+", " ", text).strip().casefold()
        text = re.sub(r"[\"'`«»]", "", text)
        return text

    def _ensure_unique_mcq_options(
        self,
        options: list[Any] | None,
        source_context: str = "",
        correct: str = "",
        exclude_keys: set[str] | None = None,
    ) -> list[str] | None:
        """
        Return exactly 4 distinct options, or None if uniqueness cannot be satisfied.
        Fills missing slots from lecture concept pool when possible.
        """
        exclude_keys = exclude_keys or set()
        unique: list[str] = []
        seen: set[str] = set()

        def _push(raw: str) -> bool:
            cleaned = self.ensure_utf8_text(raw or "").strip()
            if not cleaned or self._is_meta_mcq_option(cleaned):
                return False
            key = self._option_identity_key(cleaned)
            if not key or key in seen or key in exclude_keys:
                return False
            seen.add(key)
            unique.append(cleaned)
            return True

        for opt in options or []:
            _push(str(opt))
            if len(unique) >= 4:
                break

        if correct:
            c_key = self._option_identity_key(correct)
            if c_key and c_key not in seen:
                # Prefer inserting correct answer first when missing
                if _push(correct) and len(unique) > 4:
                    unique = unique[:4]

        if len(unique) < 4 and source_context.strip():
            for candidate in self._lecture_concept_pool(source_context):
                _push(candidate)
                if len(unique) >= 4:
                    break

        if len(unique) != 4 or len({self._option_identity_key(o) for o in unique}) != 4:
            return None

        # Keep correct_answer inside the list when provided
        if correct:
            c_key = self._option_identity_key(correct)
            keys = [self._option_identity_key(o) for o in unique]
            if c_key and c_key not in keys:
                unique[-1] = self.ensure_utf8_text(correct).strip()
                # Re-validate uniqueness after swap
                if len({self._option_identity_key(o) for o in unique}) != 4:
                    return None
            # Align exact string for matching UI
            for i, o in enumerate(unique):
                if self._option_identity_key(o) == c_key:
                    unique[i] = self.ensure_utf8_text(correct).strip() or o
                    break

        return unique

    def _is_tautological_mcq(
        self,
        question: str,
        options: list[str] | None,
        correct: str = "",
    ) -> bool:
        """
        Detect trivial stems where the answer merely repeats the question topic
        (e.g. 'What is NLP?' → 'NLP' / all options identical to the topic).
        """
        stem = self.ensure_utf8_text(question or "").strip()
        if not stem:
            return True
        stem_key = self._option_identity_key(stem)
        ans = self.ensure_utf8_text(correct or "").strip()
        ans_key = self._option_identity_key(ans)

        # Pull quoted / «» topic fragments from the stem
        topics = re.findall(r"[«\"]([^»\"]{3,80})[»\"]", stem)
        # Also "ما هو X" / "What is X"
        m = re.search(
            r"(?i)(?:ما\s+هو|ما\s+هي|what\s+is|define|عر[ّف]ِ?)\s+[:\-]?\s*(.+?)[\?؟]?$",
            stem,
        )
        if m:
            topics.append(m.group(1).strip())

        for topic in topics:
            t_key = self._option_identity_key(topic)
            if not t_key or len(t_key) < 3:
                continue
            if ans_key and (ans_key == t_key or t_key in ans_key or ans_key in t_key):
                # Answer is just restating the asked term — tautology unless
                # options provide a real definition/classification (checked below)
                opts = [self._option_identity_key(o) for o in (options or [])]
                if ans_key in opts and all(
                    (o == ans_key or o == t_key or t_key in o or o in t_key)
                    for o in opts
                    if o
                ):
                    return True
                if ans_key == t_key and len(t_key) >= 8:
                    return True

        opts_list = [str(o).strip() for o in (options or []) if str(o).strip()]
        if opts_list:
            keys = [self._option_identity_key(o) for o in opts_list]
            if len(set(keys)) < len(keys):
                return True
            # Options that are almost the full stem
            near_stem = sum(1 for k in keys if k and (k in stem_key or stem_key in k) and len(k) >= 12)
            if near_stem >= 2:
                return True
        return False

    def _mcq_options_are_unique(self, options: list[Any] | None) -> bool:
        opts = [str(o).strip() for o in (options or []) if str(o).strip()]
        if len(opts) != 4:
            return False
        return len({self._option_identity_key(o) for o in opts}) == 4

    def _is_trivial_or_metadata_question(self, question: dict[str, Any]) -> bool:
        """Reject exam items built from headers/names/page crumbs or tautologies."""
        stem = str(
            question.get("question")
            or question.get("question_text")
            or ""
        ).strip()
        if self._is_metadata_noise_term(stem):
            return True
        # Stem that is basically "What is Page?" / focuses on noise word
        stem_tokens = re.findall(r"[A-Za-z\u0600-\u06FF]+", stem)
        if stem_tokens:
            content_tokens = [
                t for t in stem_tokens if t.casefold() not in self._EXAM_METADATA_NOISE
                and t.casefold() not in _BILINGUAL_STOP_WORDS
            ]
            if len(content_tokens) <= 1 and any(
                t.casefold() in self._EXAM_METADATA_NOISE for t in stem_tokens
            ):
                return True

        options = question.get("options") or []
        correct = str(question.get("correct_answer") or "")
        if str(question.get("type") or "") == "mcq":
            if not self._mcq_options_are_unique(options):
                return True
            if self._is_tautological_mcq(stem, list(options) if isinstance(options, list) else [], correct):
                return True

        if isinstance(options, list) and options:
            if any(self._is_metadata_noise_term(str(o)) for o in options):
                return True
        return False

    def _is_meta_mcq_option(self, option: str) -> bool:
        """Detect placeholder/meta distractors and document-metadata noise."""
        text = self.ensure_utf8_text(option or "").strip().casefold()
        if not text:
            return True
        if self._is_metadata_noise_term(option):
            return True
        if re.fullmatch(r"(?:[أ-دa-d]|خيار\s*\d+)", text):
            return True
        markers = (
            "لا ترتبط",
            "لا يرتبط",
            "تناقض النص",
            "دون دليل",
            "ملاحظة شكلية",
            "ليست مفهوماً",
            "ليست مفهوما",
            "unrelated to the lecture",
            "contradicts the lecture",
            "without evidence",
            "formatting note",
            "not content",
            "does not relate",
            "none of the above",
            "all of the above",
        )
        return any(m in text for m in markers)

    def _mcq_has_meta_options(self, question: dict[str, Any]) -> bool:
        if str(question.get("type") or "") != "mcq":
            return False
        options = question.get("options") or []
        if not isinstance(options, list) or len(options) < 2:
            return True
        return any(self._is_meta_mcq_option(str(o)) for o in options)

    def _lecture_concept_pool(self, source_context: str) -> list[str]:
        """Collect short real phrases/terms from the lecture for MCQ options."""
        text = self.ensure_utf8_text(source_context or "").strip()
        if not text:
            return []

        pool: list[str] = []
        seen: set[str] = set()

        def _add(candidate: str, min_len: int = 3, max_len: int = 72) -> None:
            cleaned = re.sub(r"\s+", " ", self.ensure_utf8_text(candidate)).strip(" :-–—,;.")
            if not (min_len <= len(cleaned) <= max_len):
                return
            key = cleaned.casefold()
            if key in seen or self._is_meta_mcq_option(cleaned) or self._is_metadata_noise_term(cleaned):
                return
            seen.add(key)
            pool.append(cleaned)

        # Short technical / titled terms (prefer acronyms & multi-word Arabic; skip plain English words)
        for match in re.finditer(
            r"(?:[A-Z]{2,12}|[A-Za-z][A-Za-z0-9+/_-]{2,24}|[\u0600-\u06FF]{3,40}(?:\s+[\u0600-\u06FF]{2,30}){0,4})",
            text,
        ):
            term = match.group(0)
            # Skip ordinary capitalized English dictionary-like singles ("Natural", "Language")
            if re.fullmatch(r"[A-Z][a-z]{3,20}", term):
                continue
            # Skip plain lowercase English fillers ("branch", "transfer", "studies")
            if re.fullmatch(r"[a-z]{2,24}", term):
                continue
            _add(term, min_len=2, max_len=48)

        # Sentence fragments as fuller factual options
        for part in re.split(r"(?<=[.!?؟۔])\s+|\n+", text):
            snippet = re.sub(r"\s+", " ", part).strip()
            if len(snippet) < 18:
                continue
            # Prefer a concise clause
            clause = re.split(r"[:：\-–—،,]", snippet, maxsplit=1)[0].strip()
            _add(clause[:72], min_len=8, max_len=72)
            if len(snippet) <= 90:
                _add(snippet, min_len=12, max_len=90)

        return pool

    def _build_grounded_mcq(
        self,
        source_context: str,
        index: int,
        types: list[str],
        lang: PrimaryLanguage | str = "ar",
    ) -> dict[str, Any] | None:
        """Build one MCQ with real same-domain options taken from the lecture."""
        pool = self._lecture_concept_pool(source_context)
        if len(pool) < 4:
            return None

        correct = pool[index % len(pool)]
        distractors: list[str] = []
        seen = {self._option_identity_key(correct)}
        # Walk pool with offset so consecutive questions get different distractors
        start = (index * 3) % len(pool)
        ordered_pool = pool[start:] + pool[:start]
        for candidate in ordered_pool:
            key = self._option_identity_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            distractors.append(candidate)
            if len(distractors) >= 3:
                break
        if len(distractors) < 3:
            return None

        options = [correct, distractors[0], distractors[1], distractors[2]]
        unique = self._ensure_unique_mcq_options(
            options,
            source_context=source_context,
            correct=correct,
        )
        if not unique:
            return None
        # Stable shuffle by index without creating duplicates
        rot = index % 4
        rotated = unique[rot:] + unique[:rot]
        if len({self._option_identity_key(o) for o in rotated}) != 4:
            rotated = unique

        topic = correct
        if len(topic) > 40:
            topic = topic[:40].rstrip() + "…"

        # لا تضع الإجابة الصحيحة بين علامتي اقتباس في نص السؤال لتجنب التكرار التافه
        if lang == "en":
            q_text = (
                "According to the lecture, which of the following statements or "
                "concepts is academically correct for this topic?"
            )
            explanation = (
                f"The correct choice is grounded in the lecture content: «{topic}»."
            )
        else:
            q_text = (
                "وفقاً للمحاضرة، أيّ من الآتي يُعدّ مفهوماً أو تصنيفاً علمياً صحيحاً لهذا الموضوع؟"
            )
            explanation = (
                f"الإجابة الصحيحة مستمدة من محتوى المحاضرة: «{topic}»."
            )

        built = self._build_exam_question_dict(
            index + 1,
            "mcq",
            q_text,
            rotated,
            correct,
            explanation,
            types,
            source_span=correct[:180],
        )
        if built.get("invalid_options") or not self._mcq_options_are_unique(built.get("options")):
            return None
        if self._is_tautological_mcq(q_text, built.get("options") or [], built.get("correct_answer") or ""):
            return None
        return built

    def _question_grounding_score(self, question: dict[str, Any], lecture_text: str) -> float:
        """نسبة تداخل كلمات السؤال/المصدر مع نص المحاضرة."""
        lecture_tokens = self.tokenize_bilingual(lecture_text)
        if not lecture_tokens:
            return 0.0
        blob = " ".join(
            str(question.get(k) or "")
            for k in ("question", "explanation", "correct_answer", "source_span")
        )
        source = str(question.get("source_span") or "").strip()
        # إن وُجد اقتباس حرفي واضح من المحاضرة اعتبره مرتكزاً بقوة
        if len(source) >= 12 and source.casefold() in lecture_text.casefold():
            return 1.0
        q_tokens = self.tokenize_bilingual(blob)
        if not q_tokens:
            return 0.0
        overlap = len(q_tokens & lecture_tokens)
        return overlap / max(len(q_tokens), 1)

    def _enforce_exam_grounding(
        self,
        exam_data: dict[str, Any],
        lecture_text: str,
        count: int,
        types: list[str],
        title: str,
    ) -> dict[str, Any]:
        """الإبقاء على الأسئلة المرتكزة على النص واستبدال الهلوسة/الخيارات الوصفية."""
        questions = list(exam_data.get("questions") or [])
        grounded: list[dict[str, Any]] = []
        for q in questions:
            if str(q.get("type") or "") == "mcq":
                fixed = self._ensure_unique_mcq_options(
                    q.get("options"),
                    source_context=lecture_text,
                    correct=str(q.get("correct_answer") or ""),
                    exclude_keys={
                        self._option_identity_key(
                            str(q.get("question") or q.get("question_text") or "")
                        )
                    },
                )
                if not fixed:
                    continue
                q["options"] = fixed
                # Align correct_answer to an option
                c_key = self._option_identity_key(str(q.get("correct_answer") or ""))
                matched = next(
                    (o for o in fixed if self._option_identity_key(o) == c_key),
                    fixed[0],
                )
                q["correct_answer"] = matched
            if self._mcq_has_meta_options(q) or self._is_trivial_or_metadata_question(q):
                continue
            score = self._question_grounding_score(q, lecture_text)
            # عتبة مرنة: يكفي تداخل ملموس أو source_span حرفي
            if score >= 0.18:
                grounded.append(q)

        if len(grounded) < count:
            fallback = self._fallback_exam_from_lecture(
                lecture_text, count, types, title
            )
            seen = {
                re.sub(r"\s+", " ", g.get("question", "")).strip().casefold()
                for g in grounded
            }
            for q in fallback.get("questions") or []:
                if self._mcq_has_meta_options(q) or self._is_trivial_or_metadata_question(q):
                    continue
                key = re.sub(r"\s+", " ", q.get("question", "")).strip().casefold()
                if key in seen:
                    continue
                grounded.append(q)
                seen.add(key)
                if len(grounded) >= count:
                    break

        for i, q in enumerate(grounded[:count], start=1):
            q["id"] = i

        return {
            **exam_data,
            "exam_title": exam_data.get("exam_title") or title or "امتحان المحاضرة",
            "total_questions": len(grounded[:count]),
            "questions": grounded[:count],
            "grounded_filtered": True,
        }

    def _parse_exam_json(
        self,
        raw: str,
        count: int,
        title: str,
        types: list[str],
        source_context: str = "",
    ) -> dict[str, Any]:
        """تحليل قوي لـ JSON الامتحان مع إزالة markdown واستخراج احتياطي."""
        parsed = self._extract_exam_json(raw)
        questions_raw: list[Any] = []
        if isinstance(parsed, dict):
            # النموذج قد يُرجع خطأ عند غياب السياق
            err = str(parsed.get("error") or "").strip().casefold()
            if err in ("missing_lecture_context", "context_missing", "no_context"):
                questions_raw = []
            else:
                questions_raw = parsed.get("questions") or parsed.get("Items") or []
                if not isinstance(questions_raw, list):
                    questions_raw = []
        elif isinstance(parsed, list):
            questions_raw = parsed

        normalized = self._normalize_exam_questions(
            questions_raw, count, types, source_context=source_context
        )

        # استخراج regex إن فشل JSON أو كانت الأسئلة فارغة/قليلة
        if len(normalized) < count:
            regex_qs = self._regex_extract_exam_questions(raw, count, types)
            if regex_qs:
                merged = normalized + self._normalize_exam_questions(
                    regex_qs, count, types, source_context=source_context
                )
                # إزالة التكرار حسب نص السؤال
                seen: set[str] = set()
                deduped: list[dict[str, Any]] = []
                for q in merged:
                    key = re.sub(r"\s+", " ", q.get("question", "")).strip().casefold()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    deduped.append(q)
                    if len(deduped) >= count:
                        break
                for i, q in enumerate(deduped, start=1):
                    q["id"] = i
                normalized = deduped

        # املأ الباقي من نص المحاضرة — لا تترك الواجهة بقالب فارغ أو شبه فارغ
        if len(normalized) < count and source_context.strip():
            fallback = self._fallback_exam_from_lecture(
                source_context, count, types, title
            )
            fb_questions = fallback.get("questions") or []
            if fb_questions:
                if not normalized:
                    return fallback
                seen = {
                    re.sub(r"\s+", " ", q.get("question", "")).strip().casefold()
                    for q in normalized
                }
                for q in fb_questions:
                    key = re.sub(r"\s+", " ", q.get("question", "")).strip().casefold()
                    if key in seen:
                        continue
                    normalized.append(q)
                    seen.add(key)
                    if len(normalized) >= count:
                        break
                for i, q in enumerate(normalized, start=1):
                    q["id"] = i

        if not normalized:
            # لا نُرجع قالباً فارغاً أبداً — سؤال مقالي واحد من النص الخام إن وُجد
            snippet = self.ensure_utf8_text(raw or source_context or "").strip()
            if snippet:
                normalized = [{
                    "id": 1,
                    "type": "essay" if "essay" in types else types[0],
                    "question": (
                        "لخّص أهم أفكار المحاضرة التالية وأجب باختصار: "
                        if self.detect_primary_language(snippet) != "en"
                        else "Summarize the key ideas from this lecture excerpt: "
                    ) + snippet[:400],
                    "options": ["صح", "خطأ"] if types[0] == "true_false" else (
                        None if types[0] == "essay" else ["أ", "ب", "ج", "د"]
                    ),
                    "correct_answer": "",
                    "explanation": "",
                    "points": 3,
                    "difficulty": "medium",
                }]

        exam_title = ""
        if isinstance(parsed, dict):
            exam_title = str(parsed.get("exam_title") or parsed.get("title") or "").strip()

        return {
            "exam_title": exam_title or title or "امتحان المحاضرة",
            "total_questions": len(normalized),
            "questions": normalized[:count],
            "fallback": bool(source_context) and len(questions_raw) == 0,
        }

    def _extract_exam_json(self, raw: str) -> Any:
        """استخراج JSON حتى لو داخل ```json أو نص إضافي."""
        text = self.ensure_utf8_text(raw).strip()
        if not text:
            return {}

        # إزالة أسوار markdown الشائعة
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()

        for candidate in (text, raw):
            candidate = self.ensure_utf8_text(candidate).strip()
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                if isinstance(data, (dict, list)):
                    return data
            except json.JSONDecodeError:
                pass

            start_obj, end_obj = candidate.find("{"), candidate.rfind("}")
            if start_obj >= 0 and end_obj > start_obj:
                try:
                    data = json.loads(candidate[start_obj : end_obj + 1])
                    if isinstance(data, (dict, list)):
                        return data
                except json.JSONDecodeError:
                    pass

            start_arr, end_arr = candidate.find("["), candidate.rfind("]")
            if start_arr >= 0 and end_arr > start_arr:
                try:
                    data = json.loads(candidate[start_arr : end_arr + 1])
                    if isinstance(data, list):
                        return {"questions": data}
                except json.JSONDecodeError:
                    pass
        return {}

    @classmethod
    def _map_exam_type(cls, raw_type: Any, fallback: str) -> str:
        value = str(raw_type or "").strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "mcq": "mcq",
            "multiple_choice": "mcq",
            "multiplechoice": "mcq",
            "choice": "mcq",
            "اختيار": "mcq",
            "اختيار_من_متعدد": "mcq",
            "true_false": "true_false",
            "truefalse": "true_false",
            "tf": "true_false",
            "boolean": "true_false",
            "صح_وخطأ": "true_false",
            "صح_خطأ": "true_false",
            "essay": "essay",
            "short_answer": "essay",
            "open": "essay",
            "مقالي": "essay",
        }
        mapped = aliases.get(value, value if value in ("mcq", "true_false", "essay") else "")
        return mapped or fallback

    def _normalize_exam_questions(
        self,
        questions_raw: list[Any],
        count: int,
        types: list[str],
        source_context: str = "",
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not isinstance(questions_raw, list):
            return normalized

        for i, item in enumerate(questions_raw):
            if len(normalized) >= count:
                break
            if isinstance(item, str):
                text = item.strip()
                if len(text) < 8:
                    continue
                q_type = types[i % len(types)]
                normalized.append(self._build_exam_question_dict(
                    i + 1, q_type, text, None, "", "", types
                ))
                continue
            if not isinstance(item, dict):
                continue

            q_text = str(
                item.get("question")
                or item.get("question_text")
                or item.get("text")
                or item.get("prompt")
                or item.get("q")
                or item.get("stem")
                or ""
            ).strip()
            if len(q_text) < 5:
                continue
            if self._is_metadata_noise_term(q_text):
                continue

            fallback_type = types[i % len(types)]
            q_type = self._map_exam_type(item.get("type"), fallback_type)
            if q_type not in types:
                q_type = fallback_type

            options = item.get("options")
            if options is None:
                options = item.get("choices") or item.get("answers")
            if isinstance(options, str):
                options = [o.strip() for o in re.split(r"[|\n;]", options) if o.strip()]
            if q_type == "mcq":
                if not isinstance(options, list) or len(options) < 2:
                    options = []
                options = [str(o).strip() for o in options if str(o).strip()]
                unique_opts = self._ensure_unique_mcq_options(
                    options,
                    source_context=source_context,
                    correct=str(
                        item.get("correct_answer")
                        or item.get("answer")
                        or item.get("correct")
                        or item.get("key")
                        or ""
                    ).strip(),
                    exclude_keys={self._option_identity_key(q_text)},
                )
                if not unique_opts:
                    # Try a full rebuild from lecture concepts
                    rebuilt = self._build_grounded_mcq(
                        source_context, i, types, lang=self.detect_primary_language(q_text or source_context)
                    )
                    if rebuilt and self._mcq_options_are_unique(rebuilt.get("options")):
                        normalized.append(rebuilt)
                    continue
                options = unique_opts
                if self._is_tautological_mcq(q_text, options, str(item.get("correct_answer") or "")):
                    rebuilt = self._build_grounded_mcq(
                        source_context, i, types, lang=self.detect_primary_language(q_text or source_context)
                    )
                    if rebuilt and not self._is_trivial_or_metadata_question(rebuilt):
                        normalized.append(rebuilt)
                    continue
            elif q_type == "true_false":
                lang = self.detect_primary_language(q_text)
                options = ["صح", "خطأ"] if lang != "en" else ["True", "False"]
            else:
                options = None

            correct = str(
                item.get("correct_answer")
                or item.get("answer")
                or item.get("correct")
                or item.get("key")
                or ""
            ).strip()
            if q_type == "mcq" and options:
                # Force correct_answer to match one unique option exactly
                opt_keys = {self._option_identity_key(o): o for o in options}
                c_key = self._option_identity_key(correct)
                if c_key in opt_keys:
                    correct = opt_keys[c_key]
                else:
                    correct = options[0]
            explanation = str(item.get("explanation") or item.get("rationale") or "").strip()
            source_span = str(
                item.get("source_span")
                or item.get("quote")
                or item.get("evidence")
                or ""
            ).strip()

            try:
                points = int(item.get("points") or 2)
            except (TypeError, ValueError):
                points = 2
            difficulty = str(item.get("difficulty") or "medium").strip().casefold()
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "medium"

            try:
                qid = int(item.get("id") or i + 1)
            except (TypeError, ValueError):
                qid = i + 1

            candidate = {
                "id": qid,
                "type": q_type,
                "question": q_text,
                "question_text": q_text,
                "options": options,
                "correct_answer": correct,
                "explanation": explanation,
                "source_span": source_span,
                "points": max(1, min(points, 5)),
                "difficulty": difficulty,
            }
            if q_type == "mcq" and (
                not self._mcq_options_are_unique(options)
                or self._is_trivial_or_metadata_question(candidate)
            ):
                continue
            normalized.append(candidate)

        for i, q in enumerate(normalized, start=1):
            q["id"] = i
        return normalized

    def _build_exam_question_dict(
        self,
        qid: int,
        q_type: str,
        question: str,
        options: list[str] | None,
        correct: str,
        explanation: str,
        types: list[str],
        source_span: str = "",
    ) -> dict[str, Any]:
        if q_type not in ("mcq", "true_false", "essay"):
            q_type = types[0] if types else "mcq"
        base = {
            "id": qid,
            "type": q_type,
            "question": question,
            "question_text": question,
            "correct_answer": correct,
            "explanation": explanation,
            "source_span": (source_span or "")[:180],
            "difficulty": "medium",
        }
        if q_type == "mcq":
            unique = self._ensure_unique_mcq_options(
                options,
                source_context="",
                correct=correct,
                exclude_keys={self._option_identity_key(question)},
            )
            if not unique:
                # Do not emit duplicate-padded options — caller should rebuild
                return {
                    **base,
                    "options": [],
                    "correct_answer": correct,
                    "points": 2,
                    "invalid_options": True,
                }
            ans = correct
            ans_key = self._option_identity_key(ans)
            for o in unique:
                if self._option_identity_key(o) == ans_key:
                    ans = o
                    break
            else:
                ans = unique[0]
            return {
                **base,
                "options": unique,
                "correct_answer": ans,
                "points": 2,
            }
        if q_type == "true_false":
            lang = self.detect_primary_language(question)
            opts = ["صح", "خطأ"] if lang != "en" else ["True", "False"]
            return {
                **base,
                "options": opts,
                "correct_answer": correct or opts[0],
                "points": 1,
            }
        return {
            **base,
            "type": "essay",
            "options": None,
            "points": 5,
        }

    def _regex_extract_exam_questions(
        self,
        raw: str,
        count: int,
        types: list[str],
    ) -> list[dict[str, Any]]:
        """استخراج أسئلة من نص حر أو JSON مكسور حتى لا تبقى الواجهة فارغة."""
        text = self.ensure_utf8_text(raw or "")
        found: list[dict[str, Any]] = []

        # حقول question داخل JSON حتى لو كان مكسوراً
        for m in re.finditer(
            r'"question"\s*:\s*"((?:[^"\\]|\\.){5,})"',
            text,
            flags=re.IGNORECASE,
        ):
            q_text = (
                m.group(1)
                .replace('\\"', '"')
                .replace("\\n", " ")
                .replace("\\t", " ")
                .replace("\\\\", "\\")
                .strip()
            )
            if len(q_text) >= 5:
                found.append({
                    "type": types[len(found) % len(types)],
                    "question": q_text,
                    "options": None,
                    "correct_answer": "",
                    "explanation": "",
                })
            if len(found) >= count:
                return found

        # ترقيم شائع: 1. السؤال ... أو السؤال 1:
        blocks = re.split(
            r"(?:^|\n)\s*(?:\d{1,2}[\.\)]\s+|Q\s*\d+\s*[:.\-]\s*|السؤال\s*\d+\s*[:.\-]?\s*)",
            text,
            flags=re.IGNORECASE,
        )
        for block in blocks:
            block = re.sub(r"\s+", " ", block).strip()
            # تجاهل المقاطع القصيرة أو غير النصية (مثل أخطاء التحليل)
            if len(block) < 40:
                continue
            if not re.search(r"[A-Za-z\u0600-\u06FF]{6,}", block):
                continue
            # تجاهل أسطر JSON الهيكلية
            if block.startswith("{") or '"exam_title"' in block[:40]:
                continue
            if block.casefold() in {"not json at all", "null", "undefined"}:
                continue
            q_type = types[len(found) % len(types)]
            options = None
            if q_type == "mcq":
                opts = re.findall(
                    r"(?:^|\s)(?:[A-Dأ-د]|[a-d])[\.\)\-:\s]\s*([^|\n]{2,80})",
                    block,
                )
                options = [o.strip() for o in opts[:4]] if opts else None
                question = re.split(
                    r"(?:^|\s)(?:[A-Dأ-د]|[a-d])[\.\)\-:\s]",
                    block,
                    maxsplit=1,
                )[0].strip()
            else:
                question = block[:500]
            if len(question) < 20:
                continue
            found.append({
                "type": q_type,
                "question": question,
                "options": options,
                "correct_answer": "",
                "explanation": "",
            })
            if len(found) >= count:
                break
        return found

    def _fallback_exam_from_lecture(
        self,
        source_context: str,
        count: int,
        types: list[str],
        title: str = "",
    ) -> dict[str, Any]:
        """أسئلة احتياطية مباشرة من مقاطع المحاضرة عند فشل النموذج/التحليل."""
        text = self.ensure_utf8_text(source_context or "").strip()
        if not text:
            return {
                "exam_title": title or "امتحان المحاضرة",
                "total_questions": 0,
                "questions": [],
                "fallback": True,
            }

        parts = [
            s.strip()
            for s in re.split(r"(?<=[.!?؟۔])\s+|\n+", text)
            if len(s.strip()) >= 25
        ]
        if not parts:
            parts = [
                text[i : i + 180].strip()
                for i in range(0, min(len(text), 900), 180)
                if text[i : i + 180].strip()
            ]

        lang = self.detect_primary_language(text)
        questions: list[dict[str, Any]] = []
        for i, part in enumerate(parts):
            if len(questions) >= count:
                break
            q_type = types[i % len(types)]
            snippet = re.sub(r"\s+", " ", part).strip()
            if len(snippet) > 220:
                snippet = snippet[:220].rstrip() + "…"

            if q_type == "mcq":
                mcq = self._build_grounded_mcq(text, i, types, lang=lang)
                if mcq:
                    questions.append(mcq)
                    continue
                # آخر ملاذ: 4 مقاطع حقيقية من المحاضرة كخيارات (بدون عبارات وصفية)
                pool = self._lecture_concept_pool(text)
                if len(pool) >= 4:
                    correct = pool[i % len(pool)]
                    others = [p for p in pool if p.casefold() != correct.casefold()][:3]
                    options = [correct, *others][:4]
                    rotated = options[i % 4 :] + options[: i % 4]
                    topic = correct if len(correct) <= 42 else correct[:42].rstrip() + "…"
                    if lang == "en":
                        q_text = (
                            f"According to the lecture, which choice correctly relates to «{topic}»?"
                        )
                        explanation = "The correct option is taken from the lecture content."
                    else:
                        q_text = (
                            f"وفقاً للمحاضرة، أيّ خيار يرتبط بشكل صحيح بالمفهوم: «{topic}»؟"
                        )
                        explanation = "الخيار الصحيح مأخوذ من محتوى المحاضرة."
                    questions.append(
                        self._build_exam_question_dict(
                            i + 1,
                            "mcq",
                            q_text,
                            rotated,
                            correct,
                            explanation,
                            types,
                            source_span=snippet[:180],
                        )
                    )
                else:
                    # حوّل إلى صح/خطأ بدل خيارات وصفية فارغة
                    if lang == "en":
                        q_text = f"True or False: {snippet}"
                        correct = "True"
                        explanation = "This statement is taken from the lecture content."
                    else:
                        q_text = f"صح أم خطأ: {snippet}"
                        correct = "صح"
                        explanation = "العبارة مأخوذة من محتوى المحاضرة."
                    questions.append(
                        self._build_exam_question_dict(
                            i + 1,
                            "true_false",
                            q_text,
                            None,
                            correct,
                            explanation,
                            types,
                            source_span=snippet,
                        )
                    )
            elif q_type == "true_false":
                if lang == "en":
                    q_text = f"True or False: {snippet}"
                    correct = "True"
                    explanation = "This statement is taken from the lecture content."
                else:
                    q_text = f"صح أم خطأ: {snippet}"
                    correct = "صح"
                    explanation = "العبارة مأخوذة من محتوى المحاضرة."
                questions.append(
                    self._build_exam_question_dict(
                        i + 1,
                        "true_false",
                        q_text,
                        None,
                        correct,
                        explanation,
                        types,
                        source_span=snippet,
                    )
                )
            else:
                if lang == "en":
                    q_text = f"Explain the following lecture idea in your own words: {snippet}"
                    correct = "Mention the main concept, related terms, and one practical implication."
                else:
                    q_text = f"اشرح بأسلوبك الفكرة التالية من المحاضرة: {snippet}"
                    correct = "اذكر المفهوم الأساسي والمصطلحات المرتبطة وأثراً عملياً واحداً."
                questions.append(
                    self._build_exam_question_dict(
                        i + 1,
                        "essay",
                        q_text,
                        None,
                        correct,
                        "",
                        types,
                        source_span=snippet,
                    )
                )

        return {
            "exam_title": title or ("Lecture quiz" if lang == "en" else "امتحان المحاضرة"),
            "total_questions": len(questions),
            "questions": questions,
            "fallback": True,
        }


# ==========================================
# دالة مساعدة للحصول على نسخة الخدمة
# ==========================================

_default_service: AcademicAIService | None = None


def get_ai_service() -> AcademicAIService:
    """إرجاع نسخة مشتركة من خدمة الذكاء الاصطناعي"""
    global _default_service
    if _default_service is None:
        _default_service = AcademicAIService()
    return _default_service
