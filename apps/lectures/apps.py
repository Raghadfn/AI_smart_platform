from django.apps import AppConfig


class LecturesConfig(AppConfig):
    """تطبيق المحاضرات"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lectures"
    verbose_name = "المحاضرات"
