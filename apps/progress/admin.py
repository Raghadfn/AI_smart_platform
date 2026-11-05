from django.contrib import admin

from .models import LectureProgress


@admin.register(LectureProgress)
class LectureProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lecture", "status", "progress_percent", "last_accessed_at")
    list_filter = ("status", "lecture__subject")
    search_fields = ("user__username", "lecture__title_ar")
