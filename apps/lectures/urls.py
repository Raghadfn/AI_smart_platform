from django.urls import path

from .views import LectureDetailAPIView, LectureSearchAPIView, SubjectLecturesAPIView

app_name = "lectures"

urlpatterns = [
    path("lectures/search/", LectureSearchAPIView.as_view(), name="search"),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/",
        SubjectLecturesAPIView.as_view(),
        name="subject_lectures",
    ),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/",
        LectureDetailAPIView.as_view(),
        name="detail",
    ),
]
