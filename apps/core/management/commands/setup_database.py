"""
أمر إعداد قاعدة البيانات - تفعيل الامتدادات وبذر المنهج
Management command: setup_database
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from config.database import (
    REQUIRED_EXTENSIONS,
    check_connection,
    enable_all_extensions,
    get_installed_extensions,
    is_postgresql,
)


class Command(BaseCommand):
    help = "إعداد قاعدة البيانات: امتدادات PostgreSQL + بذر المنهج (5 سنوات + اختصاصات)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-extensions",
            action="store_true",
            help="تخطي تفعيل الامتدادات (فقط فحص الاتصال)",
        )
        parser.add_argument(
            "--seed-curriculum",
            action="store_true",
            help="بذر المنهج الدراسي (5 سنوات + 3 اختصاصات للسنة 4-5) بعد الإعداد",
        )
        parser.add_argument(
            "--clear-curriculum",
            action="store_true",
            help="حذف المنهج القديم قبل البذر (يُستخدم مع --seed-curriculum)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== إعداد قاعدة البيانات ===\n"))

        conn = check_connection()
        if not conn["connected"]:
            self.stdout.write(self.style.ERROR(f"فشل الاتصال: {conn['error']}"))
            self.stdout.write(
                self.style.WARNING(
                    "\nتأكد من:\n"
                    "  1. تشغيل PostgreSQL (docker compose up -d أو خدمة Windows)\n"
                    "  2. ضبط USE_SQLITE=false في ملف .env\n"
                    "  3. صحة بيانات DB_HOST, DB_PORT, DB_USER, DB_PASSWORD\n"
                )
            )
            return

        self.stdout.write(self.style.SUCCESS(f"الاتصال ناجح: {conn['database']}"))

        if is_postgresql():
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.stdout.write(f"الإصدار: {version[:80]}...")

            if not options["skip_extensions"]:
                self.stdout.write(self.style.MIGRATE_HEADING("\nتفعيل الامتدادات..."))
                results = enable_all_extensions()
                for ext_name, success in results.items():
                    desc = REQUIRED_EXTENSIONS[ext_name]
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"  [OK] {ext_name}: {desc}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  [FAIL] {ext_name}: {desc}"))
                self._show_extensions()
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nتستخدم SQLite حالياً. امتدادات pgvector تتطلب PostgreSQL.\n"
                    "عيّن USE_SQLITE=false في .env لاستخدام PostgreSQL."
                )
            )

        if options["seed_curriculum"] or options["clear_curriculum"]:
            self.stdout.write(self.style.MIGRATE_HEADING("\nبذر المنهج الدراسي (5 سنوات + اختصاصات)..."))
            seed_args = []
            if options["clear_curriculum"]:
                seed_args.append("--clear")
            call_command("seed_curriculum", *seed_args, stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS("\nاكتمل إعداد قاعدة البيانات."))

    def _show_extensions(self):
        extensions = get_installed_extensions()
        if extensions:
            self.stdout.write(self.style.MIGRATE_HEADING("\nالامتدادات المثبتة:"))
            for ext in extensions:
                self.stdout.write(f"  - {ext['name']} v{ext['version']}")
