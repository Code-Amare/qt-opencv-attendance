from django.urls import path, include
from .views import (
    TestView,
    SiteSettingsView,
    LatestDownloadView,
    LatestReleaseView,
    HomeStatsView,
)

urlpatterns = [
    path("test/", TestView.as_view()),
    path("site/home/", HomeStatsView.as_view()),
    path("users/", include("users.urls")),
    path("attendance/", include("attendance.urls")),
    path("admin/", include("console.urls")),
    path("tenant/", include("tenant.urls")),
    path("console/", include("console.urls")),
    path("site/", SiteSettingsView.as_view()),
    path("releases/latest/", LatestReleaseView.as_view()),
    path("releases/latest/download/", LatestDownloadView.as_view()),
]
