"""
أدوات مساعدة لخدمات الذكاء الاصطناعي
AI services utility functions
"""
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.ai_services.exceptions import LectureContentError, RateLimitExceededError
from apps.ai_services.models import SavedAIResult
from apps.lectures.models import Lecture
from apps.lectures.services.text_extractor import ensure_lecture_text

logger = logging.getLogger(__name__)


def get_lecture_or_404(year_slug: str, subject_slug: str, lecture_slug: str) -> Lecture:
    """جلب محاضرة منشورة أو رفع استثناء"""
    try:
        return Lecture.objects.select_related("subject", "subject__semester", "subject__semester__year").get(
            subject__semester__year__slug=year_slug,
            subject__slug=subject_slug,
            slug=lecture_slug,
            is_published=True,
        )
    except Lecture.DoesNotExist as exc:
        from rest_framework.exceptions import NotFound
        raise NotFound("المحاضرة غير موجودة أو غير منشورة.") from exc


def get_lecture_content(lecture: Lecture) -> str:
    """
    جلب محتوى المحاضرة النصي للـ RAG كنص UTF-8 نظيف لـ Groq.
    """
    from apps.guest.utils.pdf_extractor import looks_corrupted_arabic, to_ai_utf8

    content = to_ai_utf8(ensure_lecture_text(lecture)).strip()
    if getattr(lecture.pdf_file, "name", None) and (
        not content or looks_corrupted_arabic(lecture.content_text or "")
    ):
        content = to_ai_utf8(ensure_lecture_text(lecture, force=True)).strip()

    if not content:
        raise LectureContentError(
            "لا يوجد محتوى نصي متاح لهذه المحاضرة. ارفع PDF نصي أو الصق المحتوى في لوحة الإدارة."
        )
    return content.encode("utf-8").decode("utf-8")


def check_rate_limit(user, is_guest: bool = False) -> None:
    """التحقق من حد معدل الطلبات"""
    limit = settings.AI_RATE_LIMIT_GUEST if is_guest else settings.AI_RATE_LIMIT_STUDENT
    if is_guest:
        cache_key = f"ai_rate_guest_{user}"
    else:
        cache_key = f"ai_rate_user_{user.id}"

    count = cache.get(cache_key, 0)
    if count >= limit:
        raise RateLimitExceededError(limit)

    cache.set(cache_key, count + 1, timeout=3600)


def save_ai_result(
    user,
    lecture: Lecture | None,
    result_type: str,
    title: str,
    input_params: dict,
    result_data: dict,
) -> SavedAIResult:
    """حفظ نتيجة الذكاء الاصطناعي للمستخدم"""
    return SavedAIResult.objects.create(
        user=user,
        lecture=lecture,
        result_type=result_type,
        title=title,
        input_params=input_params,
        result_data=result_data,
    )


def build_ai_response(
    data: dict,
    saved_result: SavedAIResult | None = None,
) -> dict[str, Any]:
    """بناء استجابة API موحدة"""
    response = {
        "success": True,
        "data": data,
        "tokens_used": data.get("tokens_used", 0),
    }
    if saved_result:
        response["saved_result_id"] = str(saved_result.id)
    return response


def _normalize_answer(value: str) -> str:
    """تطبيع الإجابة للمقارنة"""
    return str(value).strip().lower().replace(" ", "")


def grade_exam_answers(questions: list[dict], answers: dict) -> dict:
    """
    تصحيح تلقائي لأسئلة MCQ وصح/خطأ
    Returns score summary with per-question grading details
    """
    details = []
    correct = 0
    gradable = 0

    for q in questions:
        q_id = str(q.get("id", ""))
        q_type = q.get("type", "mcq")
        user_answer = answers.get(q_id, answers.get(int(q_id) if q_id.isdigit() else q_id, ""))
        correct_answer = q.get("correct_answer", "")

        if q_type == "essay":
            details.append({
                "question_id": q.get("id"),
                "type": q_type,
                "question": q.get("question", ""),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": None,
                "graded": False,
                "explanation": q.get("explanation", ""),
            })
            continue

        gradable += 1
        is_correct = _normalize_answer(user_answer) == _normalize_answer(correct_answer)
        if is_correct:
            correct += 1

        details.append({
            "question_id": q.get("id"),
            "type": q_type,
            "question": q.get("question", ""),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "graded": True,
            "explanation": q.get("explanation", ""),
        })

    score_percent = round((correct / gradable) * 100) if gradable else 0

    return {
        "score_percent": score_percent,
        "correct_count": correct,
        "total_gradable": gradable,
        "total_questions": len(questions),
        "grading_details": details,
    }
