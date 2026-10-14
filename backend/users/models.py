from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
import uuid
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

