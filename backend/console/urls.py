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
    path("admin/stats/", AdminStatsView.as_view()),
    path("admin/users/", AdminUserListView.as_view()),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view()),
    path("admin/users/<int:user_id>/reset-face/", AdminUserResetFaceView.as_view()),
    path("admin/sessions/", AdminSessionListView.as_view()),
    path("admin/sessions/<int:session_id>/", AdminSessionDetailView.as_view()),
    path("admin/attendance/override/", AdminAttendanceOverrideView.as_view()),
]
