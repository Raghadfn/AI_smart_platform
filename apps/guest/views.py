"""
واجهات وضع الزائر - رفع PDF وخدمات AI
Guest mode views - PDF upload and AI features
"""
import logging

from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from academic_platform.ai_services import get_ai_service
from apps.ai_services.exceptions import (
    AIServiceError,
    HFRateLimitExhaustedError,
    RateLimitExceededError,
)
from apps.guest.exceptions import GuestUploadError
from apps.guest.models import GuestAIResult, GuestUpload
from apps.guest.serializers import GuestAskSerializer, GuestSummarizeSerializer
from apps.guest.services import get_guest_content, process_guest_upload
from apps.guest.utils.session import (
    ensure_session,
    get_guest_session_info,
    verify_guest_upload_access,
)
from apps.guest.utils.session import check_guest_rate_limit as guest_rate_limit

logger = logging.getLogger(__name__)


def _handle_guest_error(exc: Exception) -> Response:
    """معالجة أخطاء الزائر"""
    if isinstance(exc, GuestUploadError):
        return Response(
            {"success": False, "detail": exc.message, "code": exc.code},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, (RateLimitExceededError, HFRateLimitExhaustedError)):
        return Response(
            {"success": False, "detail": exc.message, "code": exc.code},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if isinstance(exc, AIServiceError):
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if exc.code in ("rate_limit_exceeded", "hf_rate_limited", "groq_rate_limited")
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {"success": False, "detail": exc.message, "code": exc.code},
            status=status_code,
        )
    logger.exception("خطأ غير متوقع في وضع الزائر")
    return Response(
        {"success": False, "detail": "حدث خطأ أثناء المعالجة.", "code": "server_error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _guest_ai_failure(response) -> Response | None:
    """تحويل فشل AIResponse إلى استجابة HTTP ودية عند ازدحام Hugging Face"""
    if response.success:
        return None
    busy = HFRateLimitExhaustedError.DEFAULT_MESSAGE_AR
    if response.error == busy or (
        response.error and "يُعالج العديد من الطلبات" in response.error
    ):
        return Response(
            {
                "success": False,
                "detail": response.error or busy,
                "code": "hf_rate_limited",
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    return Response(
        {"success": False, "detail": response.error, "code": "ai_error"},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ==========================================
# رفع ملف PDF - Guest Upload View
# ==========================================

@csrf_protect
@require_http_methods(["GET", "POST"])
def guest_upload_view(request):
    """
    واجهة رفع PDF للزوار (صفحة ويب)
    Guest PDF upload view - uses session_id to isolate temporary data

    GET  /guest/          → صفحة الرفع
    POST /guest/          → رفع ملف PDF واستخراج النص
    """
    # التأكد من وجود جلسة لعزل بيانات الزائر
    ensure_session(request)

    if request.method == "GET":
        context = {
            "session_info": get_guest_session_info(request),
        }
        return render(request, "guest/upload.html", context)

    # POST - رفع الملف
    uploaded_file = request.FILES.get("pdf_file")
    if not uploaded_file:
        return render(request, "guest/upload.html", {
            "error": "يرجى اختيار ملف PDF.",
            "session_info": get_guest_session_info(request),
        })

    try:
        result = process_guest_upload(request, uploaded_file)
        return redirect("guest_web:workspace", upload_id=result["upload_id"])
    except GuestUploadError as exc:
        return render(request, "guest/upload.html", {
            "error": exc.message,
            "session_info": get_guest_session_info(request),
        })
    except Exception as exc:
        logger.exception("فشل رفع ملف الزائر")
        return render(request, "guest/upload.html", {
            "error": "حدث خطأ أثناء معالجة الملف. حاول مرة أخرى.",
            "session_info": get_guest_session_info(request),
        })


class GuestUploadAPIView(APIView):
    """
    API رفع PDF للزوار
    POST /api/v1/guest/upload/
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ensure_session(request)

        uploaded_file = request.FILES.get("pdf_file") or request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"success": False, "detail": "ملف PDF مطلوب.", "code": "missing_file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = process_guest_upload(request, uploaded_file)
            return Response({"success": True, **result}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return _handle_guest_error(exc)


class GuestUploadStatusAPIView(APIView):
    """
    حالة معالجة الرفع
    GET /api/v1/guest/upload/<upload_id>/status/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, upload_id):
        ensure_session(request)

        if not verify_guest_upload_access(request, upload_id):
            return Response(
                {"success": False, "detail": "غير مصرح بالوصول لهذا الملف."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            upload = GuestUpload.objects.get(id=upload_id)
            return Response({
                "success": True,
                "upload_id": str(upload.id),
                "filename": upload.original_filename,
                "status": upload.processing_status,
                "text_length": len(upload.extracted_text),
                "error": upload.processing_error or None,
            })
        except GuestUpload.DoesNotExist:
            return Response(
                {"success": False, "detail": "الملف غير موجود."},
                status=status.HTTP_404_NOT_FOUND,
            )


class GuestSummarizeAPIView(APIView):
    """
    تلخيص ملف الزائر
    POST /api/v1/guest/upload/<upload_id>/summarize/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, upload_id):
        ensure_session(request)

        if not verify_guest_upload_access(request, upload_id):
            return Response(
                {"success": False, "detail": "غير مصرح."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            guest_rate_limit(request.session.session_key)
            serializer = GuestSummarizeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            content = get_guest_content(request)
            length = serializer.validated_data["length"]
            filename = request.session.get("guest_filename", "ملف PDF")

            ai = get_ai_service()
            response = ai.summarize(content, length, title=filename)

            if not response.success:
                return _guest_ai_failure(response)

            # حفظ نتيجة AI للزائر
            upload = GuestUpload.objects.get(id=upload_id)
            GuestAIResult.objects.create(
                upload=upload,
                result_type=GuestAIResult.ResultType.SUMMARY,
                input_params={"length": length},
                result_data={**response.data, "tokens_used": response.tokens_used},
            )

            return Response({
                "success": True,
                "data": response.data,
                "tokens_used": response.tokens_used,
            })

        except Exception as exc:
            return _handle_guest_error(exc)


class GuestAskAPIView(APIView):
    """
    سؤال وجواب على ملف الزائر
    POST /api/v1/guest/upload/<upload_id>/ask/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, upload_id):
        ensure_session(request)

        if not verify_guest_upload_access(request, upload_id):
            return Response(
                {"success": False, "detail": "غير مصرح."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            guest_rate_limit(request.session.session_key)
            serializer = GuestAskSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            content = get_guest_content(request)
            question = serializer.validated_data["question"]
            filename = request.session.get("guest_filename", "ملف PDF")

            ai = get_ai_service()
            response = ai.ask_question_rag(question, content, title=filename)

            if not response.success:
                return _guest_ai_failure(response)

            upload = GuestUpload.objects.get(id=upload_id)
            GuestAIResult.objects.create(
                upload=upload,
                result_type=GuestAIResult.ResultType.QA,
                input_params={"question": question},
                result_data={**response.data, "tokens_used": response.tokens_used},
            )

            return Response({
                "success": True,
                "data": response.data,
                "tokens_used": response.tokens_used,
            })

        except Exception as exc:
            return _handle_guest_error(exc)
