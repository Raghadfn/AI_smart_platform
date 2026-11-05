"""
إعدادات بيئة الإنتاج
Production environment settings
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# ============================================
# إعدادات الأمان للإنتاج
# ============================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS - فعّل عند توفر شهادة SSL
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() in ("true", "1")  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ============================================
# CORS للإنتاج
# ============================================
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")  # noqa: F405
    if origin.strip()
]

# ============================================
# تسجيل الأحداث في الإنتاج
# ============================================
LOGGING["handlers"]["file"]["filename"] = "/var/log/informatics/django.log"  # noqa: F405
LOGGING["root"]["handlers"] = ["console", "file"]  # noqa: F405
