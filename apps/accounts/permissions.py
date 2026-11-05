"""
صلاحيات الوصول للمنصة
Platform access permissions
"""
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """يسمح للطلاب فقط"""

    message = "هذه الصفحة متاحة للطلاب المسجلين فقط."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_student
        )


class IsPlatformAdmin(BasePermission):
    """يسمح لمسؤولي المنصة فقط"""

    message = "هذه الصفحة متاحة للمسؤولين فقط."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (request.user.is_platform_admin or request.user.is_staff)
        )


class IsStudentOrAdmin(BasePermission):
    """يسمح للطلاب أو مسؤولي المنصة"""

    message = "يجب تسجيل الدخول للوصول."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False
        return request.user.is_student or request.user.is_platform_admin or request.user.is_staff
