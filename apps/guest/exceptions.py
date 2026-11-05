"""
استثناءات وضع الزائر
Guest mode exceptions
"""


class GuestUploadError(Exception):
    """خطأ في رفع ملف الزائر"""

    def __init__(self, message: str, code: str = "upload_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class PDFExtractionError(GuestUploadError):
    def __init__(self, message: str = "فشل استخراج النص من ملف PDF."):
        super().__init__(message, code="pdf_extraction_failed")


class FileTooLargeError(GuestUploadError):
    def __init__(self, max_mb: int):
        super().__init__(
            f"حجم الملف يتجاوز الحد المسموح ({max_mb} ميجابايت).",
            code="file_too_large",
        )


class InvalidFileTypeError(GuestUploadError):
    def __init__(self):
        super().__init__(
            "يُسمح برفع ملفات PDF فقط.",
            code="invalid_file_type",
        )
