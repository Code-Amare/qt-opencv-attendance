from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Attendance, AttendanceSession
from users.serializers import UserSerializer

User = get_user_model()


class AttendanceSessionSerializer(serializers.ModelSerializer):
    target_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        source="targets",
        write_only=True,
        required=False,
    )
    targets = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    target_count = serializers.SerializerMethodField()

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
            "target_ids",
            "targets",
            "target_count",
        ]
        read_only_fields = [
            "status",
            "created_at",
        ]

    def get_target_count(self, obj):
        annotated = getattr(obj, "target_count", None)
        return annotated if annotated is not None else obj.targets.count()

    def validate_target_ids(self, users):
        tenant_id = self.context["request"].user.tenant_id
        if any(u.tenant_id != tenant_id for u in users):
            raise serializers.ValidationError(
                "Some users don't belong to your organization."
            )
        if not all(u.is_active for u in users):
            raise serializers.ValidationError("Some selected users are disabled.")
        return users

    def validate(self, data):
        started = data.get("started_at", getattr(self.instance, "started_at", None))
        ended = data.get("ended_at", getattr(self.instance, "ended_at", None))
        if started and ended and ended <= started:
            raise serializers.ValidationError("ended_at must be after started_at.")

        if self.instance is None and not data.get("targets"):
            raise serializers.ValidationError(
                {"target_ids": "Select at least one person."}
            )

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
