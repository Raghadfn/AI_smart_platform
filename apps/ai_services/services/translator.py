"""
خدمة ترجمة المحاضرات
Lecture translation service
"""

from .openai_client import chat_completion

LANGUAGE_NAMES = {
    "ar": "العربية",
    "en": "الإنجليزية",
}


def translate_content(content: str, target_lang: str, title: str = "") -> dict:
    """
    ترجمة محتوى المحاضرة إلى اللغة المطلوبة
    Translate lecture content to target language
    """
    if target_lang not in LANGUAGE_NAMES:
        raise ValueError(f"لغة غير مدعومة: {target_lang}")

    target_name = LANGUAGE_NAMES[target_lang]

    # للنصوص الطويلة: ترجمة على دفعات
    max_chars = 6000
    if len(content) <= max_chars:
        translated, tokens = _translate_chunk(content, target_name, title)
        return {
            "translated_text": translated,
            "target_language": target_lang,
            "target_language_name": target_name,
            "tokens_used": tokens,
            "truncated": False,
        }

    # ترجمة أجزاء للنصوص الطويلة
    from .chunker import chunk_text

    chunks = chunk_text(content, chunk_size=max_chars, overlap=0)
    translated_parts = []
    total_tokens = 0
    for i, chunk in enumerate(chunks[:5]):  # حد أقصى 5 أجزاء
        part, tokens = _translate_chunk(chunk, target_name, title if i == 0 else "")
        translated_parts.append(part)
        total_tokens += tokens

    return {
        "translated_text": "\n\n".join(translated_parts),
        "target_language": target_lang,
        "target_language_name": target_name,
        "tokens_used": total_tokens,
        "truncated": len(chunks) > 5,
    }


def _translate_chunk(text: str, target_language: str, title: str = "") -> tuple[str, int]:
    """ترجمة جزء واحد من النص"""
    system_prompt = f"""أنت مترجم أكاديمي متخصص في هندسة المعلوماتية.
ترجم النص التالي إلى {target_language} بدقة مع الحفاظ على المصطلحات التقنية.
أعد النص المترجم فقط بدون شرح."""

    user_content = text
    if title:
        user_content = f"عنوان المحاضرة: {title}\n\n{text}"

    result, tokens = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    return result.strip(), tokens
