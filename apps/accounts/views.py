"""
واجهات API للمصادقة
Authentication API views
"""
from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsPlatformAdmin
from .serializers import AdminCreateUserSerializer, LoginSerializer, UserSerializer
from .utils import clear_jwt_cookies, get_tokens_for_user, set_jwt_cookies


class LoginAPIView(APIView):
    """
    تسجيل الدخول - إرجاع JWT وإنشاء جلسة
    POST /api/v1/auth/login/
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # لا يتطلب مصادقة مسبقة

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        # إنشاء جلسة Django للقوالب
        login(request, user)

        response = Response(
            {
                "success": True,
                "message": "تم تسجيل الدخول بنجاح.",
                "tokens": tokens,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        return set_jwt_cookies(response, tokens)


class RefreshTokenAPIView(APIView):
    """
    تجديد رمز الوصول
    POST /api/v1/auth/refresh/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"success": False, "detail": "رمز التجديد مطلوب."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            new_tokens = {"access": access_token, "refresh": str(refresh)}

            response = Response(
                {
                    "success": True,
                    "message": "تم تجديد الرمز بنجاح.",
                    "tokens": new_tokens,
                },
                status=status.HTTP_200_OK,
            )
            return set_jwt_cookies(response, new_tokens)

        except TokenError:
            return Response(
                {"success": False, "detail": "رمز التجديد غير صالح أو منتهي الصلاحية."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutAPIView(APIView):
    """
    تسجيل الخروج - إبطال JWT وحذف الجلسة
    POST /api/v1/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # الرمز قد يكون منتهياً مسبقاً

        logout(request)

        response = Response(
            {"success": True, "message": "تم تسجيل الخروج بنجاح."},
            status=status.HTTP_200_OK,
        )
        return clear_jwt_cookies(response)


class MeAPIView(APIView):
    """
    بيانات المستخدم الحالي
    GET /api/v1/auth/me/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "success": True,
                "user": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminCreateUserAPIView(APIView):
    """
    إنشاء مستخدم جديد - للمسؤولين فقط (لا يوجد تسجيل ذاتي)
    POST /api/v1/auth/admin/users/
    """

    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": f"تم إنشاء المستخدم '{user.username}' بنجاح.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )
