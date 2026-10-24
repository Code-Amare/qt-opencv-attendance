import logging
import secrets
import cloudinary.uploader
from django.utils.text import slugify
import requests as http_requests
from axes.utils import reset
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from tenant.models import Tenant
from utils.emails import (
    send_contact_admin_email,
    send_forgot_password_email,
    send_login_link_email,
    send_verification_code_email,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from .models import EmailLoginCode, EmailLoginLink, ForgotPasswordRequest
from .serializers import UserSerializer, RegisterSerializer, ProfileUpdateSerializer
from django.db import IntegrityError, transaction
from utils.auth import IsSuperOrTenantAdmin

logger = logging.getLogger(__name__)

User = get_user_model()

ACCESS_MAX_AGE = 60 * 15
REFRESH_MAX_AGE = 60 * 60 * 24 * 7
PICTURE_FOLDER = "ai/opencv-attendance/profile_picture"
COOKIE_SAMESITE = "Lax" if settings.DEBUG else "None"
ALLOWED_PICTURE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PICTURE_BYTES = 5 * 1024 * 1024


def set_cookie(response, key, value, max_age=None, httponly=True):
    response.set_cookie(
        key,
        str(value),
        max_age=max_age,
        httponly=httponly,
        secure=True,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def send_cookies(request, user):
    refresh_token = RefreshToken.for_user(user)
    access_token = refresh_token.access_token
    csrf_token = get_token(request)

    response = Response(
        {
            "user": UserSerializer(user).data,
            "tokens": {
                "access": str(access_token),
                "refresh": str(refresh_token),
                "csrf": csrf_token,
            },
        },
        status=status.HTTP_200_OK,
    )

    set_cookie(response, "access_token", access_token, ACCESS_MAX_AGE)
    set_cookie(response, "refresh_token", refresh_token, REFRESH_MAX_AGE)
    set_cookie(response, "csrftoken", csrf_token, httponly=False)
    return response


def find_user(identifier):
    return (
        User.objects.filter(username=identifier).first()
        or User.objects.filter(email=identifier).first()
    )


def check_credentials(request):
    identifier = str(request.data.get("username_or_email", "")).strip()
    password = request.data.get("password", "")

    if not identifier or not password:
        return None, Response(
            {"error": "Username and Password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = find_user(identifier)
    if not user or not user.check_password(password):
        return None, Response(
            {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_active:
        return None, Response(
            {"error": "Your account has been disabled."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return user, None


class MeView(APIView):
    def get(self, request):
        return Response(
            {"user": UserSerializer(request.user).data}, status=status.HTTP_200_OK
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token missing"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
        except TokenError as e:
            logger.info("Refresh failed: %s", e)
            return Response(
                {"detail": "Invalid or expired refresh token", "refresh": True},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response({"success": True}, status=status.HTTP_200_OK)
        set_cookie(response, "access_token", token.access_token, ACCESS_MAX_AGE)
        set_cookie(response, "refresh_token", token, REFRESH_MAX_AGE)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale token must not stop the cookies clearing

    def post(self, request):
        response = Response(
            {"message": "Logged out successfully."}, status=status.HTTP_200_OK
        )
        for key in ("access_token", "refresh_token", "csrftoken"):
            response.delete_cookie(key, path="/", samesite=COOKIE_SAMESITE)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user, error = check_credentials(request)
        if error:
            return error

        if not (user.two_factor_enabled or not user.email_verified):
            return send_cookies(request, user)

        login_link = EmailLoginLink.objects.filter(user=user).first()

        if login_link and not login_link.is_expired():
            return Response(
                {
                    "error": "Login link already sent, please try later to request a new one."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if login_link:
            login_link.delete()

        new_login_link = EmailLoginLink.objects.create(user=user)
        try:
            send_login_link_email(user=user, code=new_login_link.code)
        except Exception:
            logger.exception("Login link email failed | user=%s", user.pk)
            new_login_link.delete()
            return Response(
                {"error": "Unable to send the login link. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": "A login link has been sent to your email address.",
                "twofa_required": True,
            },
            status=status.HTTP_200_OK,
        )


class GUILoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        user, error = check_credentials(request)
        if error:
            return error

        if not user.is_tenant_admin:
            return Response(
                {"error": "You must be a tenant admin"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login_code = EmailLoginCode.objects.filter(user=user).first()

        if login_code and not login_code.is_expired():
            return Response(
                {"error": "Wait a minute to request another OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if login_code:
            login_code.delete()

        new_login_code = EmailLoginCode.objects.create(user=user)
        try:
            send_verification_code_email(user=user, code=new_login_code.code)
        except Exception:
            logger.exception("Verification code email failed | user=%s", user.pk)
            new_login_code.delete()
            return Response(
                {
                    "error": "Unable to send the verification code. Please try again later."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not user.email_verified:
            return Response(
                {"error": "Email not verified yet.", "twofa_required": True},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "OTP has been sent, check your inbox.", "twofa_required": True},
            status=status.HTTP_200_OK,
        )


class VerifyUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = str(request.data.get("username_or_email", "")).strip()
        code = str(request.data.get("code", "")).strip()

        if not identifier or not code:
            return Response(
                {"error": "Username/email and code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = find_user(identifier)
        if not user or not user.is_active:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )

        login_code = EmailLoginCode.objects.filter(user=user).first()

        if login_code and login_code.is_expired():
            return Response(
                {"error": "Code expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        if login_code and login_code.verify(code):
            with transaction.atomic():
                login_code.delete()
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            return send_cookies(request, user)

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)


class LoginViaLinkView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, code):
        login_link = EmailLoginLink.objects.filter(code=code).first()

        if not login_link or login_link.is_expired():
            return Response(
                {"error": "This login link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = login_link.user
        if not user.is_active:
            return Response(
                {"error": "Your account has been disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                user.email_verified = True
                user.save(update_fields=["email_verified"])
                reset(username=user.email)
                login_link.delete()
        except Exception:
            logger.exception("Login via link failed | user=%s", user.pk)
            return Response(
                {"error": "Unable to log you in."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return send_cookies(request, user)


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"error": "Google token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            google_response = http_requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if google_response.status_code != 200:
                return Response(
                    {"error": "Invalid Google token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            google_user = google_response.json()
        except (http_requests.RequestException, ValueError):
            return Response(
                {"error": "Unable to verify the Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = google_user.get("email")
        google_id = google_user.get("sub")

        if not google_user.get("email_verified", False):
            return Response(
                {"error": "Google email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()
        if not user:
            tenant_name = f"Workspace {secrets.token_hex(4)}"
            try:
                with transaction.atomic():
                    tenant = Tenant.objects.create(
                        name=tenant_name, slug=slugify(tenant_name)
                    )
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=None,
                        first_name=google_user.get("given_name", ""),
                        last_name=google_user.get("family_name", ""),
                        tenant=tenant,
                        is_tenant_admin=True,
                        email_verified=True,
                        google_id=google_id,
                    )
            except IntegrityError:
                return Response(
                    {"error": "Unable to create your account. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response = send_cookies(request, user)
            response.data["registered"] = True
            response.data["onboarding_required"] = True
            response.status_code = status.HTTP_201_CREATED
            return response

        if not user.is_active:
            return Response(
                {"error": "Your account has been disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.google_id and user.google_id != google_id:
            return Response(
                {"error": "This account is linked to a different Google account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.google_id = google_id
            user.email_verified = True
            user.save(update_fields=["google_id", "email_verified"])
            reset(username=user.email)

        return send_cookies(request, user)


class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get("email", "")).strip()

        if not email:
            return Response(
                {"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "Invalid Email address."}, status=status.HTTP_400_BAD_REQUEST
            )

        existing = ForgotPasswordRequest.objects.filter(user=user).first()
        if existing and not existing.is_expired():
            return Response(
                {"error": "Request has already been sent. Please try later."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if existing:
                existing.delete()
            new_request = ForgotPasswordRequest.objects.create(user=user)

        try:
            send_forgot_password_email(user, new_request.code)
        except Exception as e:
            print(e)
            logger.exception("Forgot-password email failed | user=%s", user.pk)
            new_request.delete()
            return Response(
                {"error": "Unable to send the reset link. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"detail": "A password reset link has been sent to your email address."},
            status=status.HTTP_200_OK,
        )


class CheckResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        code = str(request.data.get("code", "")).strip()

        if not code:
            return Response(
                {"error": "Code is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        reset_request = ForgotPasswordRequest.objects.filter(code=code).first()
        if not reset_request or reset_request.is_expired():
            return Response(
                {"error": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"detail": "This code is valid."}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, code):
        reset_request = ForgotPasswordRequest.objects.filter(code=code).first()
        if not reset_request or reset_request.is_expired():
            return Response(
                {"error": "Invalid or expired password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = str(request.data.get("password", "")).strip()
        if not password:
            return Response(
                {"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = reset_request.user

        if user.check_password(password):
            return Response(
                {
                    "error": "Your new password must be different from your current password. Please request a new verification code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(password)
            user.save()
            reset_request.delete()
            reset(username=user.email)

        return Response(
            {"detail": "Your password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


class ContactResponseView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # also removes the CSRF requirement for public visitors

    SUBJECTS = [
        "Request account access",
        "Forgot password / locked out",
        "Report a problem",
        "General question",
    ]

    def post(self, request):
        name = str(request.data.get("name", "")).strip()
        email = str(request.data.get("email", "")).strip()
        subject = str(request.data.get("subject", "")).strip()
        message = str(request.data.get("message", "")).strip()

        if not all([name, email, subject, message]):
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "Enter a valid email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subject not in self.SUBJECTS:
            return Response(
                {"error": "Invalid subject."}, status=status.HTTP_400_BAD_REQUEST
            )

        if len(message) < 10:
            return Response(
                {"error": "Message is too short."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            send_contact_admin_email(name, email, subject, message)
        except Exception:
            logger.exception(
                "Contact form email failed | email=%s | subject=%r", email, subject
            )
            return Response(
                {"error": "Unable to send your message. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"detail": "Message sent."}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            first = next(iter(serializer.errors.values()))[0]
            return Response(
                {"error": str(first), "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            with transaction.atomic():
                tenant = Tenant.objects.create(
                    name=data["organization_name"], slug=data["slug"]
                )
                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                    tenant=tenant,
                    is_tenant_admin=True,
                    email_verified=False,
                )
        except IntegrityError:
            return Response(
                {"error": "Organization, username or email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link = EmailLoginLink.objects.create(user=user)
        try:
            send_login_link_email(user=user, code=link.code)
        except Exception:
            logger.exception("Registration email failed | user=%s", user.pk)
            link.delete()

        return Response(
            {
                "detail": "Account created. Check your email to confirm your address and sign in.",
                "tenant": {"name": tenant.name, "slug": tenant.slug},
            },
            status=status.HTTP_201_CREATED,
        )


class EditProfileView(APIView):
    permission_classes = [IsSuperOrTenantAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request, user_id):
        user = User.objects.filter(id=user_id, tenant=request.user.tenant).first()

        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        picture = request.FILES.get("profile_picture")
        remove_picture = str(
            request.data.get("remove_profile_picture", "")
        ).strip().lower() in ("true", "1")

        if picture:
            if picture.content_type not in ALLOWED_PICTURE_TYPES:
                return Response(
                    {"errors": {"profile_picture": ["Use a JPEG, PNG or WebP image."]}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if picture.size > MAX_PICTURE_BYTES:
                return Response(
                    {
                        "errors": {
                            "profile_picture": ["The image must be 5 MB or smaller."]
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        changed = {
            field: value
            for field, value in serializer.validated_data.items()
            if (getattr(user, field) or None) != (value or None)
        }

        if not changed and not picture and not remove_picture:
            return Response(
                {"is_no_change": True, "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_public_id = user.profile_picture.public_id if user.profile_picture else None
        new_public_id = None

        if picture:
            try:
                result = cloudinary.uploader.upload(
                    picture,
                    folder=PICTURE_FOLDER,
                    resource_type="image",
                    transformation=[
                        {
                            "width": 512,
                            "height": 512,
                            "crop": "fill",
                            "gravity": "face",
                        }
                    ],
                )
            except Exception:
                logger.exception("Profile picture upload failed | user=%s", user.pk)
                return Response(
                    {"error": "Unable to upload the picture. Please try again."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            new_public_id = result["public_id"]
            changed["profile_picture"] = (
                f"image/upload/v{result['version']}/{new_public_id}.{result['format']}"
            )
        elif remove_picture:
            changed["profile_picture"] = None

        for field, value in changed.items():
            setattr(user, field, value)

        try:
            user.save(update_fields=list(changed))
        except Exception:
            if new_public_id:
                try:
                    cloudinary.uploader.destroy(new_public_id, invalidate=True)
                except Exception:
                    logger.exception("Orphan cleanup failed | id=%s", new_public_id)
            raise

        if "profile_picture" in changed:
            user.refresh_from_db(fields=["profile_picture"])

        if "profile_picture" in changed and old_public_id != new_public_id:
            if old_public_id:
                try:
                    cloudinary.uploader.destroy(old_public_id, invalidate=True)
                except Exception:
                    logger.exception(
                        "Old picture cleanup failed | id=%s", old_public_id
                    )

        return Response(
            {"detail": "Profile updated", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
