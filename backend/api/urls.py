from django.urls import path, include
from .views import (
    TestView,
    SiteSettingsView,
    AssetDetailView,
    AssetListCreateView,
    LatestDownloadView,
    LatestReleaseView,
    ReleaseDetailView,
    ReleaseListCreateView,
    ReleasePublishView,
)

urlpatterns = [
    path("test/", TestView.as_view()),
    path("users/", include("users.urls")),
    path("attendance/", include("attendance.urls")),
    path("admin/", include("console.urls")),
    path("site/", SiteSettingsView.as_view()),
    path("releases/latest/", LatestReleaseView.as_view()),
    path("releases/latest/download/", LatestDownloadView.as_view()),
    # admin (dashboard)
    path("admin/releases/", ReleaseListCreateView.as_view()),
    path("admin/releases/<int:pk>/", ReleaseDetailView.as_view()),
    path("admin/releases/<int:pk>/publish/", ReleasePublishView.as_view(publish=True)),
    path(
        "admin/releases/<int:pk>/unpublish/", ReleasePublishView.as_view(publish=False)
    ),
    path("admin/release-assets/", AssetListCreateView.as_view()),
    path("admin/release-assets/<int:pk>/", AssetDetailView.as_view()),
]
