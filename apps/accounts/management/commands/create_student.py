"""
أمر إنشاء حساب طالب - للمسؤول/المبرمج فقط
Management command: create_student
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import StudentProfile, User


class Command(BaseCommand):
    help = "إنشاء حساب طالب جديد (لا يوجد تسجيل ذاتي - يُنشأ من المبرمج فقط)"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="اسم المستخدم")
        parser.add_argument("password", type=str, help="كلمة المرور")
        parser.add_argument("--full-name-ar", type=str, default="", help="الاسم الكامل بالعربية")
        parser.add_argument("--student-id", type=str, default="", help="الرقم الجامعي")
        parser.add_argument("--email", type=str, default="", help="البريد الإلكتروني")

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        full_name_ar = options["full_name_ar"].strip() or username
        student_id = options["student_id"].strip()
        email = options["email"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f"اسم المستخدم '{username}' موجود مسبقاً.")

        if len(password) < 8:
            raise CommandError("كلمة المرور يجب أن تكون 8 أحرف على الأقل.")

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role=User.Role.STUDENT,
        )

        profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                "full_name_ar": full_name_ar,
                "student_id": student_id,
            },
        )

        if not created:
            profile.full_name_ar = full_name_ar
            if student_id:
                profile.student_id = student_id
            profile.save(update_fields=["full_name_ar", "student_id"])

        self.stdout.write(self.style.SUCCESS(f"تم إنشاء حساب الطالب: {username}"))
        self.stdout.write(f"  الاسم: {profile.full_name_ar}")
        if student_id:
            self.stdout.write(f"  الرقم الجامعي: {student_id}")
