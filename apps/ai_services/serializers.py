"""
مسلسلات API للذكاء الاصطناعي
AI API serializers
"""
from rest_framework import serializers

from apps.ai_services.models import ExamAttempt, SavedAIResult


class TranslateSerializer(serializers.Serializer):
    """مسلسل طلب الترجمة"""

    target_lang = serializers.ChoiceField(
        choices=[("ar", "العربية"), ("en", "English")],
        default="en",
    )
    save = serializers.BooleanField(default=True)


class SummarizeSerializer(serializers.Serializer):
    """مسلسل طلب التلخيص"""

    length = serializers.ChoiceField(
        choices=[("short", "قصير"), ("medium", "متوسط"), ("detailed", "مفصل")],
        default="medium",
    )
    save = serializers.BooleanField(default=True)


class AskSerializer(serializers.Serializer):
    """مسلسل طلب سؤال وجواب"""

    question = serializers.CharField(min_length=3, max_length=1000)
    save = serializers.BooleanField(default=True)
    force_visual = serializers.BooleanField(default=False)


class IllustrateSerializer(serializers.Serializer):
    """مسلسل طلب رسم توضيحي تعليمي"""

    concept = serializers.CharField(min_length=3, max_length=500)
    save = serializers.BooleanField(default=True)


class ExamSerializer(serializers.Serializer):
    """مسلسل طلب إنشاء أسئلة امتحان"""

    types = serializers.ListField(
        child=serializers.ChoiceField(choices=["mcq", "true_false", "essay"]),
        default=["mcq"],
    )
    count = serializers.IntegerField(min_value=1, max_value=20, default=5)
    save = serializers.BooleanField(default=True)


class SubmitExamSerializer(serializers.Serializer):
    """مسلسل تسليم إجابات الامتحان"""

    answers = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        help_text="خريطة {question_id: answer}",
    )


class ExamAttemptSerializer(serializers.ModelSerializer):
    """مسلسل محاولة امتحان"""

    exam_title = serializers.CharField(source="saved_result.title", read_only=True)

    class Meta:
        model = ExamAttempt
        fields = (
            "id",
            "saved_result",
            "exam_title",
            "answers",
            "score_percent",
            "correct_count",
            "total_gradable",
            "grading_details",
            "submitted_at",
        )
        read_only_fields = fields


class SavedAIResultSerializer(serializers.ModelSerializer):
    """مسلسل النتائج المحفوظة"""

    result_type_display = serializers.CharField(source="get_result_type_display", read_only=True)
    lecture_title = serializers.CharField(source="lecture.title_ar", read_only=True, allow_null=True)

    class Meta:
        model = SavedAIResult
        fields = (
            "id",
            "result_type",
            "result_type_display",
            "title",
            "lecture",
            "lecture_title",
            "input_params",
            "result_data",
            "created_at",
        )
        read_only_fields = fields
