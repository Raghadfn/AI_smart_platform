"""
استثناءات خدمات الذكاء الاصطناعي
AI services exceptions
"""


class AIServiceError(Exception):
    """خطأ عام في خدمة الذكاء الاصطناعي"""

    def __init__(self, message: str, code: str = "ai_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class HFNotConfiguredError(AIServiceError):
    def __init__(self):
        super().__init__(
                "مفتاح Hugging Face غير مُعدّ. أضف HF_TOKEN أو HF_TOKENS إلى ملف .env",
            code="hf_not_configured",
        )


# aliases للتوافق مع الكود القديم
GroqNotConfiguredError = HFNotConfiguredError
OpenAINotConfiguredError = HFNotConfiguredError


class RateLimitExceededError(AIServiceError):
    def __init__(self, limit: int):
        super().__init__(
            f"تجاوزت الحد المسموح ({limit} طلب/ساعة). حاول لاحقاً.",
            code="rate_limit_exceeded",
        )


class HFRateLimitExhaustedError(AIServiceError):
    """Hugging Face مشغول (503 model loading / rate limit بعد إعادة المحاولة)"""

    DEFAULT_MESSAGE_AR = (
        "المساعد يُعالج العديد من الطلبات حالياً. "
        "يرجى الانتظار قليلاً قبل طرح سؤالك التالي."
    )
    DEFAULT_MESSAGE_EN = (
        "The assistant is processing many requests right now. "
        "Please wait a moment before asking your next question."
    )

    def __init__(self, message: str | None = None):
        super().__init__(
            message or self.DEFAULT_MESSAGE_AR,
            code="hf_rate_limited",
        )


# alias للتوافق مع الكود القديم
GroqRateLimitExhaustedError = HFRateLimitExhaustedError


class LectureContentError(AIServiceError):
    def __init__(self, message: str = "لا يوجد محتوى نصي متاح لهذه المحاضرة."):
        super().__init__(message, code="no_content")
