from django.apps import AppConfig


class GuestConfig(AppConfig):
    """تطبيق وضع الزائر"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.guest"
    verbose_name = "وضع الزائر"
