"""
استخراج النص من PDF المحاضرات وربطه بحقل content_text
Lecture PDF text extraction for AI/RAG (PyMuPDF + Arabic reshape preview)
"""
from __future__ import annotations

import logging

from apps.lectures.models import Lecture

logger = logging.getLogger(__name__)


def ensure_lecture_text(lecture: Lecture, *, force: bool = False) -> str:
    """
    ضمان وجود نص مستخرج للمحاضرة.
    يعيد الاستخراج تلقائياً إذا كان النص المحفوظ تالفاً لـ Groq
    (presentation forms / unicode escapes).
    """
    from apps.guest.utils.pdf_extractor import (
        as_clean_utf8,
        looks_corrupted_arabic,
        to_ai_utf8,
    )

    existing = to_ai_utf8(lecture.content_text or "").strip()
    needs_refresh = bool(getattr(lecture.pdf_file, "name", None)) and (
        force or not existing or looks_corrupted_arabic(lecture.content_text or "")
    )

    if existing and not needs_refresh:
        return existing.encode("utf-8").decode("utf-8")

    if not getattr(lecture.pdf_file, "name", None):
        return existing.encode("utf-8").decode("utf-8") if existing else ""

    lecture.processing_status = Lecture.ProcessingStatus.PROCESSING
    lecture.processing_error = ""
    lecture.save(update_fields=["processing_status", "processing_error", "updated_at"])

    try:
        from apps.guest.utils.pdf_extractor import PDFExtractor

        result = PDFExtractor.extract_text(file_path=lecture.pdf_file.path)
        text = to_ai_utf8(result.get("text") or "").strip()
        if not text:
            raise ValueError("الملف لا يحتوي على نص قابل للاستخراج.")

        # طباعة معاينة إضافية بعد الحفظ
        print(text[:500])

        lecture.content_text = text
        lecture.processing_status = Lecture.ProcessingStatus.READY
        lecture.processing_error = ""
        lecture.save(
            update_fields=[
                "content_text",
                "processing_status",
                "processing_error",
                "updated_at",
            ]
        )
        logger.info(
            "Extracted %d chars from lecture %s via %s",
            len(text),
            lecture.id,
            result.get("method", "unknown"),
        )
        return text.encode("utf-8").decode("utf-8")
    except Exception as exc:
        logger.exception("PDF extraction failed for lecture %s", lecture.id)
        lecture.processing_status = Lecture.ProcessingStatus.FAILED
        lecture.processing_error = str(exc)[:2000]
        lecture.save(
            update_fields=["processing_status", "processing_error", "updated_at"]
        )
        return as_clean_utf8(existing)
