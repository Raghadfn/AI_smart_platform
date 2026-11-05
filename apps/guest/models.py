"""
نماذج وضع الزائر - رفع ملفات PDF مؤقتة
Guest mode models - temporary PDF uploads
"""
import uuid

from django.db import models


def guest_pdf_path(instance, filename):
    """مسار حفظ ملف PDF للزائر"""
    return f"guest/{instance.session_key}/{filename}"


class GuestUpload(models.Model):
    """ملف PDF مرفوع من زائر غير مسجل"""

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        PROCESSING = "processing", "قيد المعالجة"
        READY = "ready", "جاهز"
        FAILED = "failed", "فشل"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=64, db_index=True, verbose_name="مفتاح الجلسة")
    original_filename = models.CharField(max_length=255, verbose_name="اسم الملف الأصلي")
    pdf_file = models.FileField(upload_to=guest_pdf_path, verbose_name="ملف PDF")
    extracted_text = models.TextField(blank=True, verbose_name="النص المستخرج")
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        verbose_name="حالة المعالجة",
    )
    processing_error = models.TextField(blank=True, verbose_name="خطأ المعالجة")
    expires_at = models.DateTimeField(verbose_name="تاريخ انتهاء الصلاحية")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "رفع زائر"
        verbose_name_plural = "رفوعات الزوار"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_key", "expires_at"]),
        ]

    def __str__(self):
        return self.original_filename


class GuestAIResult(models.Model):
    """نتيجة ذكاء اصطناعي لملف زائر"""

    class ResultType(models.TextChoices):
        SUMMARY = "summary", "تلخيص"
        QA = "qa", "سؤال وجواب"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(
        GuestUpload,
        on_delete=models.CASCADE,
        related_name="ai_results",
        verbose_name="الملف المرفوع",
    )
    result_type = models.CharField(
        max_length=20,
        choices=ResultType.choices,
        verbose_name="نوع النتيجة",
    )
    input_params = models.JSONField(default=dict, verbose_name="معاملات الإدخال")
    result_data = models.JSONField(default=dict, verbose_name="بيانات النتيجة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "نتيجة ذكاء اصطناعي (زائر)"
        verbose_name_plural = "نتائج الذكاء الاصطناعي (زوار)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.upload.original_filename} - {self.get_result_type_display()}"
