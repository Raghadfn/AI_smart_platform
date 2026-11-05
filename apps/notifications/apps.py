from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """تطبيق الإشعارات"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "الإشعارات"
