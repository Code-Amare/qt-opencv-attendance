from django.urls import path
from .views import (
    EvaluateAttendanceView,
    CreateSessionView,
    AttendanceListView,
    UserAttendanceDetailView,
    AdminDashboardView
)

urlpatterns = [
    path("", EvaluateAttendanceView.as_view()),
    path("session/create/", CreateSessionView.as_view()),
    path("session/<int:session_id>/", AttendanceListView.as_view()),
    path("<int:user_id>/", UserAttendanceDetailView.as_view()),
    path("data/", AdminDashboardView.as_view()),
]
