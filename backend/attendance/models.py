from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class AttendanceSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_attendance_sessions",
    )

    name = models.CharField(max_length=255)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    late_time = models.DurationField(default=timedelta(minutes=10))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_ended(self):
        if self.status in {
            self.Status.COMPLETED,
            self.Status.CANCELLED,
        }:
            return True

        return timezone.now() >= self.ended_at

    @property
    def is_absent(self):
        return timezone.now() >= (self.ended_at + self.self.late_time)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.name


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        LATE = "late", "Late"
        ABSENT = "absent", "Absent"

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="attendances",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attendances",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
    )

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="unique_attendance_per_session",
            )
        ]
        ordering = ["recorded_at"]

    def __str__(self):
        return f"{self.user} - {self.session}"
