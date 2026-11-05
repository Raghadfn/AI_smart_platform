"""
نماذج تتبع تقدم الطلاب في المحاضرات
Student lecture progress tracking models
"""
import uuid

from django.conf import settings
from django.db import models

from apps.lectures.models import Lecture


class LectureProgress(models.Model):
    """تقدم الطالب في محاضرة معينة"""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "لم يبدأ"
        IN_PROGRESS = "in_progress", "قيد التقدم"
        COMPLETED = "completed", "مكتمل"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lecture_progress",
        verbose_name="الطالب",
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        related_name="student_progress",
        verbose_name="المحاضرة",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        verbose_name="الحالة",
    )
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="نسبة التقدم",
    )
    last_accessed_at = models.DateTimeField(auto_now=True, verbose_name="آخر وصول")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "تقدم محاضرة"
        verbose_name_plural = "تقدم المحاضرات"
        unique_together = [["user", "lecture"]]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.lecture.title_ar} ({self.progress_percent}%)"
