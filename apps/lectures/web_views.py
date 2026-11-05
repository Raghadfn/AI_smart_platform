"""
واجهات صفحات المحاضرات
Lecture web template views
"""
from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import DetailView

from apps.accounts.mixins import StudentRequiredMixin
from apps.progress.models import LectureProgress

from .models import Lecture
from .services.text_extractor import ensure_lecture_text


class LectureDetailView(StudentRequiredMixin, DetailView):
    """
    عرض تفاصيل المحاضرة مع المحتوى
    GET /lecture/<lecture_id>/
    GET /year/<year_slug>/subject/<subject_slug>/lecture/<lecture_slug>/
    """

    model = Lecture
    context_object_name = "lecture"
    template_name = "academic/lecture_detail.html"

    def get_object(self, queryset=None):
        lecture_id = self.kwargs.get("lecture_id")
        if lecture_id:
            try:
                lecture = (
                    Lecture.objects.select_related(
                        "subject",
                        "subject__semester",
                        "subject__semester__year",
                        "subject__specialization",
                    ).get(pk=lecture_id, is_published=True)
                )
            except Lecture.DoesNotExist as exc:
                raise Http404("المحاضرة غير موجودة أو غير منشورة.") from exc
        else:
            year_slug = self.kwargs.get("year_slug")
            subject_slug = self.kwargs.get("subject_slug")
            lecture_slug = self.kwargs.get("lecture_slug")

            try:
                lecture = (
                    Lecture.objects.select_related(
                        "subject",
                        "subject__semester",
                        "subject__semester__year",
                        "subject__specialization",
                    ).get(
                        subject__semester__year__slug=year_slug,
                        subject__slug=subject_slug,
                        slug=lecture_slug,
                        is_published=True,
                    )
                )
            except Lecture.DoesNotExist as exc:
                raise Http404("المحاضرة غير موجودة أو غير منشورة.") from exc

        # استخراج / إعادة استخراج النص من PDF بمحرك العربية الجديد
        if lecture.pdf_file:
            ensure_lecture_text(lecture)
            lecture.refresh_from_db(
                fields=["content_text", "processing_status", "processing_error"]
            )

        return lecture

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lecture = self.object
        user = self.request.user

        progress, _ = LectureProgress.objects.get_or_create(
            user=user,
            lecture=lecture,
            defaults={
                "status": LectureProgress.Status.IN_PROGRESS,
                "progress_percent": 0,
            },
        )
        if progress.status == LectureProgress.Status.NOT_STARTED:
            progress.status = LectureProgress.Status.IN_PROGRESS
            progress.save(update_fields=["status", "last_accessed_at"])

        has_pdf = bool(getattr(lecture.pdf_file, "name", None))
        extracted_text = (lecture.content_text or "").strip()
        has_content = bool(extracted_text)

        context["progress"] = progress
        context["has_pdf"] = has_pdf
        context["has_content"] = has_content
        # Keep full extracted text in context for AI panel / tools; UI must not render it as primary content.
        context["extracted_text"] = extracted_text
        context["show_raw_extracted_text"] = False
        context["lecture_id"] = str(lecture.id)
        context["pdf_embed_url"] = (
            reverse("lectures_web:pdf_embed", kwargs={"lecture_id": lecture.id})
            if has_pdf
            else ""
        )
        context["extraction_failed"] = (
            lecture.processing_status == Lecture.ProcessingStatus.FAILED
        )
        context["breadcrumb"] = [
            {"label": "لوحة التحكم", "url": "/dashboard/"},
            {
                "label": lecture.subject.year.name_ar,
                "url": f"/year/{lecture.subject.year.slug}/",
            },
            {
                "label": lecture.subject.name_ar,
                "url": f"/year/{lecture.subject.year.slug}/subject/{lecture.subject.slug}/",
            },
            {"label": lecture.title_ar, "url": None},
        ]
        return context


@method_decorator(xframe_options_sameorigin, name="dispatch")
class LecturePDFEmbedView(StudentRequiredMixin, View):
    """
    تقديم ملف PDF للعرض داخل الصفحة (inline) بدل التنزيل المباشر
    GET /lecture/<lecture_id>/pdf/
    """

    def get(self, request, lecture_id):
        try:
            lecture = Lecture.objects.get(pk=lecture_id, is_published=True)
        except Lecture.DoesNotExist as exc:
            raise Http404("المحاضرة غير موجودة أو غير منشورة.") from exc

        if not lecture.pdf_file:
            raise Http404("لا يوجد ملف PDF لهذه المحاضرة.")

        try:
            pdf_file = lecture.pdf_file.open("rb")
        except FileNotFoundError as exc:
            raise Http404("ملف PDF غير موجود على الخادم.") from exc

        response = FileResponse(
            pdf_file,
            content_type="application/pdf",
            as_attachment=False,
            filename=lecture.pdf_file.name.split("/")[-1],
        )
        response["Content-Disposition"] = (
            f'inline; filename="{lecture.pdf_file.name.split("/")[-1]}"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
