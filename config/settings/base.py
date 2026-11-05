"""
إعدادات Django المشتركة بين بيئات التطوير والإنتاج
Shared Django settings for development and production
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# المسار الجذري للمشروع
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================
# الأمان - Security
# ============================================
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-in-production-immediately",
)

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# ============================================
# التطبيقات المثبتة - Installed Apps
# ============================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.curriculum",
    "apps.lectures",
    "apps.ai_services",
    "apps.guest",
    "apps.progress",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================
# الوسطاء - Middleware
# ============================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ============================================
# القوالب - Templates
# ============================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ============================================
# قاعدة البيانات PostgreSQL
# ============================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "informatics_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
            "options": "-c search_path=public",
        },
        "ATOMIC_REQUESTS": True,
    }
}

# ============================================
# نموذج المستخدم المخصص
# ============================================
AUTH_USER_MODEL = "accounts.User"

# ============================================
# التحقق من كلمات المرور
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================
# التدويل واللغة العربية - i18n
# ============================================
LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Baghdad"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
    ("ku", "کوردی"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# ============================================
# التخزين المؤقت - Cache (لتحديد معدل AI)
# ============================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "informatics-cache",
    }
}

# ============================================
# الملفات الثابتة والوسائط
# ============================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================
# المفتاح الافتراضي للنماذج
# ============================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================
# Django REST Framework
# ============================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DATE_FORMAT": "%Y-%m-%d",
}

# ============================================
# JWT - رموز المصادقة
# ============================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "60"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ============================================
# CORS - السماح بالطلبات من نفس المصدر
# ============================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True

# ============================================
# Celery - المهام الخلفية
# ============================================
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 دقيقة كحد أقصى للمهمة

# ============================================
# Hugging Face - إعدادات الذكاء الاصطناعي
# ============================================
def _load_hf_tokens_from_env() -> list[str]:
    """Up to 4 HF API keys: HF_TOKENS csv, or HF_TOKEN / HF_TOKEN_1..4."""
    tokens: list[str] = []
    csv = os.getenv("HF_TOKENS", "").strip()
    if csv:
        tokens.extend(part.strip() for part in csv.split(",") if part.strip())
    else:
        for key in (
            "HF_TOKEN",
            "HF_TOKEN_1",
            "HF_TOKEN_2",
            "HF_TOKEN_3",
            "HF_TOKEN_4",
            "HUGGINGFACEHUB_API_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
        ):
            value = os.getenv(key, "").strip()
            if value and value not in tokens:
                tokens.append(value)
    # Preserve order, drop empties, cap at 4
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            unique.append(token)
    return unique[:4]


HF_TOKENS = _load_hf_tokens_from_env()
HF_TOKEN = HF_TOKENS[0] if HF_TOKENS else ""
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
# "auto" يختار أفضل مزوّد متاح (hf-inference لم يعد يخدم نماذج المحادثة هذه)
HF_PROVIDER = os.getenv("HF_PROVIDER", "auto").strip() or "auto"
HF_TIMEOUT = float(os.getenv("HF_TIMEOUT", "120"))
# نماذج احتياطية سريعة عند انشغال النموذج الأساسي (Llama-3.2-3B الأكثر توفراً)
_fallback_raw = os.getenv(
    "HF_FALLBACK_MODELS",
    "meta-llama/Llama-3.2-3B-Instruct,mistralai/Mistral-7B-Instruct-v0.3",
)
HF_FALLBACK_MODELS = [
    m.strip() for m in _fallback_raw.split(",") if m.strip() and m.strip() != HF_MODEL
]

# أسماء قديمة للتوافق مع الوحدات التي لم تُحدَّث بعد
GROQ_API_KEYS = list(HF_TOKENS)
GROQ_API_KEY = HF_TOKEN
GROQ_MODEL = HF_MODEL
OPENAI_API_KEYS = list(HF_TOKENS)
OPENAI_API_KEY = HF_TOKEN
OPENAI_MODEL = HF_MODEL

# توليد الرسوم التوضيحية التعليمية (Pollinations — بدون مفتاح)
AI_IMAGE_PROVIDER = os.getenv("AI_IMAGE_PROVIDER", "pollinations")
AI_IMAGE_BASE_URL = os.getenv(
    "AI_IMAGE_BASE_URL",
    "https://image.pollinations.ai/prompt",
)
AI_IMAGE_WIDTH = int(os.getenv("AI_IMAGE_WIDTH", "1024"))
AI_IMAGE_HEIGHT = int(os.getenv("AI_IMAGE_HEIGHT", "768"))

# ============================================
# رفع الملفات ووضع الزائر
# ============================================
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
GUEST_FILE_EXPIRY_HOURS = int(os.getenv("GUEST_FILE_EXPIRY_HOURS", "24"))

# أنواع الملفات المسموحة
ALLOWED_UPLOAD_EXTENSIONS = [".pdf"]
ALLOWED_UPLOAD_MIME_TYPES = ["application/pdf"]

# ============================================
# تحديد معدل طلبات الذكاء الاصطناعي
# ============================================
AI_RATE_LIMIT_STUDENT = int(os.getenv("AI_RATE_LIMIT_STUDENT", "20"))
AI_RATE_LIMIT_GUEST = int(os.getenv("AI_RATE_LIMIT_GUEST", "5"))

# ============================================
# تسجيل الدخول والخروج
# ============================================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ============================================
# إعدادات الجلسة
# ============================================
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # أسبوع واحد
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# ============================================
# تسجيل الأحداث - Logging
# ============================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# ============================================
# إعدادات معالجة النصوص للذكاء الاصطناعي
# ============================================
AI_CHUNK_SIZE = 800       # عدد الأحرف لكل جزء نصي
AI_CHUNK_OVERLAP = 100    # التداخل بين الأجزاء
AI_TOP_K_CHUNKS = 3       # أجزاء RAG الأكثر صلة (خفض TPM)
AI_RAG_MAX_CHARS = 3500   # حد سياق الأسئلة/الرسوم التوضيحية
AI_TASK_MAX_CHARS = 4500  # حد سياق التلخيص/الترجمة/الامتحان
