"""
Mixins مشتركة للصفحات المحمية
Shared mixins for protected pages
"""
from django.contrib import messages
from django.shortcuts import redirect


class StudentRequiredMixin:
    """Mixin للصفحات التي تتطلب تسجيل دخول طالب أو مسؤول"""

    login_url = "/login/"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "يجب تسجيل الدخول للوصول إلى هذه الصفحة.")
            return redirect(f"{self.login_url}?next={request.path}")

        if not request.user.is_active:
            messages.error(request, "حسابك معطّل. تواصل مع المسؤول.")
            return redirect("/login/")

        if not (request.user.is_student or request.user.is_platform_admin or request.user.is_staff):
            messages.error(request, "ليس لديك صلاحية للوصول إلى المنصة.")
            return redirect("/login/")

        return super().dispatch(request, *args, **kwargs)
