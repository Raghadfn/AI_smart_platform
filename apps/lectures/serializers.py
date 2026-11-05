"""
مسلسلات API للمحاضرات
Lecture API serializers
"""
from rest_framework import serializers

from .models import Lecture


class LectureListSerializer(serializers.ModelSerializer):
    """مسلسل قائمة المحاضرات"""

    subject_name = serializers.CharField(source="subject.name_ar", read_only=True)
    year_name = serializers.CharField(source="subject.year.name_ar", read_only=True)

    class Meta:
        model = Lecture
        fields = (
            "id",
            "title_ar",
            "title_en",
            "slug",
            "order",
            "duration_minutes",
            "is_published",
            "processing_status",
            "subject_name",
            "year_name",
        )


class LectureDetailSerializer(serializers.ModelSerializer):
    """مسلسل تفاصيل المحاضرة"""

    subject_slug = serializers.CharField(source="subject.slug", read_only=True)
    year_slug = serializers.CharField(source="subject.year.slug", read_only=True)
    subject_name = serializers.CharField(source="subject.name_ar", read_only=True)
    year_name = serializers.CharField(source="subject.year.name_ar", read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = (
            "id",
            "title_ar",
            "title_en",
            "slug",
            "content_text",
            "pdf_url",
            "order",
            "duration_minutes",
            "processing_status",
            "subject_slug",
            "year_slug",
            "subject_name",
            "year_name",
            "created_at",
            "updated_at",
        )

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None
