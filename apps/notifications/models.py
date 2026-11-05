"""
نماذج الإشعارات
Notification models
"""
import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """إشعار للطلاب"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="المستخدم",
        help_text="اتركه فارغاً للإرسال لجميع الطلاب",
    )
    title_ar = models.CharField(max_length=200, verbose_name="العنوان")
    message_ar = models.TextField(verbose_name="الرسالة")
    link = models.CharField(max_length=500, blank=True, verbose_name="الرابط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title_ar


class NotificationRead(models.Model):
    """تتبع قراءة الإشعارات لكل مستخدم"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="read_by",
        verbose_name="الإشعار",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="read_notifications",
        verbose_name="المستخدم",
    )
    read_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ القراءة")

    class Meta:
        verbose_name = "قراءة إشعار"
        verbose_name_plural = "قراءات الإشعارات"
        unique_together = [["notification", "user"]]

    def __str__(self):
        return f"{self.user.username} قرأ: {self.notification.title_ar}"
