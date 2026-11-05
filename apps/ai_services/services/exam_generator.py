"""
مولّد أسئلة الامتحان — مسار بسيط ومباشر
Simple high-quality exam generator
"""
import json
import re

from .openai_client import chat_completion

EXAM_TYPE_LABELS = {
    "mcq": "اختيار من متعدد",
    "true_false": "صح وخطأ",
    "essay": "مقالي",
}


def _option_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def _dedupe_options(options: list) -> list[str] | None:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in options or []:
        text = str(raw).strip()
        if not text:
            continue
        key = _option_key(text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(text)
    if len(unique) != 4:
        return None
    return unique


def generate_exam(
    content: str,
    types: list[str] | None = None,
    count: int = 5,
    title: str = "",
) -> dict:
    """إنشاء أسئلة امتحان MCQ مع احترام عدد الأسئلة المطلوب."""
    num_questions = max(1, min(int(count or 5), 20))
    content_to_use = (content or "").strip()
    # حد عملي آمن فقط للمستندات الضخمة جداً
    if len(content_to_use) > 10000:
        content_to_use = content_to_use[:10000]

    system_prompt = (
        "You are an expert professor. Read the lecture content and create exact "
        f"{num_questions} high-quality multiple-choice questions. "
        "Write the question, all 4 options, and correct_answer in Modern Standard Arabic. "
        "Keep English technical acronyms inside Arabic when needed. "
        "Output ONLY a valid JSON array like this:\n"
        '[{"question": "سؤال بالعربية؟", "options": ["خيار ١", "خيار ٢", "خيار ٣", "خيار ٤"], "correct_answer": "خيار ١"}]'
    )
    user_prompt = (
        f"عنوان المحاضرة: {title or 'بدون عنوان'}\n\n"
        f"محتوى المحاضرة:\n{content_to_use}\n\n"
        f"أنشئ بالضبط {num_questions} أسئلة. السؤال والخيارات بالعربية فقط. "
        f"Output ONLY a valid JSON array."
    )

    result, tokens = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    try:
        parsed = json.loads(result)
        if isinstance(parsed, list):
            questions = parsed
        elif isinstance(parsed, dict):
            questions = parsed.get("questions") or parsed.get("Items") or []
        else:
            questions = []
    except json.JSONDecodeError:
        questions = []

    normalized = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        stem = str(q.get("question") or q.get("question_text") or "").strip()
        if not stem:
            continue
        unique = _dedupe_options(q.get("options") if isinstance(q.get("options"), list) else [])
        if not unique:
            continue
        correct = str(q.get("correct_answer") or "").strip()
        keys = {_option_key(o): o for o in unique}
        correct = keys.get(_option_key(correct), unique[0])
        normalized.append({
            "type": "mcq",
            "question": stem,
            "question_text": stem,
            "options": unique,
            "correct_answer": correct,
            "explanation": str(q.get("explanation") or "").strip(),
        })
        if len(normalized) >= num_questions:
            break

    return {
        "questions": normalized[:num_questions],
        "types": ["mcq"],
        "count": len(normalized[:num_questions]),
        "tokens_used": tokens,
    }
