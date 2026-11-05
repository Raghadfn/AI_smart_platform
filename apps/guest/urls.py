from django.urls import path

from .views import (
    GuestAskAPIView,
    GuestSummarizeAPIView,
    GuestUploadAPIView,
    GuestUploadStatusAPIView,
)

app_name = "guest"

urlpatterns = [
    path("guest/upload/", GuestUploadAPIView.as_view(), name="api_upload"),
    path("guest/upload/<uuid:upload_id>/status/", GuestUploadStatusAPIView.as_view(), name="api_status"),
    path("guest/upload/<uuid:upload_id>/summarize/", GuestSummarizeAPIView.as_view(), name="api_summarize"),
    path("guest/upload/<uuid:upload_id>/ask/", GuestAskAPIView.as_view(), name="api_ask"),
]
