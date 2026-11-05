"""
أمر فحص صحة قاعدة البيانات
Management command: check_database
"""
from django.core.management.base import BaseCommand
from django.db import connection

from config.database import (
    check_connection,
    check_required_extensions,
    get_database_url,
    is_postgresql,
    is_sqlite,
)


class Command(BaseCommand):
    help = "فحص صحة الاتصال بقاعدة البيانات والامتدادات المطلوبة"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== فحص قاعدة البيانات ===\n"))

        all_ok = True

        # 1. نوع قاعدة البيانات
        if is_postgresql():
            db_type = "PostgreSQL"
            self.stdout.write(self.style.SUCCESS(f"نوع القاعدة: {db_type}"))
        elif is_sqlite():
            db_type = "SQLite (تطوير فقط)"
            self.stdout.write(self.style.WARNING(f"نوع القاعدة: {db_type}"))
        else:
            db_type = "غير معروف"
            self.stdout.write(self.style.ERROR(f"نوع القاعدة: {db_type}"))
            all_ok = False

        # 2. الاتصال
        conn = check_connection()
        if conn["connected"]:
            self.stdout.write(self.style.SUCCESS(f"الاتصال: ناجح"))
            self.stdout.write(f"  قاعدة البيانات: {conn['database']}")
        else:
            self.stdout.write(self.style.ERROR(f"الاتصال: فشل"))
            self.stdout.write(self.style.ERROR(f"  الخطأ: {conn['error']}"))
            all_ok = False
            self._print_summary(all_ok)
            return

        # 3. اختبار الكتابة والقراءة
        try:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TEMP TABLE _health_check (id INTEGER)")
                cursor.execute("INSERT INTO _health_check VALUES (1)")
                cursor.execute("SELECT id FROM _health_check")
                assert cursor.fetchone()[0] == 1
            self.stdout.write(self.style.SUCCESS("اختبار القراءة/الكتابة: ناجح"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"اختبار القراءة/الكتابة: فشل - {exc}"))
            all_ok = False

        # 4. الامتدادات (PostgreSQL فقط)
        if is_postgresql():
            self.stdout.write(self.style.MIGRATE_HEADING("\nالامتدادات المطلوبة:"))
            ext_status = check_required_extensions()
            for ext_name, info in ext_status.items():
                if info.get("skipped"):
                    self.stdout.write(self.style.WARNING(f"  {ext_name}: متخطى ({info['reason']})"))
                elif info["installed"]:
                    self.stdout.write(self.style.SUCCESS(f"  {ext_name}: مثبت - {info['description']}"))
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  {ext_name}: غير مثبت - {info['description']}")
                    )
                    self.stdout.write(
                        self.style.WARNING(f"    شغّل: python manage.py setup_database")
                    )
                    all_ok = False

            # 5. اختبار pgvector
            ext_status = check_required_extensions()
            if ext_status.get("vector", {}).get("installed"):
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT '[1,2,3]'::vector")
                        cursor.fetchone()
                    self.stdout.write(self.style.SUCCESS("\nاختبار pgvector: ناجح"))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"\nاختبار pgvector: فشل - {exc}"))
                    all_ok = False

        self._print_summary(all_ok)

    def _print_summary(self, all_ok: bool):
        self.stdout.write("")
        if all_ok:
            self.stdout.write(self.style.SUCCESS("=== جميع الفحوصات ناجحة ==="))
        else:
            self.stdout.write(self.style.ERROR("=== بعض الفحوصات فشلت ==="))
