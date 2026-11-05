"""
إعدادات Celery للمهام الخلفية
Celery configuration for background tasks
"""
import os

from celery import Celery

# تعيين إعدادات Django الافتراضية
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# إنشاء تطبيق Celery
app = Celery("informatics_platform")

# تحميل الإعدادات من Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# اكتشاف المهام تلقائياً من جميع التطبيقات المسجّلة
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """مهمة اختبارية للتحقق من عمل Celery"""
    print(f"Request: {self.request!r}")
