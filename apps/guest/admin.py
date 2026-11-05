from django.contrib import admin

from .models import GuestAIResult, GuestUpload


class GuestAIResultInline(admin.TabularInline):
    model = GuestAIResult
    extra = 0
    readonly_fields = ("result_type", "created_at")


@admin.register(GuestUpload)
class GuestUploadAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "session_key",
        "processing_status",
        "expires_at",
        "created_at",
    )
    list_filter = ("processing_status",)
    search_fields = ("original_filename", "session_key")
    readonly_fields = ("created_at",)
    inlines = [GuestAIResultInline]


@admin.register(GuestAIResult)
class GuestAIResultAdmin(admin.ModelAdmin):
    list_display = ("upload", "result_type", "created_at")
    list_filter = ("result_type",)
