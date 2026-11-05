"""
تقسيم النصوص إلى أجزاء للمعالجة والبحث
Text chunking utilities (Arabic + English aware)
"""
import re
import unicodedata

from django.conf import settings

# حدود جمل عربية وإنجليزية معاً
_SENTENCE_SEPS = ("\n\n", "\n", ". ", "。", "! ", "? ", "؟ ", "؛ ", "; ")


def _ensure_utf8(text: str | bytes | None) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    elif not isinstance(text, str):
        text = str(text)
    text = "".join(
        ch for ch in text if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 0xFEFF)
    )
    return unicodedata.normalize("NFC", text)


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """
    تقسيم النص إلى أجزاء متداخلة مع احترام نهايات الجمل العربية/الإنجليزية
    Split text into overlapping chunks without stripping Arabic characters
    """
    text = _ensure_utf8(text).strip()
    if not text:
        return []

    chunk_size = chunk_size or settings.AI_CHUNK_SIZE
    overlap = overlap or settings.AI_CHUNK_OVERLAP

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # محاولة القطع عند نهاية جملة (عربي/إنجليزي)
        if end < len(text):
            for sep in _SENTENCE_SEPS:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    chunk = chunk[: last_sep + len(sep)]
                    end = start + len(chunk)
                    break

        piece = chunk.strip()
        if piece:
            chunks.append(piece)
        start = end - overlap if end < len(text) else end

    return [c for c in chunks if c]


def estimate_tokens(text: str) -> int:
    """
    تقدير عدد الرموز للنصوص المختلطة عربي/إنجليزي.
    العربية غالباً تستهلك tokens أكثر قليلاً من الإنجليزية لكل حرف.
    """
    safe = _ensure_utf8(text)
    if not safe:
        return 1
    arabic_chars = len(re.findall(r"[\u0600-\u06FF]", safe))
    other_chars = max(0, len(safe) - arabic_chars)
    # تقريب: ~2 chars/token للعربي، ~4 للإنجليزي/أرقام
    return max(1, (arabic_chars + 1) // 2 + (other_chars + 3) // 4)
