"""
خدمة معالجة رفع ملفات الزوار
Guest upload processing service
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.guest.exceptions import GuestUploadError
from apps.guest.models import GuestUpload
from apps.guest.utils.pdf_extractor import PDFExtractor
from apps.guest.utils.session import ensure_session, store_guest_document

logger = logging.getLogger(__name__)


def process_guest_upload(request, uploaded_file) -> dict:
    """
    معالجة رفع PDF من زائر
    Process guest PDF upload: validate → extract → save → session

    Returns:
        dict with upload_id, filename, text_length, page_count, method, truncated
    """
    session_key = ensure_session(request)
    max_size = settings.MAX_UPLOAD_SIZE_BYTES

    # 1. التحقق من الملف
    PDFExtractor.validate_pdf_file(uploaded_file, max_size)

    # 2. إنشاء سجل الرفع
    expires_at = timezone.now() + timedelta(hours=settings.GUEST_FILE_EXPIRY_HOURS)
    guest_upload = GuestUpload.objects.create(
        session_key=session_key,
        original_filename=uploaded_file.name,
        pdf_file=uploaded_file,
        processing_status=GuestUpload.ProcessingStatus.PROCESSING,
        expires_at=expires_at,
    )

    try:
        # 3. استخراج النص
        extraction = PDFExtractor.extract_text(file_path=guest_upload.pdf_file.path)

        if not extraction["text"].strip():
            raise GuestUploadError(
                "لم يتم العثور على نص في الملف. قد يكون الملف ممسوحاً ضوئياً (صور فقط).",
                code="no_text_found",
            )

        # 4. تحديث السجل
        guest_upload.extracted_text = extraction["text"]
        guest_upload.processing_status = GuestUpload.ProcessingStatus.READY
        guest_upload.save(update_fields=["extracted_text", "processing_status"])

        # 5. تخزين في الجلسة للوصول السريع من AI
        store_guest_document(
            request,
            upload_id=str(guest_upload.id),
            filename=uploaded_file.name,
            extracted_text=extraction["text"],
            meta=extraction,
        )

        return {
            "upload_id": str(guest_upload.id),
            "filename": uploaded_file.name,
            "text_length": len(extraction["text"]),
            "page_count": extraction.get("page_count", 0),
            "method": extraction.get("method", ""),
            "truncated": extraction.get("truncated", False),
            "session_key": session_key,
        }

    except GuestUploadError:
        guest_upload.processing_status = GuestUpload.ProcessingStatus.FAILED
        guest_upload.processing_error = "فشل استخراج النص"
        guest_upload.save(update_fields=["processing_status", "processing_error"])
        raise
    except Exception as exc:
        logger.exception("فشل معالجة رفع الزائر")
        guest_upload.processing_status = GuestUpload.ProcessingStatus.FAILED
        guest_upload.processing_error = str(exc)
        guest_upload.save(update_fields=["processing_status", "processing_error"])
        raise GuestUploadError(f"فشلت معالجة الملف: {exc}", code="processing_failed") from exc


def get_guest_content(request) -> str:
    """جلب محتوى المستند من الجلسة أو قاعدة البيانات كـ UTF-8 نظيف لـ Groq"""
    from apps.guest.utils.pdf_extractor import to_ai_utf8
    from apps.guest.utils.session import get_guest_text, get_guest_upload_id

    text = to_ai_utf8(get_guest_text(request) or "").strip()
    if text:
        return text.encode("utf-8").decode("utf-8")

    upload_id = get_guest_upload_id(request)
    if upload_id:
        try:
            upload = GuestUpload.objects.get(
                id=upload_id,
                processing_status=GuestUpload.ProcessingStatus.READY,
            )
            return to_ai_utf8(upload.extracted_text).encode("utf-8").decode("utf-8")
        except GuestUpload.DoesNotExist:
            pass

    raise GuestUploadError(
        "لا يوجد ملف مرفوع. يرجى رفع ملف PDF أولاً.",
        code="no_upload",
    )
