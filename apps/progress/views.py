"""
واجهات API لتتبع التقدم
Progress API views
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudentOrAdmin
from apps.lectures.models import Lecture

from .models import LectureProgress


class SaveProgressAPIView(APIView):
    """
    حفظ تقدم قراءة المحاضرة
    POST /api/v1/progress/save/
    """

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]

    def post(self, request):
        year_slug = request.data.get("year_slug")
        subject_slug = request.data.get("subject_slug")
        lecture_slug = request.data.get("lecture_slug")
        progress_percent = request.data.get("progress_percent", 0)
        progress_status = request.data.get("status", "in_progress")

        if not all([year_slug, subject_slug, lecture_slug]):
            return Response(
                {"success": False, "detail": "معاملات المحاضرة مطلوبة."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lecture = Lecture.objects.get(
                subject__semester__year__slug=year_slug,
                subject__slug=subject_slug,
                slug=lecture_slug,
                is_published=True,
            )
        except Lecture.DoesNotExist:
            return Response(
                {"success": False, "detail": "المحاضرة غير موجودة."},
                status=status.HTTP_404_NOT_FOUND,
            )

        progress_percent = max(0, min(100, int(progress_percent)))

        if progress_status not in dict(LectureProgress.Status.choices):
            progress_status = LectureProgress.Status.IN_PROGRESS

        progress, _ = LectureProgress.objects.get_or_create(
            user=request.user,
            lecture=lecture,
            defaults={"progress_percent": progress_percent, "status": progress_status},
        )

        if progress_percent > progress.progress_percent:
            progress.progress_percent = progress_percent

        progress.status = progress_status
        if progress_status == LectureProgress.Status.COMPLETED and not progress.completed_at:
            progress.completed_at = timezone.now()
            progress.progress_percent = 100

        progress.save()

        return Response({
            "success": True,
            "progress_percent": progress.progress_percent,
            "status": progress.status,
        })
