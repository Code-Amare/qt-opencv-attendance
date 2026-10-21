import re
from django.db.models import Count, Q
from rest_framework import serializers

from tenant.models import Tenant
from .models import DesktopRelease, DesktopReleaseAsset

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


def with_counts(queryset):
    """Annotate tenants with counts. distinct=True stops the joins inflating each other."""
    return queryset.annotate(
        member_count=Count(
            "users", filter=Q(users__is_tenant_admin=False), distinct=True
        ),
        admin_count=Count(
            "users", filter=Q(users__is_tenant_admin=True), distinct=True
        ),
        session_count=Count("attendance_sessions", distinct=True),
    )


class TenantSerializer(serializers.ModelSerializer):
    # Always serialize from with_counts(...), these come from the annotations
    member_count = serializers.IntegerField(read_only=True)
    admin_count = serializers.IntegerField(read_only=True)
    session_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "created_at",
            "member_count",
            "admin_count",
            "session_count",
        ]
        read_only_fields = fields


class DesktopReleaseAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesktopReleaseAsset
        fields = [
            "id",
            "release",
            "platform",
            "architecture",
            "download_url",
            "file_size",
            "checksum_sha256",
        ]

    def validate_download_url(self, value):
        if not value.lower().startswith("https://"):
            raise serializers.ValidationError("The download URL must use https.")
        return value

    def validate_checksum_sha256(self, value):
        if not value:
            return value
        if not SHA256_RE.match(value):
            raise serializers.ValidationError(
                "Must be a 64-character hexadecimal SHA-256 hash."
            )
        return value.lower()


class DesktopReleaseSerializer(serializers.ModelSerializer):
    assets = DesktopReleaseAssetSerializer(many=True, read_only=True)

    class Meta:
        model = DesktopRelease
        fields = [
            "id",
            "version",
            "release_notes",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
            "assets",
        ]
        read_only_fields = [
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def validate_version(self, value):
        value = value.strip().lstrip("vV")
        if not VERSION_RE.match(value):
            raise serializers.ValidationError(
                "Use a version like 1.2.0 (optionally 1.2.0-beta.1)."
            )
        taken = DesktopRelease.objects.filter(version=value)
        if self.instance:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError(
                "A release with this version already exists."
            )
        return value


class PublicAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesktopReleaseAsset
        fields = [
            "platform",
            "architecture",
            "download_url",
            "file_size",
            "checksum_sha256",
        ]


class PublicReleaseSerializer(serializers.ModelSerializer):
    assets = PublicAssetSerializer(many=True, read_only=True)

    class Meta:
        model = DesktopRelease
        fields = ["version", "release_notes", "published_at", "assets"]
