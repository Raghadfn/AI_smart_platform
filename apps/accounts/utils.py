"""
أدوات مساعدة للمصادقة
Authentication utility functions
"""
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    """إنشاء رموز JWT للمستخدم"""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def set_jwt_cookies(response, tokens):
    """
    تعيين رموز JWT في ملفات تعريف الارتباط الآمنة
    Set JWT tokens in secure httpOnly cookies
    """
    access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    response.set_cookie(
        key="access_token",
        value=tokens["access"],
        max_age=int(access_lifetime.total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh"],
        max_age=int(refresh_lifetime.total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return response


def clear_jwt_cookies(response):
    """حذف ملفات تعريف ارتباط JWT"""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
