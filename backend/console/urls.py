from django.urls import path

from .views import (
    ConsoleStatsView,
    TenantAdminCreateView,
    TenantDetailView,
    TenantListCreateView,
    ReleaseDetailView,
    ReleaseListCreateView,
    ReleasePublishView,
    AssetDetailView,
    AssetListCreateView,
)

urlpatterns = [
    path("stats/", ConsoleStatsView.as_view()),
    path("tenants/", TenantListCreateView.as_view()),
    path("tenants/<int:tenant_id>/", TenantDetailView.as_view()),
    path("tenants/<int:tenant_id>/admins/", TenantAdminCreateView.as_view()),
    path("releases/", ReleaseListCreateView.as_view()),
    path("releases/<int:pk>/", ReleaseDetailView.as_view()),
    path("releases/<int:pk>/publish/", ReleasePublishView.as_view(publish=True)),
    path("releases/<int:pk>/unpublish/", ReleasePublishView.as_view(publish=False)),
    path("release-assets/", AssetListCreateView.as_view()),
    path("release-assets/<int:pk>/", AssetDetailView.as_view()),
]
