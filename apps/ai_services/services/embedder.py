"""
تضمين النصوص وإدارة أجزاء المحاضرات
Text embedding and lecture chunk management
"""
import logging

from django.conf import settings
from django.db import transaction

from apps.lectures.models import Lecture, LectureChunk

from .chunker import chunk_text, estimate_tokens
from .openai_client import create_embedding

logger = logging.getLogger(__name__)


def ensure_lecture_chunks(lecture: Lecture, generate_embeddings: bool = True) -> int:
    """
    التأكد من وجود أجزاء نصية للمحاضرة
    Ensure lecture has text chunks (and optionally embeddings)
    Returns number of chunks
    """
    if not lecture.content_text.strip():
        return 0

    existing = lecture.chunks.count()
    if existing > 0:
        return existing

    chunks = chunk_text(lecture.content_text)
    if not chunks:
        return 0

    with transaction.atomic():
        lecture.chunks.all().delete()
        for idx, chunk in enumerate(chunks):
            embedding = None
            if generate_embeddings and settings.HF_TOKEN:
                try:
                    embedding = create_embedding(chunk)
                except Exception as exc:
                    logger.warning("فشل إنشاء التضمين للجزء %s: %s", idx, exc)

            LectureChunk.objects.create(
                lecture=lecture,
                chunk_index=idx,
                chunk_text=chunk,
                embedding=embedding,
                token_count=estimate_tokens(chunk),
            )

    lecture.processing_status = Lecture.ProcessingStatus.READY
    lecture.save(update_fields=["processing_status", "updated_at"])
    return len(chunks)
