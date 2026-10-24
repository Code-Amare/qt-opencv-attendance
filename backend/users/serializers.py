import re
from django.utils.text import slugify
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User
from tenant.models import Tenant
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from tenant.serializers import TenantSerializer


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "section",
            "phone_number",
            "date_of_birth",
        ]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "section": {"required": False, "allow_blank": True, "allow_null": True},
            "phone_number": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "date_of_birth": {"required": False, "allow_null": True},
        }


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    has_face = serializers.SerializerMethodField()
    tenant = TenantSerializer()

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
            "is_staff",
            "is_active",
            "tenant",
            "is_tenant_admin",
            "has_face",
        ]
        read_only_fields = [
            "id",
            "email_verified",
            "two_factor_enabled",
        ]

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        return None

    def get_has_face(self, obj):
        if obj.face_embeddings:
            return True
        return None


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


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "section",
            "phone_number",
            "date_of_birth",
            "is_active",
        ]


class RegisterSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_organization_name(self, value):
        name = re.sub(r"\s+", " ", value).strip()
        slug = slugify(name)
        if not slug:
            raise serializers.ValidationError(
                "Organization name must contain letters or numbers."
            )
        if Tenant.objects.filter(Q(name__iexact=name) | Q(slug=slug)).exists():
            raise serializers.ValidationError(
                "An organization with this name already exists."
            )
        self._slug = slug
        return name

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        attrs["slug"] = self._slug
        return attrs
