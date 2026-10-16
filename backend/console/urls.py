from django.urls import path
from .views import (
    AdminAttendanceOverrideView,
    AdminSessionDetailView,
    AdminSessionListView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserResetFaceView,
)

urlpatterns = [
    path("stats/", AdminStatsView.as_view()),
    path("users/", AdminUserListView.as_view()),
    path("users/<int:user_id>/", AdminUserDetailView.as_view()),
    path("users/<int:user_id>/reset-face/", AdminUserResetFaceView.as_view()),
    path("sessions/", AdminSessionListView.as_view()),
    path("sessions/<int:session_id>/", AdminSessionDetailView.as_view()),
    path("attendance/override/", AdminAttendanceOverrideView.as_view()),
]
