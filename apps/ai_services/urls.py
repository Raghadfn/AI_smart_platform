from django.urls import path

from .views import (
    AskAPIView,
    ExamAttemptsListAPIView,
    GenerateExamAPIView,
    IllustrateAPIView,
    SavedResultDetailAPIView,
    SavedResultsListAPIView,
    SubmitExamAPIView,
    SummarizeAPIView,
    TranslateAPIView,
)

app_name = "ai_services"

urlpatterns = [
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/translate/",
        TranslateAPIView.as_view(),
        name="translate",
    ),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/summarize/",
        SummarizeAPIView.as_view(),
        name="summarize",
    ),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/ask/",
        AskAPIView.as_view(),
        name="ask",
    ),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/illustrate/",
        IllustrateAPIView.as_view(),
        name="illustrate",
    ),
    path(
        "years/<slug:year_slug>/subjects/<slug:subject_slug>/lectures/<slug:lecture_slug>/generate-exam/",
        GenerateExamAPIView.as_view(),
        name="generate_exam",
    ),
    path("saved-results/", SavedResultsListAPIView.as_view(), name="saved_results"),
    path("saved-results/<uuid:pk>/", SavedResultDetailAPIView.as_view(), name="saved_result_detail"),
    path("saved-results/<uuid:pk>/submit/", SubmitExamAPIView.as_view(), name="submit_exam"),
    path("exam-attempts/", ExamAttemptsListAPIView.as_view(), name="exam_attempts"),
]
