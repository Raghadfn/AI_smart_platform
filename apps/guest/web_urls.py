from django.urls import path

from .views import guest_upload_view
from .web_views import GuestWorkspaceView

app_name = "guest_web"

urlpatterns = [
    path("guest/", guest_upload_view, name="upload"),
    path("guest/<uuid:upload_id>/", GuestWorkspaceView.as_view(), name="workspace"),
]
