from django.apps import AppConfig


class ProgressConfig(AppConfig):
    """تطبيق تتبع تقدم الطلاب"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.progress"
    verbose_name = "تقدم الطلاب"
