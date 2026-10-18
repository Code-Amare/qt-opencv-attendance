from django.urls import path
from .views import (
    AdminAttendanceOverrideView,
    AdminSessionDetailView,
    AdminSessionListView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
    AdminSessionStateView,
    AdminSessionReportView,
    UserTableDataView,
)

urlpatterns = [
    path("stats/", AdminStatsView.as_view()),
    path("users/", AdminUserListView.as_view()),
    path("users/gui-table/", UserTableDataView.as_view()),
    path("users/<int:user_id>/", AdminUserDetailView.as_view()),
    path("sessions/", AdminSessionListView.as_view()),
    path("sessions/<int:session_id>/", AdminSessionDetailView.as_view()),
    path("attendance/override/", AdminAttendanceOverrideView.as_view()),
    path("sessions/<int:session_id>/state/", AdminSessionStateView.as_view()),
    path("sessions/<int:session_id>/report/", AdminSessionReportView.as_view()),
]
