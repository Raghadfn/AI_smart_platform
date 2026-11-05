from django.apps import AppConfig


class AiServicesConfig(AppConfig):
    """تطبيق خدمات الذكاء الاصطناعي"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_services"
    verbose_name = "خدمات الذكاء الاصطناعي"
