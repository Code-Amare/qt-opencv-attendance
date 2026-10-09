from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Attendance, AttendanceSession
from .serializers import AttendanceSerializer, AttendanceSessionSerializer
from users.serializers import UserSerializer

User = get_user_model()


class EvaluateAttendanceView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id", "")
        session_id = request.data.get("session_id", "")

        if not user_id or not session_id:
            return Response(
                {"error": "user_id and session_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "Invalid user_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        session = AttendanceSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Invalid session_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        if now <= session.ended_at:
            attendance_status = Attendance.Status.PRESENT
        elif now <= session.ended_at + session.late_time:
            attendance_status = Attendance.Status.LATE
        else:
            attendance_status = Attendance.Status.ABSENT

        attendance, created = Attendance.objects.get_or_create(
            user=user,
            session=session,
            defaults={
                "status": attendance_status,
            },
        )

        if not created:
            return Response(
                {
                    "attendance": AttendanceSerializer(attendance).data,
                    "is_attendance_taken_before": True,
                },
                status=status.HTTP_200_OK,
            )

        print(attendance)

        return Response(
            {
                "attendance": AttendanceSerializer(attendance).data,
                "is_attendance_taken_before": False,
            },
            status=status.HTTP_201_CREATED,
        )


class CreateSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AttendanceSessionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = serializer.save(
            created_by=request.user,
            status=AttendanceSession.Status.ACTIVE,
        )

        return Response(
            AttendanceSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class UserAttendanceDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "Invalid user_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        attendances = user.attendances
        return Response(
            {
                "user": UserSerializer(user).data,
                "attendances": AttendanceSerializer(attendances, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AttendanceListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = AttendanceSession.objects.filter(id=session_id).first()

        if not session:
            return  Response({"error": "Invalid session_id"}, status=status.HTTP_200_OK)

        existing = {
            record.user_id: record
            for record in Attendance.objects.filter(
                session=session
            )
        }

        users = User.objects.filter(is_active=True).order_by(
            "id"
        )

        attendance_list = []

        for user in users:
            record = existing.get(user.id)

            if record:
                attendance_status = record.status
            else:
                attendance_status = Attendance.Status.ABSENT

            attendance_list.append({
                "user_id": user.id,
                "first_name": user.first_name,
                "status": attendance_status,
            })

        return Response({
            "session_id": session.id,
            "session_name": session.name,
            "session_status": session.status,
            "finalized": session.is_ended,
            "total_users": len(attendance_list),
            "attendance": attendance_list,
        })