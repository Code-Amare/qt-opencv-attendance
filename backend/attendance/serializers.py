from django.utils import timezone
from rest_framework import serializers

from .models import Attendance, AttendanceSession
from users.serializers import UserSerializer


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "name",
            "started_at",
            "ended_at",
            "late_time",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "created_at",
        ]

    def validate(self, data):
        started = data.get("started_at")
        ended = data.get("ended_at")
        if started and ended and ended <= started:
            raise serializers.ValidationError("ended_at must be after started_at.")
        return data


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
