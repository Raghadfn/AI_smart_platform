from django.urls import path

from .views import SaveProgressAPIView

app_name = "progress"

urlpatterns = [
    path("progress/save/", SaveProgressAPIView.as_view(), name="save"),
]
