from django.utils import timezone
from rest_framework import serializers

from .models import Attendance, AttendanceSession
from users.serializers import UserSerializer


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "created_by",
            "name",
            "started_at",
            "ended_at",
            "late_time",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "status",
            "created_at",
        ]

    def validate(self, attrs):
        started_at = attrs.get("started_at")
        ended_at = attrs.get("ended_at")

        if started_at and ended_at and ended_at <= started_at:
            raise serializers.ValidationError(
                {"ended_at": "ended_at must be later than started_at."}
            )

        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    session = AttendanceSessionSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "session",
            "user",
            "status",
            "recorded_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "recorded_at",
        ]
