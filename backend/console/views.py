import io
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.utils import timezone
from xml.sax.saxutils import escape
from attendance.models import Attendance, AttendanceSession
from attendance.serializers import AttendanceSerializer, AttendanceSessionSerializer
from users.serializers import UserSerializer, AdminUserUpdateSerializer
from django.db import transaction
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from cloudinary.exceptions import Error as CloudinaryError

MAX_PICTURE_SIZE = 5 * 1024 * 1024


def first_error(errors):
    field, messages = next(iter(errors.items()))
    message = messages[0] if isinstance(messages, (list, tuple)) else messages
    return f"{field}: {message}"


def invalid_picture(file):
    if not (file.content_type or "").startswith("image/"):
        return "profile_picture: the file must be an image"
    if file.size > MAX_PICTURE_SIZE:
        return "profile_picture: the image must be 5 MB or smaller"
    return None


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

STATUS_COLORS = {
    "present": colors.HexColor("#047857"),
    "late": colors.HexColor("#B45309"),
    "absent": colors.HexColor("#B91C1C"),
    "not set": colors.HexColor("#6B7280"),
}


def fmt_dt(value):
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M") if value else "-"


class AdminSessionReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, session_id):
        session = AttendanceSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        records = {r.user_id: r for r in Attendance.objects.filter(session=session)}
        users = User.objects.filter(is_staff=False, is_active=True).order_by(
            "first_name", "last_name", "id"
        )

        counts = {"present": 0, "late": 0, "absent": 0, "not set": 0}
        rows = [["#", "Name", "Email", "Status", "Recorded at"]]
        row_colors = []

        for i, user in enumerate(users, start=1):
            record = records.get(user.id)
            state = record.status if record else "not set"
            counts[state] += 1
            name = f"{user.first_name} {user.last_name}".strip() or "-"
            rows.append(
                [
                    str(i),
                    name,
                    user.email or "-",
                    state.title(),
                    fmt_dt(record.recorded_at) if record else "-",
                ]
            )
            row_colors.append(("TEXTCOLOR", (3, i), (3, i), STATUS_COLORS[state]))

        # ---- build the PDF ----
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=f"{session.name} - Attendance report",
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph(escape(session.name), styles["Title"]),
            Paragraph("Attendance report", styles["Heading3"]),
            Spacer(1, 4 * mm),
        ]

        late_minutes = int(session.late_time.total_seconds() // 60)
        info = [
            ["Status", session.status.title()],
            ["Starts", fmt_dt(session.started_at)],
            ["Ends", fmt_dt(session.ended_at)],
            ["Late window", f"{late_minutes} min"],
            [
                "Summary",
                f"Present {counts['present']} | Late {counts['late']} | "
                f"Absent {counts['absent']} | Not set {counts['not set']}",
            ],
            ["Generated", fmt_dt(timezone.now())],
        ]
        info_table = Table(info, colWidths=[30 * mm, 150 * mm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story += [info_table, Spacer(1, 8 * mm)]

        if len(rows) == 1:
            story.append(Paragraph("No students found.", styles["Normal"]))
        else:
            table = Table(
                rows,
                colWidths=[10 * mm, 52 * mm, 60 * mm, 25 * mm, 33 * mm],
                repeatRows=1,  # header repeats on every page
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5B21B6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F3F4F6")],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        *row_colors,
                    ]
                )
            )
            story.append(table)

        doc.build(story)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="session-{session.id}-report.pdf"'
        )
        return response


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = User.objects.filter(is_staff=False)
        by_status = (
            Attendance.objects.filter(user__is_staff=False)
            .values("status")
            .annotate(count=Count("id"))
        )

        def count(state):
            return Count(
                "attendances",
                filter=Q(
                    attendances__status=state,
                    attendances__user__is_staff=False,
                ),
            )

        recent = (
            AttendanceSession.objects.annotate(
                present=count("present"),
                late=count("late"),
                absent=count("absent"),
            )
            .order_by("-started_at")[:7]
            .values("id", "name", "started_at", "status", "present", "late", "absent")
        )

        return Response(
            {
                "total_users": students.count(),
                "active_users": students.filter(is_active=True).count(),
                "users_with_face": students.exclude(
                    face_embeddings__isnull=True
                ).count(),
                "total_sessions": AttendanceSession.objects.count(),
                "attendance_by_status": {i["status"]: i["count"] for i in by_status},
                "recent_sessions": list(recent),  # newest first
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
            if field in request.data and field not in ("email", "profile_picture"):
                setattr(user, field, request.data[field])

        picture = request.FILES.get("profile_picture")
        if picture:
            user.profile_picture = picture  # CloudinaryField uploads it on save

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

        picture = request.FILES.get("profile_picture")
        if picture:
            error = invalid_picture(picture)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"error": first_error(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if picture:
            user.profile_picture = picture

        try:
            serializer.save()
        except CloudinaryError as e:
            return Response(
                {"error": f"Image upload failed: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

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


class AdminSessionStateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, session_id):
        session = AttendanceSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get("status", "")
        if not new_status:
            return Response(
                {"error": "status is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in AttendanceSession.Status.values:
            return Response(
                {
                    "error": f"status must be one of {list(AttendanceSession.Status.values)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        marked_absent = 0
        with transaction.atomic():
            session.status = new_status
            session.save(update_fields=["status"])

            # Completing a session: everyone with no record becomes Absent
            if new_status == AttendanceSession.Status.COMPLETED:
                recorded = Attendance.objects.filter(session=session).values_list(
                    "user_id", flat=True
                )
                missing = list(
                    User.objects.filter(is_staff=False, is_active=True).exclude(
                        id__in=recorded
                    )
                )
                Attendance.objects.bulk_create(
                    [
                        Attendance(
                            session=session,
                            user=user,
                            status=Attendance.Status.ABSENT,
                        )
                        for user in missing
                    ],
                    ignore_conflicts=True,
                )
                marked_absent = len(missing)

        return Response(
            {
                "detail": "Session state updated",
                "marked_absent": marked_absent,
                "session": AttendanceSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )


class UserTableDataView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(is_staff=False).order_by("id")
        if not users:
            return Response(
                {"error": "No users found"}, status=status.HTTP_400_BAD_REQUEST
            )

        users_data = []

        for user in users:
            try:
                profile_picture_url = user.profile_picture.url
            except (ValueError, AttributeError):
                profile_picture_url = None

            users_data.append(
                {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "face_embeddings": user.has_face,
                    "profile_picture": profile_picture_url,
                }
            )

        return Response({"users": users_data})
