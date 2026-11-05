# Generated migration - enables PostgreSQL extensions
# هجرة تفعيل امتدادات PostgreSQL

from django.db import migrations


def enable_extensions(apps, schema_editor):
    """تفعيل الامتدادات المطلوبة (PostgreSQL فقط)"""
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def disable_extensions(apps, schema_editor):
    """إزالة الامتدادات (للتراجع - اختياري)"""
    if schema_editor.connection.vendor != "postgresql":
        return
    # لا نحذف الامتدادات عند التراجع لتجنب كسر جداول أخرى
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(enable_extensions, disable_extensions),
    ]
