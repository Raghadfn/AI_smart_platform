"""
أمر تقسيم المحاضرات وإنشاء التضمينات
Management command: chunk_lectures
"""
from django.core.management.base import BaseCommand

from apps.ai_services.services.embedder import ensure_lecture_chunks
from apps.lectures.models import Lecture


class Command(BaseCommand):
    help = "تقسيم المحاضرات إلى أجزاء وإنشاء تضمينات للبحث الدلالي (RAG)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lecture",
            type=str,
            help="معرّف slug للمحاضرة (اختياري، يعالج الكل إن لم يُحدد)",
        )
        parser.add_argument(
            "--no-embeddings",
            action="store_true",
            help="تقسيم فقط بدون إنشاء تضمينات",
        )

    def handle(self, *args, **options):
        qs = Lecture.objects.filter(is_published=True).exclude(content_text="")
        if options["lecture"]:
            qs = qs.filter(slug=options["lecture"])

        if not qs.exists():
            self.stdout.write(self.style.WARNING("لا توجد محاضرات للمعالجة."))
            return

        total_chunks = 0
        for lecture in qs:
            count = ensure_lecture_chunks(
                lecture,
                generate_embeddings=not options["no_embeddings"],
            )
            total_chunks += count
            self.stdout.write(
                self.style.SUCCESS(f"  {lecture.title_ar}: {count} جزء")
            )

        self.stdout.write(self.style.SUCCESS(f"\nاكتمل: {total_chunks} جزء إجمالاً"))
