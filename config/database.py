"""
أدوات إعداد وصحة قاعدة البيانات
Database configuration utilities and health checks
"""
import os
from typing import Any

from django.conf import settings
from django.db import connection


def get_database_config() -> dict[str, Any]:
    """إرجاع إعدادات قاعدة البيانات الحالية"""
    return settings.DATABASES["default"]


def is_postgresql() -> bool:
    """هل قاعدة البيانات PostgreSQL؟"""
    engine = get_database_config().get("ENGINE", "")
    return "postgresql" in engine


def is_sqlite() -> bool:
    """هل قاعدة البيانات SQLite؟"""
    engine = get_database_config().get("ENGINE", "")
    return "sqlite" in engine


def get_database_url() -> str:
    """بناء رابط الاتصال بقاعدة البيانات"""
    db = get_database_config()
    if is_sqlite():
        return f"sqlite:///{db['NAME']}"
    return (
        f"postgresql://{db['USER']}:{db['PASSWORD']}"
        f"@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    )


def check_connection() -> dict[str, Any]:
    """
    فحص الاتصال بقاعدة البيانات
    Returns dict with status, engine, and optional error
    """
    result: dict[str, Any] = {
        "connected": False,
        "engine": get_database_config().get("ENGINE", "unknown"),
        "database": str(get_database_config().get("NAME", "")),
        "error": None,
    }
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        result["connected"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def get_installed_extensions() -> list[dict[str, str]]:
    """جلب قائمة الامتدادات المثبتة (PostgreSQL فقط)"""
    if not is_postgresql():
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT extname, extversion FROM pg_extension ORDER BY extname"
        )
        return [{"name": row[0], "version": row[1]} for row in cursor.fetchall()]


def extension_exists(extension_name: str) -> bool:
    """التحقق من وجود امتداد معين"""
    if not is_postgresql():
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_extension WHERE extname = %s",
            [extension_name],
        )
        return cursor.fetchone() is not None


# الامتدادات المطلوبة للمنصة
REQUIRED_EXTENSIONS = {
    "vector": "pgvector - البحث الدلالي للذكاء الاصطناعي",
    "pg_trgm": "البحث النصي الضبابي للعربية",
    "unaccent": "إزالة التشكيل للبحث النصي",
}


def check_required_extensions() -> dict[str, dict[str, Any]]:
    """فحص حالة الامتدادات المطلوبة"""
    status: dict[str, dict[str, Any]] = {}
    for ext_name, description in REQUIRED_EXTENSIONS.items():
        if not is_postgresql():
            status[ext_name] = {
                "installed": False,
                "description": description,
                "skipped": True,
                "reason": "يتطلب PostgreSQL",
            }
        else:
            status[ext_name] = {
                "installed": extension_exists(ext_name),
                "description": description,
                "skipped": False,
            }
    return status


def enable_extension(extension_name: str) -> bool:
    """
    تفعيل امتداد PostgreSQL
    Returns True if successful
    """
    if not is_postgresql():
        return False
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension_name}"')
    return extension_exists(extension_name)


def enable_all_extensions() -> dict[str, bool]:
    """تفعيل جميع الامتدادات المطلوبة"""
    results: dict[str, bool] = {}
    for ext_name in REQUIRED_EXTENSIONS:
        if is_postgresql():
            results[ext_name] = enable_extension(ext_name)
        else:
            results[ext_name] = False
    return results
