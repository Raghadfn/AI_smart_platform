"""
مسارات صفحات المنهج الدراسي
Curriculum web routes
"""
from django.urls import path

from .web_views import SearchView, SubjectLecturesView, YearSubjectsView

app_name = "curriculum_web"

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("year/<slug:year_slug>/", YearSubjectsView.as_view(), name="year"),
    path(
        "year/<slug:year_slug>/subject/<slug:subject_slug>/",
        SubjectLecturesView.as_view(),
        name="subject",
    ),
]
