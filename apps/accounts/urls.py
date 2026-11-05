"""
مسارات API للمصادقة
Authentication API routes
"""
from django.urls import path

from .views import (
    AdminCreateUserAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    RefreshTokenAPIView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="api_refresh"),
    path("logout/", LogoutAPIView.as_view(), name="api_logout"),
    path("me/", MeAPIView.as_view(), name="api_me"),
    path("admin/users/", AdminCreateUserAPIView.as_view(), name="api_admin_create_user"),
]
