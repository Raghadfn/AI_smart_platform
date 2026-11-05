"""
مصادقة JWT من ملفات تعريف الارتباط
JWT authentication from httpOnly cookies
"""
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    قراءة رمز JWT من ملف تعريف الارتباط إذا لم يُرسل في الترويسة
    Read JWT from cookie if not provided in Authorization header
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
