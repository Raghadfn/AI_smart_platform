from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import StudentProfile, User


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name = "ملف الطالب"
    verbose_name_plural = "ملف الطالب"
    fields = ("full_name_ar", "student_id", "preferred_language")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    إدارة المستخدمين - إنشاء الحسابات من المسؤول فقط
    Admin-only user management (no self-registration)
    """

    list_display = ("username", "email", "role", "is_active", "is_staff", "date_joined", "last_login")
    list_filter = ("role", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "profile__full_name_ar", "profile__student_id")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (_("Platform"), {"fields": ("role",)}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "is_active",
                ),
            },
        ),
    )

    inlines = [StudentProfileInline]

    def get_inlines(self, request, obj=None):
        """عرض ملف الطالب فقط للمستخدمين بدور طالب"""
        if obj and obj.role != User.Role.STUDENT:
            return []
        return [StudentProfileInline]

    def save_model(self, request, obj, form, change):
        """حفظ المستخدم مع ضبط الصلاحيات حسب الدور"""
        if not change and obj.role == User.Role.ADMIN:
            obj.is_staff = True
        super().save_model(request, obj, form, change)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name_ar", "user", "student_id", "preferred_language", "created_at")
    list_filter = ("preferred_language",)
    search_fields = ("full_name_ar", "student_id", "user__username")
    raw_id_fields = ("user",)
