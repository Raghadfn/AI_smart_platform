from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """تطبيق إدارة الحسابات والمصادقة"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "الحسابات"

    def ready(self):
        # تحميل الإشارات عند بدء التطبيق
        import apps.accounts.signals  # noqa: F401
