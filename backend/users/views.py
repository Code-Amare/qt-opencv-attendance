import io
import numpy as np
from axes.utils import reset
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.middleware.csrf import get_token
from django.db import transaction
from .models import EmailLoginLink, ForgotPasswordRequest, EmailLoginCode
from .serializers import UserCreateSerializer, UserSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from utils.emails import (
    send_forgot_password_email,
    send_verification_code_email,
    send_login_link_email,
    send_contact_admin_email,
)
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


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

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=60 * 15,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=60 * 60 * 24 * 7,
    )

    response.set_cookie(
        "csrftoken",
        csrf_token,
        httponly=False,
        secure=True,
        samesite="Lax",
    )

    return response


class MeView(APIView):
    def get(self, request):
        me = request.user
        return Response({"user": UserSerializer(me).data}, status=status.HTTP_200_OK)


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

            response = Response({"success": True}, status=status.HTTP_200_OK)
            response.set_cookie(
                "access_token",
                str(token.access_token),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=60 * 15,
                path="/",
            )

            response.set_cookie(
                "refresh_token",
                str(token),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=60 * 60 * 24 * 7,
                path="/",
            )
            return response
        except TokenError as e:
            print("TokenError:", type(e).__name__)
            print("Message:", str(e))
            return Response(
                {"detail": "Invalid or expired refresh token", "refresh": True},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class RecognitionMapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.all().exclude(is_staff=True).values("id", "first_name")
        return Response({"users": users}, status=status.HTTP_200_OK)


class BulkUserCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, many=True)

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "detail": "Users created successfully.",
                    "users": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class UsersListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.filter().exclude(is_staff=True)
        if not users:
            return Response(
                {"error": "No user found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"users": UserSerializer(users, many=True).data}, status=status.HTTP_200_OK
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username_or_email", "").strip()
        password = request.data.get("password", "")

        if not username_or_email or not password:
            return Response(
                {"error": "Username and Password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username=username_or_email).first()
        if not user:
            user = User.objects.filter(email=username_or_email).first()
            if not user:
                return Response(
                    {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
                )

        if not user.check_password(password):
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.two_factor_enabled or not user.email_verified:

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

                send_login_link_email(
                    user=user,
                    code=new_login_link.code,
                )

            except Exception:

                new_login_link.delete()

                return Response(
                    {
                        "error": (
                            "Unable to send the login link. " "Please try again later."
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "detail": "A login link has been sent to your email address.",
                    "twofa_required": True,
                },
                status=status.HTTP_200_OK,
            )

        return send_cookies(request, user)


class GUILoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username_or_email", "").strip()
        password = request.data.get("password", "")

        if not username_or_email or not password:
            return Response(
                {"error": "Username and Password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username=username_or_email).first()
        if not user:
            user = User.objects.filter(email=username_or_email).first()
            if not user:
                return Response(
                    {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
                )

        if not user.check_password(password):
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )

        login_code = EmailLoginCode.objects.filter(user=user).first()

        if login_code and not login_code.is_expired():
            return Response(
                {"error": "Wait a mintue to request another OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if login_code:
            login_code.delete()
        new_login_code = EmailLoginCode.objects.create(user=user)
        try:

            send_verification_code_email(
                user=user,
                code=new_login_code.code,
            )

        except Exception:

            new_login_code.delete()

            return Response(
                {
                    "error": (
                        "Unable to send the login link. " "Please try again later."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if user.email_verified:
            return Response(
                {
                    "error": "Email not verified yet.",
                    "twofa_required": True,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "detail": "OTP has been sent, check your inbox.",
                "twofa_required": True,
            },
            status=status.HTTP_200_OK,
        )


class LoginViaEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, code):
        if not code:
            return Response(
                {"error": "Invalid login link."}, status=status.HTTP_400_BAD_REQUEST
            )

        login_link = EmailLoginLink.objects.filter(code=code).first()

        if not login_link or login_link.is_expired():
            return Response(
                {"error": "This login link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            with transaction.atomic():
                user = login_link.user
                user.email_verified = True
                user.save(update_fields=["email_verified"])

                reset(username=user.email)

                login_link.delete()

                return send_cookies(request, user)

        except Exception as e:
            return Response(
                {
                    "error": "Unable to log you in.",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecognitionMapFileView(APIView):

    def get(self, request):
        users = User.objects.exclude(face_embeddings__isnull=True).only(
            "id", "first_name", "face_embeddings"
        )

        vectors, labels, user_ids, first_names = [], [], [], []
        for u in users:
            arr = u.get_embeddings()
            if len(arr) == 0:
                continue
            vectors.append(arr)
            labels.extend([u.id] * len(arr))
            user_ids.append(u.id)
            first_names.append(u.first_name)

        buf = io.BytesIO()
        np.savez_compressed(
            buf,
            embeddings=(
                np.concatenate(vectors) if vectors else np.empty((0, 512), np.float32)
            ),
            labels=np.array(labels, dtype=np.int32),
            user_ids=np.array(user_ids, dtype=np.int32),
            first_names=np.array(first_names, dtype=str),
        )

        response = HttpResponse(buf.getvalue(), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="face_embeddings.npz"'
        return response


class SaveFaceEmbeddingView(APIView):
    def post(self, request, user_id):
        face_embedding = request.data.get("face_embedding")

        if not isinstance(face_embedding, list) or not face_embedding:
            return Response(
                {"error": "A face embedding list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "Invalid User id"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            embedding = np.asarray(face_embedding, dtype=np.float32)

            if embedding.shape != (512,):
                raise ValueError("Embedding must contain exactly 512 values")

            if not np.isfinite(embedding).all():
                raise ValueError("Embedding contains invalid numbers")

            user.set_embeddings(embedding)
            user.embeddings_updated_at = timezone.now()
            user.save(
                update_fields=[
                    "face_embeddings",
                    "embeddings_updated_at",
                ]
            )

        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid face embedding format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Face embedding saved successfully"},
            status=status.HTTP_200_OK,
        )


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
            import requests as http_requests

            google_response = http_requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )

            if google_response.status_code != 200:
                return Response(
                    {"error": "Invalid Google token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            google_user = google_response.json()

        except ValueError:
            return Response(
                {"error": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = google_user.get("email")
        google_id = google_user.get("sub")
        email_verified = google_user.get("email_verified", False)

        if not email_verified:
            return Response(
                {"error": "Google email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()

        if not user:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if not user.is_active:
            return Response(
                {"error": "Your account has been disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.google_id:
            user.google_id = google_id

        with transaction.atomic():
            user.email_verified = True

            user.save(update_fields=["google_id", "email_verified"])
            reset(username=user.email)

        return send_cookies(request, user)


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
        name = request.data.get("name", "").strip()
        email = request.data.get("email", "").strip()
        subject = request.data.get("subject", "").strip()
        message = request.data.get("message", "").strip()

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


class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email", "").strip()

        user = User.objects.filter(email=email).first()

        if not email:
            return Response(
                {"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not user:
            return Response(
                {"error": "Invalid Email address."}, status=status.HTTP_400_BAD_REQUEST
            )

        forgot_password_request = ForgotPasswordRequest.objects.filter(
            user=user
        ).first()

        if forgot_password_request and not forgot_password_request.is_expired():
            return Response(
                {"error": "Request has already been sent. Please try later."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if forgot_password_request:
                forgot_password_request.delete()
            new_fpr = ForgotPasswordRequest.objects.create(user=user)

            send_forgot_password_email(user, new_fpr.code)
            return Response(
                {
                    "detail": "A password reset link has been sent to your email address."
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Something went wrong."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class CheckResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        code = request.data.get("code", "").strip()

        if not code:
            return Response(
                {"error": "Code is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        reset_password_request = ForgotPasswordRequest.objects.filter(code=code).first()
        print(reset_password_request)
        if not reset_password_request or reset_password_request.is_expired():
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

        password = request.data.get("password", "").strip()

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


class VerifyUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username_or_email", "").strip()
        code = request.data.get("code", "").strip()

        if not username_or_email or not code:
            return Response(
                {"error": "Username/email and code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username=username_or_email).first()
        if not user:
            user = User.objects.filter(email=username_or_email).first()

        if not user:
            return Response(
                {"error": "Invalid credientials"}, status=status.HTTP_400_BAD_REQUEST
            )

        login_code = EmailLoginCode.objects.filter(user=user).first()

        if login_code and login_code.is_expired():
            return Response(
                {"error": "Code expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if login_code and login_code.verify(code):
            with transaction.atomic():
                login_code.delete()
                user.email_verified = True
                user.save(update_fields=["email_verified"])

            return send_cookies(request, user)

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
