from django.urls import path

from .views import (
    AttendanceListView,
    EvaluateAttendanceView,
    SessionDetailView,
    SessionListCreateView,
    SessionStatusView,
    UserAttendanceDetailView,
    UserAttendanceHistoryView,
)

urlpatterns = [
    path("sessions/", SessionListCreateView.as_view()),
    path("sessions/<int:session_id>/", SessionDetailView.as_view()),
    path("sessions/<int:session_id>/status/", SessionStatusView.as_view()),
    path("sessions/<int:session_id>/attendance/", AttendanceListView.as_view()),
    path("evaluate/", EvaluateAttendanceView.as_view()),
    path("users/<int:user_id>/", UserAttendanceDetailView.as_view()),
    path("users/<int:user_id>/history/", UserAttendanceHistoryView.as_view()),
]
