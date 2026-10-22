import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from .models import DesktopRelease, DesktopReleaseAsset
from attendance.models import AttendanceSession, Attendance
from users.models import Tenant
from users.models import ForgotPasswordRequest
from utils.emails import send_forgot_password_email

from .serializers import TenantSerializer, with_counts, DesktopReleaseAssetSerializer, DesktopReleaseSerializer

logger = logging.getLogger(__name__)

User = get_user_model()


def error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def unique_slug(value, exclude_pk=None):
    base = slugify(value) or "tenant"
    slug, n = base, 2
    while Tenant.objects.filter(slug=slug).exclude(pk=exclude_pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def check_admin_data(data):
    """Returns (cleaned, None) or (None, error message)."""
    if not isinstance(data, dict):
        return None, "admin details are required"

    email = str(data.get("email", "")).strip().lower()
    if not email:
        return None, "admin email is required"

    try:
        validate_email(email)
    except ValidationError:
        return None, "Enter a valid admin email address"

    if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
        return None, "A user with this email already exists"

    return {
        "email": email,
        "first_name": str(data.get("first_name", "")).strip(),
        "last_name": str(data.get("last_name", "")).strip(),
    }, None


def create_tenant_admin(tenant, cleaned):
    # No password is set. The admin chooses theirs through the reset link.
    return User.objects.create_user(
        username=cleaned["email"],
        email=cleaned["email"],
        password=None,
        first_name=cleaned["first_name"],
        last_name=cleaned["last_name"],
        tenant=tenant,
        is_tenant_admin=True,
    )


def send_invite(user):
    """Emails a set-your-password link. Returns False if sending failed."""
    ForgotPasswordRequest.objects.filter(user=user).delete()
    request = ForgotPasswordRequest.objects.create(user=user)
    try:
        send_forgot_password_email(user, request.code)
        return True
    except Exception:
        logger.exception("Tenant admin invite failed | user=%s", user.pk)
        request.delete()
        return False


def tenant_payload(tenant_id):
    return TenantSerializer(
        with_counts(Tenant.objects.filter(pk=tenant_id)).first()
    ).data


class ConsoleStatsView(APIView):
    """Platform-wide numbers only. No names, no sessions, no attendance rows."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        tenants = Tenant.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            suspended=Count("id", filter=Q(is_active=False)),
        )

        tenant_users = User.objects.filter(tenant__isnull=False)
        users = tenant_users.aggregate(
            members=Count("id", filter=Q(is_tenant_admin=False)),
            admins=Count("id", filter=Q(is_tenant_admin=True)),
            with_face=Count(
                "id", filter=Q(is_tenant_admin=False, face_embeddings__isnull=False)
            ),
        )

        by_status = Attendance.objects.values("status").annotate(count=Count("id"))

        newest = with_counts(Tenant.objects.all()).order_by("-created_at")[:5]
        busiest = with_counts(Tenant.objects.all()).order_by("-session_count")[:5]

        return Response(
            {
                "tenants": tenants,
                "users": users,
                "sessions": AttendanceSession.objects.count(),
                "attendance_by_status": {i["status"]: i["count"] for i in by_status},
                "newest_tenants": TenantSerializer(newest, many=True).data,
                "busiest_tenants": TenantSerializer(busiest, many=True).data,
            }
        )

class TenantListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        tenants = with_counts(Tenant.objects.all())

        search = request.query_params.get("search", "").strip()
        if search:
            tenants = tenants.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )

        state = request.query_params.get("status")
        if state == "active":
            tenants = tenants.filter(is_active=True)
        elif state == "suspended":
            tenants = tenants.filter(is_active=False)

        return Response(
            {
                "tenants": TenantSerializer(
                    tenants.order_by("-created_at"), many=True
                ).data
            }
        )

    def post(self, request):
        """Body: {"name": "...", "slug": "optional", "admin": {"email", "first_name", "last_name"}}"""
        name = str(request.data.get("name", "")).strip()
        if not name:
            return error("name is required")

        requested_slug = str(request.data.get("slug", "")).strip()
        if requested_slug:
            slug = slugify(requested_slug)
            if not slug or Tenant.objects.filter(slug=slug).exists():
                return error("That slug is invalid or already taken")
        else:
            slug = unique_slug(name)

        cleaned, problem = check_admin_data(request.data.get("admin"))
        if problem:
            return error(problem)

        try:
            with transaction.atomic():
                tenant = Tenant.objects.create(name=name, slug=slug)
                admin = create_tenant_admin(tenant, cleaned)
        except IntegrityError:
            return error("Unable to create the tenant, please try again")

        return Response(
            {
                "detail": "Tenant created",
                "tenant": tenant_payload(tenant.pk),
                # False means the email failed. The admin can use "Forgot password".
                "invite_sent": send_invite(admin),
            },
            status=status.HTTP_201_CREATED,
        )

class TenantDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_tenant(self, tenant_id):
        return Tenant.objects.filter(id=tenant_id).first()

    def get(self, request, tenant_id):
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return error("Tenant not found", status.HTTP_404_NOT_FOUND)

        admins = User.objects.filter(tenant=tenant, is_tenant_admin=True).values(
            "id", "first_name", "last_name", "email", "is_active", "email_verified"
        )
        return Response({"tenant": tenant_payload(tenant.pk), "admins": list(admins)})

    def patch(self, request, tenant_id):
        """Rename, change the slug, or suspend / reactivate with is_active."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return error("Tenant not found", status.HTTP_404_NOT_FOUND)

        fields = []

        if "name" in request.data:
            name = str(request.data["name"]).strip()
            if not name:
                return error("name can't be empty")
            tenant.name = name
            fields.append("name")

        if "slug" in request.data:
            slug = slugify(str(request.data["slug"]))
            if (
                not slug
                or Tenant.objects.filter(slug=slug).exclude(pk=tenant.pk).exists()
            ):
                return error("That slug is invalid or already taken")
            tenant.slug = slug
            fields.append("slug")

        if "is_active" in request.data:
            value = request.data["is_active"]
            if isinstance(value, str):
                value = value.strip().lower() in ("true", "1")
            tenant.is_active = bool(value)
            fields.append("is_active")

        if fields:
            tenant.save(update_fields=fields)

        return Response(
            {"detail": "Tenant updated", "tenant": tenant_payload(tenant.pk)}
        )

    def delete(self, request, tenant_id):
        """Permanent. The body must repeat the tenant's slug: {"confirm": "<slug>"}"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return error("Tenant not found", status.HTTP_404_NOT_FOUND)

        if request.data.get("confirm") != tenant.slug:
            return error("Send the tenant's slug as 'confirm' to delete it")

        if User.objects.filter(tenant=tenant, is_staff=True).exists():
            return error("This tenant contains a platform admin and can't be deleted")

        with transaction.atomic():
            AttendanceSession.objects.filter(
                tenant=tenant
            ).delete()  # cascades attendance
            User.objects.filter(tenant=tenant).delete()
            tenant.delete()

        return Response({"detail": "Tenant deleted"})

class TenantAdminCreateView(APIView):

    permission_classes = [IsAdminUser]

    def post(self, request, tenant_id):
        tenant = Tenant.objects.filter(id=tenant_id).first()
        if not tenant:
            return error("Tenant not found", status.HTTP_404_NOT_FOUND)

        cleaned, problem = check_admin_data(request.data)
        if problem:
            return error(problem)

        admin = create_tenant_admin(tenant, cleaned)
        return Response(
            {
                "detail": "Admin created",
                "admin": {"id": admin.id, "email": admin.email},
                "invite_sent": send_invite(admin),
            },
            status=status.HTTP_201_CREATED,
        )


class ReleaseListCreateView(generics.ListCreateAPIView):
    queryset = DesktopRelease.objects.prefetch_related("assets")
    serializer_class = DesktopReleaseSerializer
    permission_classes = [IsAdminUser]


class ReleaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DesktopRelease.objects.prefetch_related("assets")
    serializer_class = DesktopReleaseSerializer
    permission_classes = [IsAdminUser]


class ReleasePublishView(APIView):

    permission_classes = [IsAdminUser]
    publish = True

    def post(self, request, pk):
        release = get_object_or_404(
            DesktopRelease.objects.prefetch_related("assets"), pk=pk
        )

        if self.publish:
            if not release.assets.exists():
                return Response(
                    {"error": "Add at least one download before publishing."},
                    status=400,
                )
            if not release.is_published:
                release.is_published = True
                release.published_at = timezone.now()
        elif release.is_published:
            release.is_published = False
            release.published_at = None

        release.save(update_fields=["is_published", "published_at", "updated_at"])
        return Response(DesktopReleaseSerializer(release).data)


class AssetListCreateView(generics.ListCreateAPIView):

    serializer_class = DesktopReleaseAssetSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = DesktopReleaseAsset.objects.select_related("release")
        release_id = self.request.query_params.get("release")
        if release_id and release_id.isdigit():
            qs = qs.filter(release_id=release_id)
        return qs.order_by("release_id", "platform", "architecture")


class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DesktopReleaseAsset.objects.select_related("release")
    serializer_class = DesktopReleaseAssetSerializer
    permission_classes = [IsAdminUser]

