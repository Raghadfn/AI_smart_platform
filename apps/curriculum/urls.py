from django.urls import path

from .views import SubjectDetailAPIView, YearDetailAPIView, YearListAPIView, YearSubjectsAPIView

app_name = "curriculum"

urlpatterns = [
    path("years/", YearListAPIView.as_view(), name="year_list"),
    path("years/<slug:slug>/", YearDetailAPIView.as_view(), name="year_detail"),
    path("years/<slug:slug>/subjects/", YearSubjectsAPIView.as_view(), name="year_subjects"),
    path(
        "subjects/<slug:year_slug>/<slug:subject_slug>/",
        SubjectDetailAPIView.as_view(),
        name="subject_detail",
    ),
]
