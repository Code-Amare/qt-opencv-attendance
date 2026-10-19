from django.db import models
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100)
    site_logo = CloudinaryField("logos", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings instance is allowed.")

        return super().save(*args, **kwargs)


class DesktopRelease(models.Model):
    version = models.CharField(
        max_length=20,
        unique=True,
    )
    release_notes = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"FaceCall v{self.version}"


class DesktopReleaseAsset(models.Model):
    class Platform(models.TextChoices):
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"
        LINUX = "linux", "Linux"

    class Architecture(models.TextChoices):
        X64 = "x64", "x86_64"
        ARM64 = "arm64", "ARM64"

    release = models.ForeignKey(
        DesktopRelease,
        on_delete=models.CASCADE,
        related_name="assets",
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )
    architecture = models.CharField(
        max_length=10,
        choices=Architecture.choices,
        default=Architecture.X64,
    )
    download_url = models.URLField(max_length=1000)
    file_size = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["release", "platform", "architecture"],
                name="unique_release_platform_architecture",
            ),
        ]

    def __str__(self):
        return (
            f"FaceCall v{self.release.version} "
            f"- {self.platform} ({self.architecture})"
        )
