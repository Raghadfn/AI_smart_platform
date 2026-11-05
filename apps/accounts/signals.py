"""
إشارات تلقائية لإنشاء ملفات الطلاب
Signals for automatic student profile creation
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StudentProfile, User


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """
    إنشاء ملف طالب تلقائياً عند إنشاء مستخدم بدور طالب
    Auto-create student profile when a student user is created
    """
    if created and instance.role == User.Role.STUDENT:
        StudentProfile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name_ar": instance.get_full_name() or instance.username,
            },
        )


@receiver(post_save, sender=User)
def ensure_student_profile_on_role_change(sender, instance, **kwargs):
    """
    التأكد من وجود ملف طالب عند تغيير الدور إلى طالب
    Ensure profile exists when role changes to student
    """
    if instance.role == User.Role.STUDENT:
        StudentProfile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name_ar": instance.get_full_name() or instance.username,
            },
        )
