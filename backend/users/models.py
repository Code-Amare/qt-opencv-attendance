from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
import uuid


class User(AbstractUser):
    email = models.EmailField(unique=True)
    section = models.CharField(max_length=50)
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

