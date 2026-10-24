from django.urls import path

from .views import (
    AttendanceOverrideView,
    MemberDetailView,
    MemberListCreateView,
    MemberTableView,
    SessionManageView,
    SessionReportView,
    SessionStateView,
    TenantStatsView,
    MemberBulkCreateView,
    AddFaceEmbeddingView,
    DownloadFaceEmbeddingsView,
)

urlpatterns = [
    path("stats/", TenantStatsView.as_view()),
    path("users/", MemberListCreateView.as_view()),
    path("users/bulk/", MemberBulkCreateView.as_view()),
    path("users/<int:user_id>/", MemberDetailView.as_view()),
    path("users-table/", MemberTableView.as_view()),
    path("sessions/<int:session_id>/", SessionManageView.as_view()),
    path("sessions/<int:session_id>/status/", SessionStateView.as_view()),
    path("sessions/<int:session_id>/report/", SessionReportView.as_view()),
    path("attendance/override/", AttendanceOverrideView.as_view()),
    path("face-embedding/add/<int:user_id>/", AddFaceEmbeddingView.as_view()),
    path("face-embedding/download/", DownloadFaceEmbeddingsView.as_view()),
]
