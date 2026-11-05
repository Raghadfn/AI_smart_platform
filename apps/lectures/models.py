"""
نماذج المحاضرات وأجزاء النص للبحث الدلالي
Lecture models and text chunks for semantic search (RAG)
"""
import uuid

from django.db import models
from pgvector.django import VectorField

from apps.curriculum.models import Subject


def lecture_pdf_path(instance, filename):
    """مسار حفظ ملف PDF للمحاضرة"""
    return f"lectures/{instance.subject.semester.year.slug}/{instance.subject.slug}/{filename}"


class Lecture(models.Model):
    """المحاضرة الدراسية"""

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        PROCESSING = "processing", "قيد المعالجة"
        READY = "ready", "جاهز"
        FAILED = "failed", "فشل"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="lectures",
        verbose_name="المادة",
    )
    title_ar = models.CharField(max_length=300, verbose_name="العنوان بالعربية")
    title_en = models.CharField(max_length=300, blank=True, verbose_name="العنوان بالإنجليزية")
    slug = models.SlugField(max_length=150, verbose_name="الرابط")
    content_text = models.TextField(blank=True, verbose_name="نص المحاضرة المستخرج")
    pdf_file = models.FileField(
        upload_to=lecture_pdf_path,
        blank=True,
        null=True,
        verbose_name="ملف PDF",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="مدة القراءة (دقيقة)",
    )
    is_published = models.BooleanField(default=True, verbose_name="منشور")
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        verbose_name="حالة المعالجة",
    )
    processing_error = models.TextField(blank=True, verbose_name="خطأ المعالجة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "محاضرة"
        verbose_name_plural = "المحاضرات"
        ordering = ["subject__semester__year__order", "subject__order", "order"]
        unique_together = [["subject", "slug"]]
        indexes = [
            models.Index(fields=["is_published", "processing_status"]),
        ]

    def __str__(self):
        return self.title_ar


class LectureChunk(models.Model):
    """
    جزء نصي من المحاضرة مع تضمين متجهي (embedding)
    يُستخدم للبحث الدلالي والإجابة على الأسئلة (RAG)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="المحاضرة",
    )
    chunk_index = models.PositiveIntegerField(verbose_name="رقم الجزء")
    chunk_text = models.TextField(verbose_name="نص الجزء")
    embedding = VectorField(dimensions=1536, null=True, blank=True, verbose_name="التضمين المتجهي")
    token_count = models.PositiveIntegerField(default=0, verbose_name="عدد الرموز")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "جزء محاضرة"
        verbose_name_plural = "أجزاء المحاضرات"
        ordering = ["lecture", "chunk_index"]
        unique_together = [["lecture", "chunk_index"]]
        # فهرس HNSW يُنشأ في هجرة PostgreSQL فقط (0002_postgres_vector_index)

    def __str__(self):
        return f"{self.lecture.title_ar} - جزء {self.chunk_index}"
