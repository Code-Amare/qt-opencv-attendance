from django.urls import path, include
from .views import TestView, SiteSettingsView

urlpatterns = [
    path("test/", TestView.as_view()),
    path("users/", include("users.urls")),
    path("attendance/", include("attendance.urls")),
    path("admin/", include("console.urls")),
    path("site/", SiteSettingsView.as_view()),
]
