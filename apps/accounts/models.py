"""
نماذج المستخدمين وملفات الطلاب
User and student profile models
"""
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """نموذج المستخدم - الطلاب والمسؤولون"""

    class Role(models.TextChoices):
        STUDENT = "student", "طالب"
        ADMIN = "admin", "مسؤول"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="الدور",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    @property
    def is_student(self):
        """هل المستخدم طالب؟"""
        return self.role == self.Role.STUDENT

    @property
    def is_platform_admin(self):
        """هل المستخدم مسؤول المنصة؟"""
        return self.role == self.Role.ADMIN


class StudentProfile(models.Model):
    """ملف الطالب الشخصي"""

    class PreferredLanguage(models.TextChoices):
        ARABIC = "ar", "العربية"
        ENGLISH = "en", "English"
        KURDISH = "ku", "کوردی"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="المستخدم",
    )
    full_name_ar = models.CharField(max_length=200, verbose_name="الاسم الكامل بالعربية")
    student_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="الرقم الجامعي",
    )
    preferred_language = models.CharField(
        max_length=5,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.ARABIC,
        verbose_name="اللغة المفضلة",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "ملف طالب"
        verbose_name_plural = "ملفات الطلاب"

    def __str__(self):
        return self.full_name_ar
