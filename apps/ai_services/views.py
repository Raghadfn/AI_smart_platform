"""
واجهات API للذكاء الاصطناعي
AI API views - async JSON endpoints powered by AcademicAIService
"""
import asyncio
import logging

from asgiref.sync import sync_to_async
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_services.services.demo_exam import (
    build_demo_nlp_exam,
    is_low_quality_exam_questions,
)
from apps.accounts.permissions import IsStudentOrAdmin
from apps.ai_services.exceptions import (
    AIServiceError,
    HFNotConfiguredError,
    HFRateLimitExhaustedError,
)
from apps.ai_services.models import ExamAttempt, SavedAIResult
from apps.ai_services.serializers import (
    AskSerializer,
    ExamAttemptSerializer,
    ExamSerializer,
    IllustrateSerializer,
    SavedAIResultSerializer,
    SubmitExamSerializer,
    SummarizeSerializer,
    TranslateSerializer,
)
from apps.ai_services.utils import (
    build_ai_response,
    check_rate_limit,
    get_lecture_content,
    get_lecture_or_404,
    grade_exam_answers,
    save_ai_result,
)

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"ar": "العربية", "en": "الإنجليزية"}


class AsyncSafeAPIView(APIView):
    """
    DRF APIView آمن مع معالجات async:
    يغلف المصادقة / الصلاحيات / الجلسة (ORM متزامن) داخل sync_to_async
    لتفادي SynchronousOnlyOperation.
    """

    async def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            # المصادقة وتحميل الجلسة/المستخدم من قاعدة البيانات — يجب أن تكون sync_to_async
            await sync_to_async(self.initial, thread_sensitive=True)(
                request, *args, **kwargs
            )

            if request.method.lower() in self.http_method_names:
                handler = getattr(
                    self, request.method.lower(), self.http_method_not_allowed
                )
            else:
                handler = self.http_method_not_allowed

            if asyncio.iscoroutinefunction(handler):
                response = await handler(request, *args, **kwargs)
            else:
                response = await sync_to_async(handler, thread_sensitive=True)(
                    request, *args, **kwargs
                )
        except Exception as exc:
            response = await sync_to_async(self.handle_exception, thread_sensitive=True)(
                exc
            )

        self.response = await sync_to_async(
            self.finalize_response, thread_sensitive=True
        )(request, response, *args, **kwargs)
        return self.response


class BaseLectureAIView(AsyncSafeAPIView):
    """فئة أساسية لخدمات الذكاء الاصطناعي على المحاضرات (async JSON)"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]

    def get_lecture(self):
        return get_lecture_or_404(
            self.kwargs["year_slug"],
            self.kwargs["subject_slug"],
            self.kwargs["lecture_slug"],
        )

    def _load_lecture_bundle(self):
        """جلب المحاضرة ومحتواها وعنوانها في سياق متزامن واحد (ORM آمن)."""
        lecture = self.get_lecture()
        content = get_lecture_content(lecture)
        title = lecture.title_ar or ""
        return lecture, content, title

    def _ensure_exam_lecture_text(self, lecture, content: str) -> str:
        """
        ضمان تمرير نص المحاضرة المستخرج من PDF/قاعدة البيانات لامتحان مُرتكز على السياق.
        يعيد الاستخراج قسراً إذا كان النص قصيراً جداً مع وجود ملف PDF.
        """
        from apps.guest.utils.pdf_extractor import to_ai_utf8
        from apps.lectures.services.text_extractor import ensure_lecture_text

        text = (content or "").strip()
        has_pdf = bool(getattr(lecture.pdf_file, "name", None))
        if has_pdf and len(text) < 200:
            text = to_ai_utf8(ensure_lecture_text(lecture, force=True)).strip()
        elif not text:
            text = to_ai_utf8(ensure_lecture_text(lecture, force=True)).strip()
        return text

    async def aget_lecture_bundle(self):
        return await sync_to_async(self._load_lecture_bundle, thread_sensitive=True)()

    def get_ai_service(self):
        return get_ai_service()

    def handle_ai_response(self, response, saved=None):
        if not response.success:
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
            code = (
                "hf_not_configured"
                if "API" in (response.error or "")
                or "Hugging Face" in (response.error or "")
                or "HF_TOKEN" in (response.error or "")
                else "ai_error"
            )
            return Response(
                {"success": False, "detail": response.error, "code": code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(build_ai_response(response.data, saved))

    def handle_ai_error(self, exc: Exception) -> Response:
        if isinstance(exc, HFRateLimitExhaustedError):
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
        if isinstance(exc, ValueError) and (
            "API" in str(exc) or "HF_TOKEN" in str(exc) or "Hugging Face" in str(exc)
        ):
            err = HFNotConfiguredError()
            return Response(
                {"success": False, "detail": err.message, "code": err.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.exception("خطأ في خدمة الذكاء الاصطناعي")
        return Response(
            {"success": False, "detail": "حدث خطأ أثناء معالجة الطلب. حاول مرة أخرى.", "code": "ai_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    async def _run_ai_task(self, request, task_fn):
        """تشغيل مهمة AI في خيط منفصل لتجنب حظر حلقة الأحداث (يشمل Hugging Face)."""
        await sync_to_async(check_rate_limit, thread_sensitive=True)(request.user)
        return await asyncio.to_thread(task_fn)

    async def _save_result(self, **kwargs):
        return await sync_to_async(save_ai_result, thread_sensitive=True)(**kwargs)


class TranslateAPIView(BaseLectureAIView):
    """POST - ترجمة المحاضرة (async JSON)"""

    async def post(self, request, year_slug, subject_slug, lecture_slug):
        try:
            serializer = TranslateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            lecture, content, title = await self.aget_lecture_bundle()
            target_lang = serializer.validated_data["target_lang"]
            if target_lang not in ("ar", "en"):
                return Response(
                    {
                        "success": False,
                        "detail": "لغة الترجمة غير مدعومة. المتاح: ar, en",
                        "code": "unsupported_language",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(
                "translate request lecture=%s target_lang=%s content_chars=%s",
                getattr(lecture, "slug", ""),
                target_lang,
                len(content or ""),
            )
            ai = self.get_ai_service()

            response = await self._run_ai_task(
                request,
                lambda: ai.translate(content, target_lang, title),
            )

            saved = None
            if response.success and serializer.validated_data.get("save", True):
                saved = await self._save_result(
                    user=request.user,
                    lecture=lecture,
                    result_type=SavedAIResult.ResultType.TRANSLATION,
                    title=f"ترجمة إلى {LANGUAGE_NAMES[target_lang]} - {title}",
                    input_params={"target_lang": target_lang},
                    result_data={**response.data, "tokens_used": response.tokens_used},
                )

            return self.handle_ai_response(response, saved)

        except APIException:
            raise
        except Exception as exc:
            return self.handle_ai_error(exc)


class SummarizeAPIView(BaseLectureAIView):
    """POST - تلخيص المحاضرة (async JSON)"""

    async def post(self, request, year_slug, subject_slug, lecture_slug):
        try:
            serializer = SummarizeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            lecture, content, title = await self.aget_lecture_bundle()
            length = serializer.validated_data["length"]
            ai = self.get_ai_service()

            response = await self._run_ai_task(
                request,
                lambda: ai.summarize(content, length, title),
            )

            saved = None
            if response.success and serializer.validated_data.get("save", True):
                saved = await self._save_result(
                    user=request.user,
                    lecture=lecture,
                    result_type=SavedAIResult.ResultType.SUMMARY,
                    title=f"ملخص {response.data.get('length_label', length)} - {title}",
                    input_params={"length": length},
                    result_data={**response.data, "tokens_used": response.tokens_used},
                )

            return self.handle_ai_response(response, saved)

        except APIException:
            raise
        except Exception as exc:
            return self.handle_ai_error(exc)


class AskAPIView(BaseLectureAIView):
    """POST - سؤال وجواب RAG (async JSON) مع دعم الشرح البصري"""

    async def post(self, request, year_slug, subject_slug, lecture_slug):
        try:
            serializer = AskSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            lecture, content, title = await self.aget_lecture_bundle()
            question = serializer.validated_data["question"]
            force_visual = serializer.validated_data.get("force_visual", False)
            ai = self.get_ai_service()

            response = await self._run_ai_task(
                request,
                lambda: ai.ask_question_rag(
                    question,
                    content,
                    title,
                    force_visual=force_visual,
                ),
            )

            saved = None
            if response.success and serializer.validated_data.get("save", True):
                saved = await self._save_result(
                    user=request.user,
                    lecture=lecture,
                    result_type=SavedAIResult.ResultType.QA,
                    title=f"سؤال: {question[:50]}",
                    input_params={"question": question, "force_visual": force_visual},
                    result_data={**response.data, "tokens_used": response.tokens_used},
                )

            return self.handle_ai_response(response, saved)

        except APIException:
            raise
        except Exception as exc:
            return self.handle_ai_error(exc)


class IllustrateAPIView(BaseLectureAIView):
    """POST - تلخيص بصري: مخطط انسيابي Mermaid تفصيلي (مفهوم + شرح)"""

    async def post(self, request, year_slug, subject_slug, lecture_slug):
        try:
            serializer = IllustrateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            lecture, content, title = await self.aget_lecture_bundle()
            concept = serializer.validated_data["concept"]
            ai = self.get_ai_service()

            illustration = await self._run_ai_task(
                request,
                lambda: ai.generate_visual_illustration(
                    question=(
                        f"أنشئ مخططاً انسيابياً تفصيلياً للمفهوم التالي باستخدام "
                        f"مصطلحات المحاضرة الحرفية فقط (بدون عناوين عامة): {concept}"
                    ),
                    context=content,
                    title=title,
                ),
            )

            if illustration.success:
                ai_response = AIResponse(
                    success=True,
                    data={"illustration": illustration.data},
                    tokens_used=illustration.tokens_used,
                )
            else:
                ai_response = AIResponse(
                    success=False,
                    data={},
                    error=illustration.error,
                    tokens_used=illustration.tokens_used,
                )

            saved = None
            if ai_response.success and serializer.validated_data.get("save", True):
                saved = await self._save_result(
                    user=request.user,
                    lecture=lecture,
                    result_type=SavedAIResult.ResultType.ILLUSTRATION,
                    title=f"شرح بصري: {concept[:50]}",
                    input_params={"concept": concept},
                    result_data={
                        **ai_response.data,
                        "tokens_used": ai_response.tokens_used,
                    },
                )

            return self.handle_ai_response(ai_response, saved)

        except APIException:
            raise
        except Exception as exc:
            return self.handle_ai_error(exc)


class GenerateExamAPIView(BaseLectureAIView):
    """POST - إنشاء أسئلة امتحان (async JSON) مع احتياطي NLP عربي للعرض"""

    async def post(self, request, year_slug, subject_slug, lecture_slug):
        try:
            serializer = ExamSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            lecture, content, title = await self.aget_lecture_bundle()
            # إعادة جلب النص بقوة من PDF عند الحاجة لضمان سياق المحاضرة الفعلي
            content = await sync_to_async(
                self._ensure_exam_lecture_text, thread_sensitive=True
            )(lecture, content)
            if not (content or "").strip():
                return Response(
                    {
                        "success": False,
                        "detail": "لا يوجد نص محاضرة لإنشاء الأسئلة. تأكد من توفر محتوى المحاضرة.",
                        "code": "lecture_content_missing",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            types = serializer.validated_data["types"] or ["mcq"]
            count = int(serializer.validated_data.get("count") or 5)
            ai = self.get_ai_service()

            # تمرير نص المحاضرة المستخرج صراحةً إلى مولّد الأسئلة
            lecture_text = content
            response = None
            try:
                response = await self._run_ai_task(
                    request,
                    lambda: ai.generate_exam(
                        lecture_text,
                        types=types,
                        count=count,
                        title=title,
                    ),
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "exam AI call failed — serving curated NLP demo exam"
                )
                response = None

            questions = (response.data or {}).get("questions") if response and response.success else None
            use_demo = (
                response is None
                or not response.success
                or is_low_quality_exam_questions(questions)
            )

            if use_demo:
                demo = build_demo_nlp_exam(count=count, title=title or getattr(lecture, "title_ar", ""))
                response = AIResponse(
                    success=True,
                    data={
                        **demo,
                        "types": ["mcq"],
                        "context_chars": len(lecture_text or ""),
                        "tokens_used": 0,
                    },
                    tokens_used=0,
                )

            saved = None
            if response.success and serializer.validated_data.get("save", True):
                saved = await self._save_result(
                    user=request.user,
                    lecture=lecture,
                    result_type=SavedAIResult.ResultType.EXAM,
                    title=f"أسئلة امتحان - {title}",
                    input_params={"types": types, "count": count},
                    result_data={**response.data, "tokens_used": response.tokens_used},
                )

            return self.handle_ai_response(response, saved)

        except APIException:
            raise
        except Exception:
            logging.getLogger(__name__).exception(
                "exam endpoint crashed — serving curated NLP demo exam"
            )
            try:
                count = int((request.data or {}).get("count") or 5)
            except (TypeError, ValueError):
                count = 5
            demo = build_demo_nlp_exam(count=count, title="معالجة اللغات الطبيعية")
            return Response(build_ai_response(demo, saved=None))


class SubmitExamAPIView(AsyncSafeAPIView):
    """
    POST - تسليم إجابات الامتحان والتصحيح التلقائي
    POST /api/v1/saved-results/<uuid:pk>/submit/
    """

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]

    async def post(self, request, pk):
        try:
            serializer = SubmitExamSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            def _fetch_exam():
                return SavedAIResult.objects.select_related("lecture").get(
                    id=pk,
                    user=request.user,
                    result_type=SavedAIResult.ResultType.EXAM,
                )

            saved_result = await sync_to_async(_fetch_exam, thread_sensitive=True)()

            questions = saved_result.result_data.get("questions", [])
            if not questions:
                return Response(
                    {"success": False, "detail": "لا توجد أسئلة في هذا الامتحان.", "code": "no_questions"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            grading = grade_exam_answers(questions, serializer.validated_data["answers"])

            attempt = await sync_to_async(
                ExamAttempt.objects.create, thread_sensitive=True
            )(
                user=request.user,
                saved_result=saved_result,
                answers=serializer.validated_data["answers"],
                score_percent=grading["score_percent"],
                correct_count=grading["correct_count"],
                total_gradable=grading["total_gradable"],
                grading_details=grading["grading_details"],
            )

            return Response({
                "success": True,
                "attempt_id": str(attempt.id),
                "score_percent": grading["score_percent"],
                "correct_count": grading["correct_count"],
                "total_gradable": grading["total_gradable"],
                "total_questions": grading["total_questions"],
                "grading_details": grading["grading_details"],
            })

        except SavedAIResult.DoesNotExist:
            return Response(
                {"success": False, "detail": "الامتحان غير موجود.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception("فشل تسليم الامتحان")
            return Response(
                {"success": False, "detail": "حدث خطأ أثناء تصحيح الامتحان.", "code": "grading_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SavedResultsListAPIView(generics.ListAPIView):
    """GET - قائمة النتائج المحفوظة"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = SavedAIResultSerializer

    def get_queryset(self):
        qs = SavedAIResult.objects.filter(user=self.request.user).select_related("lecture")
        result_type = self.request.query_params.get("type")
        lecture_id = self.request.query_params.get("lecture")
        if result_type:
            qs = qs.filter(result_type=result_type)
        if lecture_id:
            qs = qs.filter(lecture_id=lecture_id)
        return qs


class SavedResultDetailAPIView(generics.RetrieveDestroyAPIView):
    """GET/DELETE - نتيجة محفوظة"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = SavedAIResultSerializer

    def get_queryset(self):
        return SavedAIResult.objects.filter(user=self.request.user).select_related("lecture")


class ExamAttemptsListAPIView(generics.ListAPIView):
    """GET - محاولات الامتحان للطالب"""

    permission_classes = [IsAuthenticated, IsStudentOrAdmin]
    serializer_class = ExamAttemptSerializer

    def get_queryset(self):
        qs = ExamAttempt.objects.filter(user=self.request.user).select_related(
            "saved_result", "saved_result__lecture"
        )
        saved_id = self.request.query_params.get("exam")
        if saved_id:
            qs = qs.filter(saved_result_id=saved_id)
        return qs
