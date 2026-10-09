from django.urls import path
from .views import (
    EvaluateAttendanceView,
    CreateSessionView,
    AttendanceListView,
    UserAttendanceDetailView,
)

urlpatterns = [
    path("", EvaluateAttendanceView.as_view()),
    path("session/create/", CreateSessionView.as_view()),
    path("sessions/<int:session_id>/", AttendanceListView.as_view()),
    path("<int:user_id>/", UserAttendanceDetailView.as_view()),
]
