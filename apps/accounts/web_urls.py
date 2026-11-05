"""
مسارات صفحات الويب للمصادقة
Web page routes for authentication
"""
from django.urls import path
from django.views.generic import TemplateView

from .web_views import DashboardView, LoginView, LogoutView, ProfileView

app_name = "accounts_web"

urlpatterns = [
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
