"""
واجهات API للمنهج الدراسي
Curriculum API views
"""
from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudentOrAdmin

from .models import AcademicYear, Subject
from .serializers import (
    AcademicYearDetailSerializer,
    AcademicYearSerializer,
    SubjectDetailSerializer,
    SubjectListSerializer,
)


class YearListAPIView(generics.ListAPIView):
    """GET /api/v1/years/ - قائمة السنوات الأكademية"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = AcademicYearSerializer
    queryset = AcademicYear.objects.filter(is_active=True)


class YearDetailAPIView(generics.RetrieveAPIView):
    """GET /api/v1/years/<slug>/ - تفاصيل سنة مع المواد"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = AcademicYearDetailSerializer
    lookup_field = "slug"
    queryset = AcademicYear.objects.filter(is_active=True).prefetch_related(
        "semesters__subjects", "specializations"
    )


class YearSubjectsAPIView(generics.ListAPIView):
    """GET /api/v1/years/<slug>/subjects/ - مواد سنة معينة"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = SubjectListSerializer

    def get_queryset(self):
        return Subject.objects.filter(
            semester__year__slug=self.kwargs["slug"],
            semester__year__is_active=True,
            is_active=True,
        ).select_related("semester", "semester__year").order_by(
            "semester__number", "order"
        )


class SubjectDetailAPIView(generics.RetrieveAPIView):
    """GET /api/v1/subjects/<year_slug>/<subject_slug>/ - تفاصيل مادة"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = SubjectDetailSerializer

    def get_object(self):
        return Subject.objects.select_related("semester", "semester__year").get(
            semester__year__slug=self.kwargs["year_slug"],
            slug=self.kwargs["subject_slug"],
            is_active=True,
        )
