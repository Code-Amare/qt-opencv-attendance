from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from utils.base import TenantAdminView
from users.serializers import UserSerializer

from .models import Attendance, AttendanceSession
from .serializers import AttendanceSerializer, AttendanceSessionSerializer

User = get_user_model()

Session = AttendanceSession
Present, Late, Absent = (
    Attendance.Status.PRESENT,
    Attendance.Status.LATE,
    Attendance.Status.ABSENT,
)


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def status_at(session, now):
    """Present until the session ends, late during the grace period, then absent."""
    if session.ended_at is None or now <= session.ended_at:
        return Present
    if now <= session.ended_at + session.late_time:
        return Late
    return Absent


def count_by_status(attendances):
    return attendances.aggregate(
        present=Count("id", filter=Q(status=Present)),
        late=Count("id", filter=Q(status=Late)),
        absent=Count("id", filter=Q(status=Absent)),
    )


class AttendanceBaseView(TenantAdminView):
    """Everything below only ever sees the requesting admin's own tenant."""

    def sessions(self):
        return Session.objects.filter(tenant=self.tenant)

    def get_session(self, session_id):
        return self.sessions().filter(id=session_id).first()

    def members(self):
        # tenant admins run attendance, they don't appear in it
        return User.objects.filter(
            tenant=self.tenant, is_tenant_admin=False, is_active=True
        )


# ------------------------------------------------------------- sessions


class SessionListCreateView(AttendanceBaseView):
    def get(self, request):
        sessions = self.sessions()

        wanted = request.query_params.get("status")
        if wanted in Session.Status.values:
            sessions = sessions.filter(status=wanted)

        return Response(
            {"sessions": AttendanceSessionSerializer(sessions, many=True).data}
        )

    def post(self, request):
        serializer = AttendanceSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session = serializer.save(
            tenant=self.tenant,
            created_by=request.user,
            status=Session.Status.ACTIVE,
        )
        return Response(
            AttendanceSessionSerializer(session).data, status=status.HTTP_201_CREATED
        )


class SessionDetailView(AttendanceBaseView):
    def get(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "session": AttendanceSessionSerializer(session).data,
                "summary": count_by_status(session.attendances),
            }
        )


class SessionStatusView(AttendanceBaseView):
    """POST {"action": "complete" | "cancel"}"""

    ACTIONS = {
        "complete": Session.Status.COMPLETED,
        "cancel": Session.Status.CANCELLED,
    }

    def post(self, request, session_id):
        new_status = self.ACTIONS.get(request.data.get("action"))
        if not new_status:
            return Response(
                {"error": "action must be 'complete' or 'cancel'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = self.get_session(session_id)
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if session.status != Session.Status.ACTIVE:
            return Response(
                {"error": f"Session is already {session.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        session.status = new_status
        if new_status == Session.Status.COMPLETED and (
            session.ended_at is None or session.ended_at > now
        ):
            session.ended_at = now
        session.save(update_fields=["status", "ended_at"])

        return Response(AttendanceSessionSerializer(session).data)


# ------------------------------------------------------------- attendance


class EvaluateAttendanceView(AttendanceBaseView):
    """Record a recognised person against a session."""

    def post(self, request):
        user_id = as_int(request.data.get("user_id"))
        session_id = as_int(request.data.get("session_id"))

        if user_id is None or session_id is None:
            return Response(
                {"error": "user_id and session_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = self.members().filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "Invalid user_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        session = self.get_session(session_id)
        if not session:
            return Response(
                {"error": "Invalid session_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        if session.status != Session.Status.ACTIVE:
            return Response(
                {
                    "error": f"Session is {session.status}, attendance cannot be recorded"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # get_or_create + the unique constraint make double scans safe
        with transaction.atomic():
            attendance, created = Attendance.objects.get_or_create(
                user=user,
                session=session,
                defaults={"status": status_at(session, timezone.now())},
            )

        return Response(
            {
                "attendance": AttendanceSerializer(attendance).data,
                "is_attendance_taken_before": not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AttendanceListView(AttendanceBaseView):
    """Every member of the tenant with their status for one session."""

    def get(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return Response(
                {"error": "Invalid session_id"}, status=status.HTTP_404_NOT_FOUND
            )

        recorded = dict(session.attendances.values_list("user_id", "status"))

        attendance = [
            {
                "user_id": user.id,
                "first_name": user.first_name,
                "status": recorded.get(user.id),  # None = not recorded yet
            }
            for user in self.members().order_by("id")
        ]

        return Response(
            {
                "session_id": session.id,
                "session_name": session.name,
                "session_status": session.status,
                "finalized": session.is_ended,
                "total_users": len(attendance),
                "attendance": attendance,
            }
        )


class UserAttendanceDetailView(AttendanceBaseView):
    def get(self, request, user_id):
        user = self.members().filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "Invalid user_id"}, status=status.HTTP_404_NOT_FOUND
            )

        attendances = user.attendances.filter(
            session__tenant=self.tenant
        ).select_related("session")

        return Response(
            {
                "user": UserSerializer(user).data,
                "attendances": AttendanceSerializer(attendances, many=True).data,
            }
        )
