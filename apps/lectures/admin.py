import uuid

from django.contrib import admin
from django.utils.text import slugify

from .models import Lecture, LectureChunk


class LectureChunkInline(admin.TabularInline):
    model = LectureChunk
    extra = 0
    readonly_fields = ("chunk_index", "token_count", "created_at")
    fields = ("chunk_index", "chunk_text", "token_count")
    can_delete = False


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = (
        "title_ar",
        "subject",
        "order",
        "is_published",
        "has_pdf_file",
        "processing_status",
        "created_at",
    )
    list_filter = (
        "subject__semester__year",
        "subject__specialization",
        "subject",
        "is_published",
        "processing_status",
    )
    list_editable = ("is_published", "order")
    search_fields = ("title_ar", "title_en", "content_text", "slug")
    prepopulated_fields = {"slug": ("title_en",)}
    readonly_fields = ("processing_status", "processing_error", "created_at", "updated_at")
    autocomplete_fields = ("subject",)
    inlines = [LectureChunkInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "subject",
                    "title_ar",
                    "title_en",
                    "slug",
                    "order",
                    "duration_minutes",
                    "is_published",
                ),
                "description": (
                    "فعّل «منشور» حتى تظهر المحاضرة للطلاب في الواجهة. "
                    "ارفع ملف PDF و/أو الصق نص المحتوى."
                ),
            },
        ),
        ("المحتوى", {"fields": ("pdf_file", "content_text")}),
        (
            "المعالجة",
            {
                "classes": ("collapse",),
                "fields": ("processing_status", "processing_error", "created_at", "updated_at"),
            },
        ),
    )

    @admin.display(boolean=True, description="PDF")
    def has_pdf_file(self, obj):
        return bool(obj.pdf_file)

    def get_changeform_initial_data(self, request):
        return {"is_published": True}

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            base = slugify(obj.title_en) or slugify(obj.title_ar) or "lecture"
            obj.slug = f"{base}-{uuid.uuid4().hex[:8]}"
        super().save_model(request, obj, form, change)

        # استخراج النص من PDF بعد الحفظ إن لم يُدخل يدوياً
        if obj.pdf_file and not (obj.content_text or "").strip():
            from .services.text_extractor import ensure_lecture_text

            ensure_lecture_text(obj)


@admin.register(LectureChunk)
class LectureChunkAdmin(admin.ModelAdmin):
    list_display = ("lecture", "chunk_index", "token_count", "created_at")
    list_filter = ("lecture__subject",)
    search_fields = ("chunk_text", "lecture__title_ar")
    readonly_fields = ("created_at",)
