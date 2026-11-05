"""
محرك الإجابة على الأسئلة (RAG)
Question answering engine with RAG
"""
import logging
import re

from django.conf import settings
from django.db import connection

from apps.lectures.models import Lecture, LectureChunk

from .chunker import chunk_text
from .embedder import ensure_lecture_chunks
from .openai_client import chat_completion, create_embedding

logger = logging.getLogger(__name__)


def answer_question(lecture: Lecture, question: str) -> dict:
    """
    الإجابة على سؤال بناءً على محتوى المحاضرة
    Answer a question based on lecture content using RAG
    """
    if not lecture.content_text.strip():
        raise ValueError("لا يوجد محتوى نصي للمحاضرة.")

    ensure_lecture_chunks(lecture, generate_embeddings=bool(settings.HF_TOKEN))

    chunks = _retrieve_relevant_chunks(lecture, question)
    context = "\n\n---\n\n".join(chunks)

    system_prompt = """You are a bilingual academic assistant fluent in both Arabic and English.
You must analyze the provided lecture context in whichever language it is written (Arabic or English) and respond accurately.
Always reply in the same language the student uses to ask their question.

Answer the student's question using ONLY the provided lecture content.
- If the answer is not in the content, say so clearly in the student's language.
- Treat Arabic and English (including mixed lectures with English technical terms) as equally authoritative.
- Preserve technical terminology accurately."""

    answer, tokens = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Lecture content / محتوى المحاضرة:\n{context}\n\n---\n\n"
                    f"Student question / سؤال الطالب: {question}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    return {
        "question": question,
        "answer": answer.strip(),
        "sources_count": len(chunks),
        "tokens_used": tokens,
    }


def _retrieve_relevant_chunks(lecture: Lecture, question: str) -> list[str]:
    """استرجاع الأجزاء الأكثر صلة بالسؤال"""
    db_chunks = list(lecture.chunks.order_by("chunk_index"))

    if not db_chunks:
        return chunk_text(lecture.content_text)[: settings.AI_TOP_K_CHUNKS]

    # محاولة البحث الدلالي مع pgvector
    if connection.vendor == "postgresql" and settings.HF_TOKEN:
        try:
            vector_chunks = _vector_search(lecture, question)
            if vector_chunks:
                return vector_chunks
        except Exception as exc:
            logger.warning("فشل البحث الدلالي، استخدام البحث النصي: %s", exc)

    # بديل: البحث النصي البسيط
    return _keyword_search(db_chunks, question)


def _vector_search(lecture: Lecture, question: str, top_k: int | None = None) -> list[str]:
    """بحث دلالي باستخدام pgvector"""
    from pgvector.django import CosineDistance

    top_k = top_k or settings.AI_TOP_K_CHUNKS
    query_embedding = create_embedding(question)

    chunks = (
        LectureChunk.objects.filter(lecture=lecture, embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:top_k]
    )
    return [c.chunk_text for c in chunks]


def _keyword_search(chunks: list[LectureChunk], question: str, top_k: int | None = None) -> list[str]:
    """بحث نصي ثنائي اللغة بالكلمات المفتاحية"""
    top_k = top_k or settings.AI_TOP_K_CHUNKS
    token_re = re.compile(
        r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*|"
        r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
        re.UNICODE,
    )
    stop = {
        "ما", "هل", "من", "في", "على", "إلى", "عن", "هو", "هي",
        "the", "is", "a", "an", "what", "how", "why", "when", "where",
        "and", "or", "of", "to", "in", "on", "for", "with",
    }
    question_words = {
        m.group(0)
        for m in token_re.finditer(question.casefold())
        if m.group(0) not in stop and len(m.group(0)) > 1
    }

    if not question_words:
        return [c.chunk_text for c in chunks[:top_k]]

    scored = []
    for chunk in chunks:
        text_cf = chunk.chunk_text.casefold()
        score = sum(1 for w in question_words if w in text_cf)
        scored.append((score, chunk.chunk_text))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [text for score, text in scored[:top_k] if score > 0]

    if not top:
        return [c.chunk_text for c in chunks[:top_k]]

    return top
