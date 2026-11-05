"""
إعدادات بيئة التطوير
Development environment settings
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# السماح بجميع المضيفين في التطوير
ALLOWED_HOSTS = ["*"]

# وسائط التطوير (PDF المحاضرات) — تأكيد صريح مع خدمة الملفات في urls.py
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

# قاعدة بيانات بديلة SQLite إذا لم يتوفر PostgreSQL
# يمكن التبديل عبر USE_SQLITE=true في .env
import os

if os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# إضافة أدوات التطوير
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# عرض الأخطاء بالتفصيل في التطوير
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# تعطيل ضغط الملفات الثابتة في التطوير
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# البريد الإلكتروني - طباعة في الطرفية
EMAIL_BACKEND = "django.contrib.mail.backends.console.EmailBackend"

# CORS - السماح بجميع المصادر في التطوير
CORS_ALLOW_ALL_ORIGINS = True
