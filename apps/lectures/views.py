"""
واجهات API للمحاضرات
Lecture API views
"""
from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudentOrAdmin

from .models import Lecture
from .serializers import LectureDetailSerializer, LectureListSerializer


class SubjectLecturesAPIView(generics.ListAPIView):
    """GET /api/v1/years/<year_slug>/subjects/<subject_slug>/lectures/"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = LectureListSerializer

    def get_queryset(self):
        return Lecture.objects.filter(
            subject__semester__year__slug=self.kwargs["year_slug"],
            subject__slug=self.kwargs["subject_slug"],
            is_published=True,
        ).select_related("subject", "subject__semester", "subject__semester__year").order_by("order")


class LectureDetailAPIView(generics.RetrieveAPIView):
    """GET /api/v1/years/<year_slug>/subjects/<subject_slug>/lectures/<lecture_slug>/"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = LectureDetailSerializer

    def get_object(self):
        return Lecture.objects.select_related("subject", "subject__semester", "subject__semester__year").get(
            subject__semester__year__slug=self.kwargs["year_slug"],
            subject__slug=self.kwargs["subject_slug"],
            slug=self.kwargs["lecture_slug"],
            is_published=True,
        )


class LectureSearchAPIView(APIView):
    """GET /api/v1/lectures/search/?q=كلمة"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"success": True, "results": [], "count": 0})

        lectures = (
            Lecture.objects.filter(is_published=True)
            .filter(
                Q(title_ar__icontains=query)
                | Q(title_en__icontains=query)
                | Q(content_text__icontains=query)
                | Q(subject__name_ar__icontains=query)
            )
            .select_related("subject", "subject__semester", "subject__semester__year")
            .order_by("subject__semester__year__order", "subject__order", "order")[:20]
        )

        serializer = LectureListSerializer(lectures, many=True)
        return Response({
            "success": True,
            "query": query,
            "count": len(serializer.data),
            "results": serializer.data,
        })
