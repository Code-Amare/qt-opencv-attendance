from django.urls import path, include
from .views import TestView

urlpatterns = [
    path("test/", TestView.as_view()),
    path("users/", include("users.urls")),
    path("attendance/", include("attendance.urls")),
]
