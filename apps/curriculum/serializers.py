"""
مسلسلات API للمنهج الدراسي
Curriculum API serializers
"""
from rest_framework import serializers

from .models import AcademicYear, Semester, Specialization, Subject


class SpecializationSerializer(serializers.ModelSerializer):
    """مسلسل الاختصاص"""

    subject_count = serializers.SerializerMethodField()

    class Meta:
        model = Specialization
        fields = (
            "id", "name_ar", "name_en", "slug", "description_ar", "order", "subject_count",
        )

    def get_subject_count(self, obj):
        return obj.subjects.filter(is_active=True).count()


class SubjectListSerializer(serializers.ModelSerializer):
    """مسلسل قائمة المواد"""

    lecture_count = serializers.SerializerMethodField()
    semester_name = serializers.CharField(source="semester.name_ar", read_only=True)
    year_name = serializers.CharField(source="semester.year.name_ar", read_only=True)
    specialization_name = serializers.CharField(source="specialization.name_ar", read_only=True, allow_null=True)

    class Meta:
        model = Subject
        fields = (
            "id", "name_ar", "name_en", "slug", "description_ar", "icon", "order",
            "semester_name", "year_name", "specialization_name", "lecture_count",
        )

    def get_lecture_count(self, obj):
        return obj.lectures.filter(is_published=True).count()


class SemesterSerializer(serializers.ModelSerializer):
    """مسلسل الفصل الدراسي مع المواد"""

    subjects = SubjectListSerializer(many=True, read_only=True)
    subject_count = serializers.SerializerMethodField()

    class Meta:
        model = Semester
        fields = (
            "id",
            "number",
            "name_ar",
            "name_en",
            "slug",
            "order",
            "subject_count",
            "subjects",
        )

    def get_subject_count(self, obj):
        return obj.subjects.filter(is_active=True).count()


class AcademicYearSerializer(serializers.ModelSerializer):
    """مسلسل السنة الأكاديمية"""

    subject_count = serializers.SerializerMethodField()
    semester_count = serializers.SerializerMethodField()

    class Meta:
        model = AcademicYear
        fields = (
            "id",
            "name_ar",
            "name_en",
            "slug",
            "order",
            "subject_count",
            "semester_count",
        )

    def get_subject_count(self, obj):
        return Subject.objects.filter(semester__year=obj, is_active=True).count()

    def get_semester_count(self, obj):
        return obj.semesters.filter(is_active=True).count()


class AcademicYearDetailSerializer(AcademicYearSerializer):
    """مسلسل تفاصيل السنة مع الفصول والاختصاصات"""

    semesters = SemesterSerializer(many=True, read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)

    class Meta(AcademicYearSerializer.Meta):
        fields = AcademicYearSerializer.Meta.fields + ("semesters", "specializations")


class SubjectDetailSerializer(serializers.ModelSerializer):
    """مسلسل تفاصيل المادة"""

    year = AcademicYearSerializer(source="semester.year", read_only=True)
    semester = SemesterSerializer(read_only=True)
    specialization = SpecializationSerializer(read_only=True)
    lecture_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = (
            "id",
            "name_ar",
            "name_en",
            "slug",
            "description_ar",
            "icon",
            "order",
            "year",
            "semester",
            "specialization",
            "lecture_count",
        )

    def get_lecture_count(self, obj):
        return obj.lectures.filter(is_published=True).count()
