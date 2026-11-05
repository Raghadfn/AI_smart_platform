"""
واجهات صفحات الويب للمصادقة
Web template views for authentication
"""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.mixins import StudentRequiredMixin
from apps.curriculum.models import AcademicYear, Subject

from .forms import LoginForm
from .utils import clear_jwt_cookies, get_tokens_for_user, set_jwt_cookies


class LoginView(View):
    """
    صفحة تسجيل الدخول
    GET/POST /login/
    """

    template_name = "auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts_web:dashboard")

        form = LoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts_web:dashboard")

        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        username = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]
        remember_me = form.cleaned_data.get("remember_me", False)

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
            return render(request, self.template_name, {"form": form})

        if not user.is_active:
            messages.error(request, "هذا الحساب معطّل. تواصل مع المسؤول.")
            return render(request, self.template_name, {"form": form})

        if not (user.is_student or user.is_platform_admin or user.is_staff):
            messages.error(request, "ليس لديك صلاحية للوصول إلى المنصة.")
            return render(request, self.template_name, {"form": form})

        login(request, user)

        # ضبط مدة الجلسة
        if not remember_me:
            request.session.set_expiry(0)  # تنتهي عند إغلاق المتصفح
        else:
            request.session.set_expiry(60 * 60 * 24 * 7)  # أسبوع

        messages.success(request, f"مرحباً، {user.profile.full_name_ar if hasattr(user, 'profile') else user.username}!")

        # إعداد JWT في ملفات تعريف الارتباط للطلبات API
        tokens = get_tokens_for_user(user)
        next_url = request.GET.get("next") or reverse("accounts_web:dashboard")
        response = redirect(next_url)
        set_jwt_cookies(response, tokens)
        return response


class LogoutView(View):
    """
    تسجيل الخروج
    GET/POST /logout/
    """

    def get(self, request):
        return self._logout(request)

    def post(self, request):
        return self._logout(request)

    def _logout(self, request):
        # إبطال JWT إن وُجد
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        logout(request)
        messages.success(request, "تم تسجيل الخروج بنجاح.")
        response = redirect("accounts_web:landing")
        return clear_jwt_cookies(response)


class DashboardView(StudentRequiredMixin, TemplateView):
    """
    لوحة التحكم الرئيسية - عرض السنوات الأكademية
    GET /dashboard/
    """

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        years = list(
            AcademicYear.objects.filter(is_active=True).prefetch_related(
                "semesters__subjects", "specializations"
            )
        )
        for year in years:
            if year.order >= 4:
                year.subject_total = Subject.objects.filter(
                    semester__year=year, is_active=True
                ).count()
            else:
                year.subject_total = sum(
                    len([s for s in sem.subjects.all() if s.is_active and not s.specialization_id])
                    for sem in year.semesters.all()
                )
        context["years"] = years
        context["user_display_name"] = (
            self.request.user.profile.full_name_ar
            if hasattr(self.request.user, "profile")
            else self.request.user.username
        )
        return context


class ProfileView(StudentRequiredMixin, TemplateView):
    """صفحة الملف الشخصي - GET /profile/"""

    template_name = "dashboard/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = getattr(self.request.user, "profile", None)
        return context
