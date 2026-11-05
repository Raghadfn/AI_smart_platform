"""
نماذج نتائج الذكاء الاصطناعي المحفوظة
Saved AI results models
"""
import uuid

from django.conf import settings
from django.db import models

from apps.lectures.models import Lecture


class SavedAIResult(models.Model):
    """نتيجة ذكاء اصطناعي محفوظة للمستخدم المسجل"""

    class ResultType(models.TextChoices):
        TRANSLATION = "translation", "ترجمة"
        SUMMARY = "summary", "تلخيص"
        QA = "qa", "سؤال وجواب"
        EXAM = "exam", "أسئلة امتحان"
        ILLUSTRATION = "illustration", "رسم توضيحي"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_ai_results",
        verbose_name="المستخدم",
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="saved_results",
        verbose_name="المحاضرة",
    )
    result_type = models.CharField(
        max_length=20,
        choices=ResultType.choices,
        verbose_name="نوع النتيجة",
    )
    title = models.CharField(max_length=300, verbose_name="العنوان")
    input_params = models.JSONField(default=dict, verbose_name="معاملات الإدخال")
    result_data = models.JSONField(default=dict, verbose_name="بيانات النتيجة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "نتيجة محفوظة"
        verbose_name_plural = "النتائج المحفوظة"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "result_type"]),
            models.Index(fields=["user", "lecture"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_result_type_display()})"


class ExamAttempt(models.Model):
    """محاولة امتحان تفاعلي - تتبع إجابات الطالب والدرجة"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
        verbose_name="الطالب",
    )
    saved_result = models.ForeignKey(
        SavedAIResult,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="مجموعة الأسئلة",
    )
    answers = models.JSONField(default=dict, verbose_name="إجابات الطالب")
    score_percent = models.PositiveSmallIntegerField(default=0, verbose_name="النسبة المئوية")
    correct_count = models.PositiveSmallIntegerField(default=0, verbose_name="إجابات صحيحة")
    total_gradable = models.PositiveSmallIntegerField(default=0, verbose_name="أسئلة قابلة للتصحيح")
    grading_details = models.JSONField(default=list, verbose_name="تفاصيل التصحيح")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسليم")

    class Meta:
        verbose_name = "محاولة امتحان"
        verbose_name_plural = "محاولات الامتحان"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["user", "saved_result"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.score_percent}% ({self.saved_result.title})"
