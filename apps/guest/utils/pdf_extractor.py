"""
استخراج النص من ملفات PDF مع دعم كامل للعربية
PDF text extraction via PyMuPDF + arabic_reshaper + bidi

ملاحظة هامة لـ Groq / LLMs:
- نماذج اللغة تفهم العربية المنطقية (U+0600–U+06FF) وليست أشكال العرض Presentation Forms.
- arabic_reshaper + get_display تُستخدم لإعادة بناء العربية للمعاينة في الـ console.
- النص المحفوظ والمُرسل إلى Groq يبقى UTF-8 منطقياً نظيفاً بعد التنظيف.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata

import arabic_reshaper
import fitz  # PyMuPDF
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

MAX_PAGES = 200
MAX_EXTRACTED_CHARS = 500_000

_PRESENTATION_RE = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")
_LOGICAL_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_ESCAPED_UNICODE_RE = re.compile(r"\\u[0-9a-fA-F]{4}")
_HEX_DUMPISH_RE = re.compile(r"(?:\\x[0-9a-fA-F]{2}){3,}")


def as_clean_utf8(text: str | bytes | None) -> str:
    """معاملة النص دائماً كسلسلة UTF-8 نظيفة (كما طُلب صراحةً)."""
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    elif not isinstance(text, str):
        text = str(text)

    # فكّ escape-ات شائعة مثل \\u0645 إن وُجدت كنص حرفي
    if _ESCAPED_UNICODE_RE.search(text):
        try:
            text = text.encode("utf-8", errors="replace").decode("unicode_escape", errors="replace")
        except Exception:
            pass

    # توحيد الحروف المركّبة؛ NFKC يحوّل Presentation Forms إلى حروف عربية قياسية
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        ch
        for ch in text
        if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 0xFEFF)
    )
    return text.encode("utf-8", errors="replace").decode("utf-8")


def reshape_arabic_for_display(text: str) -> str:
    """
    إعادة بناء تخطيط العربية للعرض/التصحيح:
    arabic_reshaper.reshape → bidi.get_display
    """
    clean = as_clean_utf8(text)
    if not clean.strip():
        return ""
    try:
        reshaped = arabic_reshaper.reshape(clean)
        displayed = get_display(reshaped)
        return as_clean_utf8(displayed)
    except Exception as exc:
        logger.warning("Arabic reshape/bidi failed: %s", exc)
        return clean


def to_ai_utf8(text: str) -> str:
    """
    نص جاهز لـ Groq: UTF-8 منطقي بعد تنظيف/NFKC.
    لا نُبقي أشكال العرض المقلوبة لأنها تُربك النموذج.
    """
    clean = as_clean_utf8(text)
    # تأكد مرة أخرى من إزالة بقايا Presentation Forms إن وُجدت
    if _PRESENTATION_RE.search(clean):
        clean = unicodedata.normalize("NFKC", clean)
        clean = clean.encode("utf-8", errors="replace").decode("utf-8")
    return clean


def looks_corrupted_arabic(text: str) -> bool:
    """كشف نص عربي تالف محفوظ سابقاً (presentation forms / escapes)."""
    if not text:
        return False
    if _ESCAPED_UNICODE_RE.search(text) or _HEX_DUMPISH_RE.search(text):
        return True
    # نص محفوظ بأشكال العرض فقط بدون حروف منطقية ⇒ غير صالح لـ Groq
    if _PRESENTATION_RE.search(text) and not _LOGICAL_ARABIC_RE.search(
        unicodedata.normalize("NFKC", text)
    ):
        return True
    if _PRESENTATION_RE.search(text):
        return True
    return False


class PDFExtractor:
    """مستخرج نص PDF باستخدام PyMuPDF مع إعادة تشكيل العربية للمعاينة."""

    @staticmethod
    def validate_pdf_file(file_obj, max_size_bytes: int) -> None:
        from apps.guest.exceptions import FileTooLargeError, InvalidFileTypeError

        name = getattr(file_obj, "name", "") or ""
        if not name.lower().endswith(".pdf"):
            raise InvalidFileTypeError()

        size = getattr(file_obj, "size", None)
        if size is None:
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(0)

        if size > max_size_bytes:
            raise FileTooLargeError(max_size_bytes // (1024 * 1024))

        if size == 0:
            raise InvalidFileTypeError()

        header = file_obj.read(5)
        file_obj.seek(0)
        if not header.startswith(b"%PDF"):
            raise InvalidFileTypeError()

    @classmethod
    def extract_text(cls, file_path: str | None = None, file_obj=None) -> dict:
        from apps.guest.exceptions import PDFExtractionError

        if not file_path and not file_obj:
            raise PDFExtractionError("لم يُحدد ملف للمعالجة.")

        try:
            result = cls._extract_with_pymupdf(file_path, file_obj)
        except Exception as exc:
            logger.exception("فشل استخراج PDF عبر PyMuPDF")
            raise PDFExtractionError(f"تعذّر استخراج النص: {exc}") from exc

        # مسار المستخدم المطلق: reshape + get_display ثم UTF-8
        pipeline_text = result.get("text") or ""
        reshaped_all = reshape_arabic_for_display(pipeline_text)
        # النص المحفوظ لـ AI: منطقي UTF-8 (NFKC) حتى يفهمه Groq
        extracted_text = to_ai_utf8(pipeline_text)

        # تحقق بصري في سجلات الخادم (نسخة مقروءة متصلة الحروف)
        preview = (reshaped_all or extracted_text)[:500]
        try:
            print(preview)
        except UnicodeEncodeError:
            print(preview.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

        logger.info(
            "PDF extraction preview (%s chars AI / %s display via %s):\n%s",
            len(extracted_text),
            len(reshaped_all),
            result.get("method", "pymupdf"),
            preview,
        )

        if not extracted_text.strip():
            raise PDFExtractionError("الملف لا يحتوي على نص قابل للاستخراج.")

        result["text"] = extracted_text
        result["display_text"] = reshaped_all
        result["method"] = "pymupdf+arabic_reshaper+bidi+utf8"
        return result

    @classmethod
    def _open_document(cls, file_path: str | None, file_obj) -> fitz.Document:
        if file_path:
            return fitz.open(file_path)
        file_obj.seek(0)
        data = file_obj.read()
        file_obj.seek(0)
        if isinstance(data, str):
            data = data.encode("utf-8", errors="replace")
        return fitz.open(stream=data, filetype="pdf")

    @classmethod
    def _extract_page_text(cls, page: fitz.Page) -> str:
        """استخراج نص الصفحة عبر get_text('text') مع مسار احتياطي للكتل."""
        # 1) المطلوب صراحةً
        page_text = page.get_text("text") or ""
        page_text = as_clean_utf8(page_text)

        # 2) إن كان الناتج ضعيفاً، ابنِ النص من الكتل حسب ترتيب القراءة
        if len(page_text.strip()) < 20:
            blocks = page.get_text("blocks") or []
            # blocks: (x0, y0, x1, y1, text, block_no, block_type)
            text_blocks = [
                b for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()
            ]
            text_blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
            joined = "\n".join(as_clean_utf8(b[4]).strip() for b in text_blocks)
            if len(joined.strip()) > len(page_text.strip()):
                page_text = joined

        # مرّر كل سطر عبر مسار إعادة التشكيل المطلوب، واحفظ النسخة المنطقية لـ Groq
        fixed_lines: list[str] = []
        for line in page_text.splitlines():
            raw_line = as_clean_utf8(line)
            if not raw_line.strip():
                fixed_lines.append("")
                continue
            # absolute path: reshape → get_display (للتحقق)، ثم نص AI منطقي
            reshape_arabic_for_display(raw_line)
            fixed_lines.append(to_ai_utf8(raw_line))

        return "\n".join(fixed_lines)

    @classmethod
    def _extract_with_pymupdf(cls, file_path: str | None, file_obj) -> dict:
        text_parts: list[str] = []
        truncated = False
        total_pages = 0
        pages_to_process = 0

        doc = cls._open_document(file_path, file_obj)
        try:
            total_pages = doc.page_count
            pages_to_process = min(total_pages, MAX_PAGES)
            truncated = total_pages > MAX_PAGES

            for page_index in range(pages_to_process):
                page = doc.load_page(page_index)
                page_text = cls._extract_page_text(page)
                if page_text.strip():
                    text_parts.append(page_text.strip())
        finally:
            doc.close()

        full_text = to_ai_utf8("\n\n".join(text_parts))
        if len(full_text) > MAX_EXTRACTED_CHARS:
            full_text = full_text[:MAX_EXTRACTED_CHARS]
            truncated = True

        return {
            "text": full_text,
            "page_count": pages_to_process,
            "total_pages": total_pages,
            "method": "pymupdf+arabic_reshaper+bidi",
            "truncated": truncated,
        }
