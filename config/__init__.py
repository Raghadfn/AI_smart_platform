"""
تهيئة تطبيق Django - تحميل إعدادات Celery
Django app initialization - load Celery settings
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
