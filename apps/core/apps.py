from django.apps import AppConfig


class CoreConfig(AppConfig):
    """تطبيق الأساسيات - إعداد قاعدة البيانات والأدوات المشتركة"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "الأساسيات"
