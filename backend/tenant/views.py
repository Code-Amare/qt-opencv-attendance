import io
from xml.sax.saxutils import escape

from cloudinary.exceptions import Error as CloudinaryError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import status
from rest_framework.response import Response

from attendance.models import Attendance, AttendanceSession
from attendance.serializers import AttendanceSerializer, AttendanceSessionSerializer
from users.serializers import AdminUserUpdateSerializer, UserSerializer
from utils.base import TenantAdminView

User = get_user_model()
Session = AttendanceSession

MAX_PICTURE_SIZE = 5 * 1024 * 1024

# Only these can be set from a request. tenant, is_tenant_admin and is_staff never can.
EDITABLE_FIELDS = [
    "first_name",
    "last_name",
    "section",
    "phone_number",
    "date_of_birth",
    "gender",
]

STATUS_COLORS = {
    "present": colors.HexColor("#047857"),
    "late": colors.HexColor("#B45309"),
    "absent": colors.HexColor("#B91C1C"),
    "not set": colors.HexColor("#6B7280"),
}


# ---------------------------------------------------------------- helpers


def error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def fmt_dt(value):
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M") if value else "-"


class TenantBase(TenantAdminView):
    def sessions(self):
        return Session.objects.filter(tenant=self.tenant)

    def get_session(self, session_id):
        return self.sessions().filter(id=session_id).first()

    def all_members(self):
        # tenant admins manage the tenant, they aren't part of the roster
        return User.objects.filter(tenant=self.tenant, is_tenant_admin=False)

    def active_members(self):
        return self.all_members().filter(is_active=True)


# ---------------------------------------------------------------- dashboard


class TenantStatsView(TenantBase):
    def get(self, request):
        members = self.all_members()

        by_status = (
            Attendance.objects.filter(
                session__tenant=self.tenant, user__is_tenant_admin=False
            )
            .values("status")
            .annotate(count=Count("id"))
        )

        def count(state):
            return Count(
                "attendances",
                filter=Q(
                    attendances__status=state,
                    attendances__user__is_tenant_admin=False,
                ),
            )

        recent = (
            self.sessions()
            .annotate(present=count("present"), late=count("late"), absent=count("absent"))
            .order_by("-started_at")[:7]
            .values("id", "name", "started_at", "status", "present", "late", "absent")
        )

        return Response(
            {
                "tenant": {"id": self.tenant.id, "name": self.tenant.name},
                "total_users": members.count(),
                "active_users": members.filter(is_active=True).count(),
                "users_with_face": members.exclude(face_embeddings__isnull=True).count(),
                "total_sessions": self.sessions().count(),
                "attendance_by_status": {i["status"]: i["count"] for i in by_status},
                "recent_sessions": list(recent),  # newest first
            }
        )


# ---------------------------------------------------------------- members


class MemberListCreateView(TenantBase):
    def get(self, request):
        users = self.all_members().order_by("id")

        search = request.query_params.get("search", "").strip()
        if search:
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        section = request.query_params.get("section")
        if section:
            users = users.filter(section=section)

        return Response({"users": UserSerializer(users, many=True).data})

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        username = str(request.data.get("username") or email).strip()

        if not email or not password:
            return error("email and password are required")

        try:
            validate_email(email)
            validate_password(password)
        except ValidationError as e:
            return error(" ".join(e.messages))

        if User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=username)
        ).exists():
            return error("A user with this email or username already exists")

        picture = request.FILES.get("profile_picture")
        if picture and (problem := invalid_picture(picture)):
            return error(problem)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    tenant=self.tenant,  # forced, never taken from the request
                )
                for field in EDITABLE_FIELDS:
                    if field in request.data:
                        value = request.data[field]
                        if field == "date_of_birth" and value == "":
                            value = None
                        setattr(user, field, value)
                if picture:
                    user.profile_picture = picture  # CloudinaryField uploads on save
                user.save()
        except CloudinaryError as e:
            return error(f"Image upload failed: {e}", status.HTTP_502_BAD_GATEWAY)

        return Response(
            {"detail": "User created", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class MemberDetailView(TenantBase):
    def get_member(self, user_id, allow_self=False):
        # an admin can open and edit their own profile, but nobody else's admin row
        if allow_self and user_id == self.request.user.id:
            return User.objects.filter(id=user_id, tenant=self.tenant).first()
        return self.all_members().filter(id=user_id).first()

    def get(self, request, user_id):
        user = self.get_member(user_id, allow_self=True)
        if not user:
            return error("User not found", status.HTTP_404_NOT_FOUND)

        attendances = Attendance.objects.filter(
            user=user, session__tenant=self.tenant
        ).select_related("session")

        return Response(
            {
                "user": UserSerializer(user).data,
                "has_face": user.has_face,
                "embeddings_updated_at": user.embeddings_updated_at,
                "attendances": AttendanceSerializer(attendances, many=True).data,
            }
        )

    def patch(self, request, user_id):
        user = self.get_member(user_id, allow_self=True)
        if not user:
            return error("User not found", status.HTTP_404_NOT_FOUND)

        email = str(request.data.get("email", "")).strip()
        if email and User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
            return error("A user with this email already exists")

        if user.id == request.user.id and str(request.data.get("is_active", "")).lower() in (
            "false",
            "0",
        ):
            return error("You can't deactivate your own account")

        picture = request.FILES.get("profile_picture")
        if picture and (problem := invalid_picture(picture)):
            return error(problem)

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error(first_error(serializer.errors))

        if picture:
            user.profile_picture = picture

        try:
            serializer.save()
        except CloudinaryError as e:
            return error(f"Image upload failed: {e}", status.HTTP_502_BAD_GATEWAY)

        return Response({"detail": "User updated", "user": UserSerializer(user).data})

    def delete(self, request, user_id):
        user = self.get_member(user_id)  # not allow_self: no deleting your own account
        if not user:
            return error("User not found", status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response({"detail": "User deleted"})


class MemberTableView(TenantBase):
    def get(self, request):
        users = []
        for user in self.all_members().order_by("id"):
            try:
                picture = user.profile_picture.url
            except (ValueError, AttributeError):
                picture = None

            users.append(
                {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "face_embeddings": user.has_face,
                    "profile_picture": picture,
                }
            )

        return Response({"users": users})


# ---------------------------------------------------------------- sessions


class SessionManageView(TenantBase):
    def patch(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return error("Session not found", status.HTTP_404_NOT_FOUND)

        serializer = AttendanceSessionSerializer(session, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({"detail": "Session updated", "session": serializer.data})

    def delete(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return error("Session not found", status.HTTP_404_NOT_FOUND)

        session.delete()  # cascades its attendance records
        return Response({"detail": "Session deleted"})


class SessionStateView(TenantBase):
    """PATCH {"status": "active" | "completed" | "cancelled"}"""

    def patch(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return error("Session not found", status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status", "")
        if new_status not in Session.Status.values:
            return error(f"status must be one of {list(Session.Status.values)}")

        marked_absent = 0
        with transaction.atomic():
            session.status = new_status
            session.save(update_fields=["status"])

            # Completing a session: everyone with no record becomes Absent
            if new_status == Session.Status.COMPLETED:
                recorded = session.attendances.values_list("user_id", flat=True)
                missing = list(self.active_members().exclude(id__in=recorded))
                Attendance.objects.bulk_create(
                    [
                        Attendance(session=session, user=user, status=Attendance.Status.ABSENT)
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
            }
        )


class AttendanceOverrideView(TenantBase):
    """PUT {"user_id", "session_id", "status"}: set or correct one person's status."""

    def put(self, request):
        user_id = as_int(request.data.get("user_id"))
        session_id = as_int(request.data.get("session_id"))
        new_status = request.data.get("status", "")

        if user_id is None or session_id is None or not new_status:
            return error("user_id, session_id and status are required")

        if new_status not in Attendance.Status.values:
            return error(f"status must be one of {list(Attendance.Status.values)}")

        user = self.all_members().filter(id=user_id).first()
        session = self.get_session(session_id)
        if not user or not session:
            return error("Invalid user_id or session_id")

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


# ---------------------------------------------------------------- report


class SessionReportView(TenantBase):
    def get(self, request, session_id):
        session = self.get_session(session_id)
        if not session:
            return error("Session not found", status.HTTP_404_NOT_FOUND)

        records = {r.user_id: r for r in session.attendances.all()}
        users = self.active_members().order_by("first_name", "last_name", "id")

        counts = {"present": 0, "late": 0, "absent": 0, "not set": 0}
        rows = [["#", "Name", "Email", "Status", "Recorded at"]]
        row_colors = []

        for i, user in enumerate(users, start=1):
            record = records.get(user.id)
            state = record.status if record else "not set"
            counts[state] += 1
            rows.append(
                [
                    str(i),
                    f"{user.first_name} {user.last_name}".strip() or "-",
                    user.email or "-",
                    state.title(),
                    fmt_dt(record.recorded_at) if record else "-",
                ]
            )
            row_colors.append(("TEXTCOLOR", (3, i), (3, i), STATUS_COLORS[state]))

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
            Paragraph(f"Attendance report · {escape(self.tenant.name)}", styles["Heading3"]),
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