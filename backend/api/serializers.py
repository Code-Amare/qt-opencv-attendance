import re
from rest_framework import serializers
from .models import SiteSettings, DesktopRelease, DesktopReleaseAsset


class SiteSettingsSerializer(serializers.Serializer):
    class Meta:
        model = SiteSettings
        fields = "__all__"


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


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
