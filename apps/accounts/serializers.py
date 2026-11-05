"""
مسلسلات API للمصادقة وملفات المستخدمين
Authentication and user profile serializers
"""
from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import StudentProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):
    """مسلسل ملف الطالب"""

    class Meta:
        model = StudentProfile
        fields = (
            "full_name_ar",
            "student_id",
            "preferred_language",
        )


class UserSerializer(serializers.ModelSerializer):
    """مسلسل بيانات المستخدم للعرض"""

    profile = StudentProfileSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "is_active",
            "date_joined",
            "last_login",
            "profile",
        )
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """مسلسل تسجيل الدخول"""

    username = serializers.CharField(
        max_length=150,
        error_messages={"required": "اسم المستخدم مطلوب."},
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={"required": "كلمة المرور مطلوبة."},
    )

    def validate(self, attrs):
        username = attrs.get("username", "").strip()
        password = attrs.get("password", "")

        if not username or not password:
            raise serializers.ValidationError(
                {"detail": "اسم المستخدم وكلمة المرور مطلوبان."},
                code="invalid_credentials",
            )

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                {"detail": "اسم المستخدم أو كلمة المرور غير صحيحة."},
                code="invalid_credentials",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "هذا الحساب معطّل. تواصل مع المسؤول."},
                code="account_disabled",
            )

        if not user.is_student and not user.is_platform_admin and not user.is_staff:
            raise serializers.ValidationError(
                {"detail": "ليس لديك صلاحية للوصول إلى المنصة."},
                code="permission_denied",
            )

        attrs["user"] = user
        return attrs


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """
    مسلسل إنشاء مستخدم من قبل المسؤول فقط
    Admin-only user creation serializer
    """

    password = serializers.CharField(write_only=True, min_length=8)
    full_name_ar = serializers.CharField(write_only=True, required=False, allow_blank=True)
    student_id = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "role",
            "full_name_ar",
            "student_id",
        )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("اسم المستخدم موجود مسبقاً.")
        return value

    def create(self, validated_data):
        full_name_ar = validated_data.pop("full_name_ar", "")
        student_id = validated_data.pop("student_id", "")
        password = validated_data.pop("password")
        role = validated_data.get("role", User.Role.STUDENT)

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if role == User.Role.STUDENT:
            StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name_ar": full_name_ar or user.get_full_name() or user.username,
                    "student_id": student_id,
                },
            )

        return user
