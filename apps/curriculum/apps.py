from django.apps import AppConfig


class CurriculumConfig(AppConfig):
    """تطبيق المنهج الدراسي - السنوات والمواد"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.curriculum"
    verbose_name = "المنهج الدراسي"
