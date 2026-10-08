from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "section",
            "profile_picture",
            "phone_number",
            "date_of_birth",
            "email_verified",
            "two_factor_enabled",
        ]
        read_only_fields = [
            "id",
            "email_verified",
            "two_factor_enabled",
        ]


class BulkUserSerializer(serializers.ListSerializer):
    child = UserSerializer()

    def create(self, validated_data):
        users = [User(**data) for data in validated_data]
        return User.objects.bulk_create(users)


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "section",
            "phone_number",
        ]
        list_serializer_class = BulkUserSerializer