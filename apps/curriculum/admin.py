from django.contrib import admin

from .models import AcademicYear, Semester, Specialization, Subject


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 0
    fields = ("name_ar", "name_en", "slug", "specialization", "order", "is_active")


class SemesterInline(admin.TabularInline):
    model = Semester
    extra = 0
    fields = ("number", "name_ar", "name_en", "slug", "order", "is_active")
    show_change_link = True


class SpecializationInline(admin.TabularInline):
    model = Specialization
    extra = 0
    fields = ("name_ar", "name_en", "slug", "order", "is_active")
    show_change_link = True


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "name_en", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_ar", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [SemesterInline, SpecializationInline]


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "year", "number", "slug", "order", "is_active")
    list_filter = ("year", "is_active")
    search_fields = ("name_ar", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [SubjectInline]


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "year", "slug", "order", "is_active")
    list_filter = ("year", "is_active")
    search_fields = ("name_ar", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "semester", "specialization", "slug", "order", "is_active")
    list_filter = ("semester__year", "specialization", "is_active")
    search_fields = ("name_ar", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
