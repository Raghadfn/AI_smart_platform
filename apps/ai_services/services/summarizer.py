"""
خدمة تلخيص المحاضرات
Lecture summarization service
"""
from .openai_client import chat_completion

LENGTH_INSTRUCTIONS = {
    "short": "اكتب ملخصاً قصيراً جداً (3-5 جمل فقط) يلخص أهم النقاط.",
    "medium": "اكتب ملخصاً متوسط الطول (فقرة أو فقرتين) يغطي النقاط الرئيسية.",
    "detailed": "اكتب ملخصاً مفصلاً منظماً بنقاط يغطي جميع المواضيع المهمة في المحاضرة.",
}


def summarize_content(content: str, length: str = "medium", title: str = "") -> dict:
    """
    تلخيص محتوى المحاضرة
    Summarize lecture content
    """
    if length not in LENGTH_INSTRUCTIONS:
        length = "medium"

    instruction = LENGTH_INSTRUCTIONS[length]
    max_content = 12000
    truncated = len(content) > max_content
    content_to_use = content[:max_content] if truncated else content

    system_prompt = f"""أنت مساعد تعليمي متخصص في هندسة المعلوماتية.
{instruction}
اكتب الملخص باللغة العربية بأسلوب واضح ومنظم."""

    user_prompt = f"عنوان المحاضرة: {title}\n\nمحتوى المحاضرة:\n{content_to_use}"
    if truncated:
        user_prompt += "\n\n[ملاحظة: تم اختصار المحتوى بسبب الطول]"

    summary, tokens = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2048 if length == "detailed" else 1024,
    )

    return {
        "summary": summary.strip(),
        "length": length,
        "length_label": {"short": "قصير", "medium": "متوسط", "detailed": "مفصل"}[length],
        "tokens_used": tokens,
        "truncated": truncated,
    }
