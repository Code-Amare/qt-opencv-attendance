from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.utils import timezone

from attendance.models import Attendance, AttendanceSession
from attendance.serializers import AttendanceSerializer, AttendanceSessionSerializer
from users.serializers import UserSerializer

User = get_user_model()

USER_EDITABLE_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "section",
    "phone_number",
    "date_of_birth",
    "is_active",
]


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = User.objects.filter(is_staff=False)
        by_status = Attendance.objects.values("status").annotate(count=Count("id"))

        return Response(
            {
                "total_users": students.count(),
                "active_users": students.filter(is_active=True).count(),
                "users_with_face": students.exclude(
                    face_embeddings__isnull=True
                ).count(),
                "total_sessions": AttendanceSession.objects.count(),
                "attendance_by_status": {i["status"]: i["count"] for i in by_status},
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.exclude(is_staff=True).order_by("id")

        search = request.query_params.get("search")
        if search:
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        section = request.query_params.get("section")
        if section:
            users = users.filter(section=section)

        if not users.exists():
            return Response(
                {"error": "No user found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"users": UserSerializer(users, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        username = request.data.get("username") or email

        if not email or not password:
            return Response(
                {"error": "email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "A user with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        for field in USER_EDITABLE_FIELDS:
            if field in request.data and field != "email":
                setattr(user, field, request.data[field])
        user.save()

        return Response(
            {"detail": "User created", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_user(self, user_id):
        return User.objects.filter(id=user_id, is_staff=False).first()

    def get(self, request, user_id):
        user = self.get_user(user_id)
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        attendances = Attendance.objects.filter(user=user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "has_face": user.has_face,
                "embeddings_updated_at": user.embeddings_updated_at,
                "attendances": AttendanceSerializer(attendances, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, user_id):
        user = self.get_user(user_id)
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        email = request.data.get("email")
        if email and User.objects.filter(email=email).exclude(id=user.id).exists():
            return Response(
                {"error": "A user with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field in USER_EDITABLE_FIELDS:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()

        return Response(
            {"detail": "User updated", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, user_id):
        user = self.get_user(user_id)
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.delete()
        return Response({"detail": "User deleted"}, status=status.HTTP_200_OK)


class AdminUserResetFaceView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id, is_staff=False).first()
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not user.has_face:
            return Response(
                {"error": "User has no face data"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.face_embeddings = None
        user.embeddings_updated_at = None
        user.save(update_fields=["face_embeddings", "embeddings_updated_at"])

        return Response({"detail": "Face data reset"}, status=status.HTTP_200_OK)


class AdminSessionListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        sessions = AttendanceSession.objects.all().order_by("-id")
        if not sessions.exists():
            return Response(
                {"error": "No session found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"sessions": AttendanceSessionSerializer(sessions, many=True).data},
            status=status.HTTP_200_OK,
        )


class AdminSessionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, session_id):
        session = AttendanceSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = AttendanceSessionSerializer(
            session, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {"detail": "Session updated", "session": serializer.data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, session_id):
        session = AttendanceSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        session.delete()
        return Response({"detail": "Session deleted"}, status=status.HTTP_200_OK)


class AdminAttendanceOverrideView(APIView):
    """Manually set a user's attendance status for a session."""

    permission_classes = [IsAdminUser]

    def put(self, request):
        user_id = request.data.get("user_id", "")
        session_id = request.data.get("session_id", "")
        new_status = request.data.get("status", "")

        if not user_id or not session_id or not new_status:
            return Response(
                {"error": "user_id, session_id and status are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in Attendance.Status.values:
            return Response(
                {"error": f"status must be one of {list(Attendance.Status.values)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=user_id).first()
        session = AttendanceSession.objects.filter(id=session_id).first()
        if not user or not session:
            return Response(
                {"error": "Invalid user_id or session_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attendance, created = Attendance.objects.update_or_create(
            user=user, session=session, defaults={"status": new_status}
        )

        return Response(
            {
                "detail": "Attendance created" if created else "Attendance updated",
                "attendance": AttendanceSerializer(attendance).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
