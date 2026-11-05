"""
مسارات صفحات المحاضرات
Lecture web routes
"""
from django.urls import path

from .web_views import LectureDetailView, LecturePDFEmbedView

app_name = "lectures_web"

urlpatterns = [
    # مسار بسيط وموثوق بالمعرّف — يُستخدم من قوائم المواد
    path(
        "lecture/<uuid:lecture_id>/",
        LectureDetailView.as_view(),
        name="detail_by_id",
    ),
    # مسار PDF المضمّن (Content-Disposition: inline)
    path(
        "lecture/<uuid:lecture_id>/pdf/",
        LecturePDFEmbedView.as_view(),
        name="pdf_embed",
    ),
    # المسار الهرمي (للتوافق مع الروابط القديمة)
    path(
        "year/<slug:year_slug>/subject/<slug:subject_slug>/lecture/<slug:lecture_slug>/",
        LectureDetailView.as_view(),
        name="detail",
    ),
]
