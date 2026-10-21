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
)

urlpatterns = [
    path("stats/", TenantStatsView.as_view()),
    path("users/", MemberListCreateView.as_view()),
    path("users/<int:user_id>/", MemberDetailView.as_view()),
    path("users-table/", MemberTableView.as_view()),
    path("sessions/<int:session_id>/", SessionManageView.as_view()),
    path("sessions/<int:session_id>/status/", SessionStateView.as_view()),
    path("sessions/<int:session_id>/report/", SessionReportView.as_view()),
    path("attendance/override/", AttendanceOverrideView.as_view()),
]
