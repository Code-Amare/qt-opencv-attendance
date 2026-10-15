from cloudinary.models import CloudinaryField
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import (
    AbstractUser,
)
import secrets
import numpy as np


class User(AbstractUser):
    email = models.EmailField(unique=True)
    section = models.CharField(max_length=50, null=True, blank=True)
    profile_picture = CloudinaryField(
        "ai/opencv-attendance/profile_picture",
        blank=True,
        null=True,
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
    )
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)

    google_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    face_embeddings = models.BinaryField(blank=True, null=True, editable=False)
    embeddings_updated_at = models.DateTimeField(blank=True, null=True)

    @property
    def has_face(self):
        return bool(self.face_embeddings)

    def get_embeddings(self):
        if not self.face_embeddings:
            return np.empty((0, 512), dtype=np.float32)
        return np.frombuffer(self.face_embeddings, dtype=np.float32).reshape(-1, 512)

    def set_embeddings(self, arr):
        arr = np.asarray(arr, dtype=np.float32).reshape(-1, 512)
        self.face_embeddings = arr.tobytes()


class EmailLoginCode(models.Model):
    user = models.OneToOneField(User, related_name="email_login_code", on_delete=models.CASCADE)
    code = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def save(self, *args, **kwargs):
        if not self.pk:
            self.code = secrets.token_urlsafe(32)
            self.expires_at = timezone.now() + timedelta(minutes=5)

        super().save(*args, **kwargs)

    def verify(self, code):
        return (
                not self.is_expired()
                and (code == self.code)
        )


class ForgotPasswordRequest(models.Model):
    user = models.OneToOneField(User, related_name="forgot_password_request", on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    requested_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.code = secrets.token_urlsafe(32)
            self.expires_at = timezone.now() + timedelta(minutes=10)

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def verify(self, code):
        return (
                not self.is_expired()
                and (code == self.code)
        )

    def __str__(self):
        return f"{self.user.email} Password Reset Request"