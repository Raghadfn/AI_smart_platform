"""
مسلسلات API لوضع الزائر
Guest mode API serializers
"""
from rest_framework import serializers


class GuestSummarizeSerializer(serializers.Serializer):
    """مسلسل طلب التلخيص للزائر"""

    length = serializers.ChoiceField(
        choices=[("short", "قصير"), ("medium", "متوسط"), ("detailed", "مفصل")],
        default="medium",
    )


class GuestAskSerializer(serializers.Serializer):
    """مسلسل طلب سؤال وجواب للزائر"""

    question = serializers.CharField(min_length=3, max_length=1000)
