"""
إدارة جلسة الزائر - عزل البيانات بمفتاح الجلسة
Guest session management - isolate data by session_key
"""
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

# مفاتيح الجلسة للزائر
SESSION_KEY_UPLOAD_ID = "guest_upload_id"
SESSION_KEY_EXTRACTED_TEXT = "guest_extracted_text"
SESSION_KEY_FILENAME = "guest_filename"
SESSION_KEY_PAGE_COUNT = "guest_page_count"
SESSION_KEY_UPLOADED_AT = "guest_uploaded_at"
SESSION_KEY_EXTRACTION_METHOD = "guest_extraction_method"


def ensure_session(request) -> str:
    """
    التأكد من وجود جلسة وإرجاع session_key
    Ensure Django session exists and return session_key
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def store_guest_document(request, upload_id: str, filename: str, extracted_text: str, meta: dict) -> None:
    """
    تخزين بيانات المستند المستخرج في جلسة الزائر
    Store extracted document data in guest session
    """
    request.session[SESSION_KEY_UPLOAD_ID] = str(upload_id)
    request.session[SESSION_KEY_FILENAME] = filename
    request.session[SESSION_KEY_EXTRACTED_TEXT] = extracted_text
    request.session[SESSION_KEY_PAGE_COUNT] = meta.get("page_count", 0)
    request.session[SESSION_KEY_EXTRACTION_METHOD] = meta.get("method", "")
    request.session[SESSION_KEY_UPLOADED_AT] = timezone.now().isoformat()
    request.session.modified = True


def get_guest_text(request) -> str | None:
    """جلب النص المستخرج من الجلسة"""
    return request.session.get(SESSION_KEY_EXTRACTED_TEXT)


def get_guest_upload_id(request) -> str | None:
    """جلب معرّف الرفع من الجلسة"""
    return request.session.get(SESSION_KEY_UPLOAD_ID)


def get_guest_session_info(request) -> dict | None:
    """جلب معلومات جلسة الزائر الحالية"""
    upload_id = get_guest_upload_id(request)
    text = get_guest_text(request)
    if not upload_id or not text:
        return None
    return {
        "upload_id": upload_id,
        "filename": request.session.get(SESSION_KEY_FILENAME, ""),
        "text_length": len(text),
        "page_count": request.session.get(SESSION_KEY_PAGE_COUNT, 0),
        "extraction_method": request.session.get(SESSION_KEY_EXTRACTION_METHOD, ""),
        "uploaded_at": request.session.get(SESSION_KEY_UPLOADED_AT, ""),
    }


def clear_guest_session(request) -> None:
    """مسح بيانات الزائر من الجلسة"""
    for key in (
        SESSION_KEY_UPLOAD_ID,
        SESSION_KEY_EXTRACTED_TEXT,
        SESSION_KEY_FILENAME,
        SESSION_KEY_PAGE_COUNT,
        SESSION_KEY_UPLOADED_AT,
        SESSION_KEY_EXTRACTION_METHOD,
    ):
        request.session.pop(key, None)
    request.session.modified = True


def check_guest_rate_limit(session_key: str) -> None:
    """تحديد معدل طلبات AI للزوار"""
    from apps.ai_services.exceptions import RateLimitExceededError

    limit = settings.AI_RATE_LIMIT_GUEST
    cache_key = f"ai_rate_guest_{session_key}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        raise RateLimitExceededError(limit)
    cache.set(cache_key, count + 1, timeout=3600)


def verify_guest_upload_access(request, upload_id: str) -> bool:
    """التحقق أن الرفع يخص جلسة الزائر الحالية"""
    session_upload_id = get_guest_upload_id(request)
    return session_upload_id == str(upload_id)
