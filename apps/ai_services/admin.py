from django.contrib import admin

from .models import ExamAttempt, SavedAIResult


@admin.register(SavedAIResult)
class SavedAIResultAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "lecture", "result_type", "created_at")
    list_filter = ("result_type",)
    search_fields = ("title", "user__username")


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "saved_result", "score_percent", "correct_count", "total_gradable", "submitted_at")
    list_filter = ("submitted_at",)
    search_fields = ("user__username", "saved_result__title")
