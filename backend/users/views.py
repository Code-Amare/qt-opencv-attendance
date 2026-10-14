import io
import uuid
import numpy as np
from axes.utils import reset
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.middleware.csrf import get_token
from django.db import transaction
from .serializers import UserCreateSerializer, UserSerializer

User = get_user_model()

def send_cookies(request, user):
    refresh_token = RefreshToken.for_user(user)

    access_token = refresh_token.access_token
    csrf_token = get_token(request)

    response = Response({
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
            return Response({"error": "Username and Password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(username=username_or_email).first()
        if not user:
            user = User.objects.filter(email=username_or_email).first()
            if not user:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        return send_cookies(request, user)

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
            embeddings=np.concatenate(vectors) if vectors else np.empty((0, 512), np.float32),
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
            return Response({"error": "Invalid User id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            embedding = np.asarray(face_embedding, dtype=np.float32)

            if embedding.shape != (512,):
                raise ValueError("Embedding must contain exactly 512 values")

            if not np.isfinite(embedding).all():
                raise ValueError("Embedding contains invalid numbers")

            user.set_embeddings(embedding)
            user.embeddings_updated_at = timezone.now()
            user.save(update_fields=[
                "face_embeddings",
                "embeddings_updated_at",
            ])

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

        print(google_user)

        email = google_user.get("email")
        first_name = google_user.get("given_name", "guest")
        last_name = google_user.get("family_name", "")
        google_id = google_user.get("sub")
        email_verified = google_user.get("email_verified", False)

        if not email_verified:
            return Response(
                {"error": "Google email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()

        if not user:
            username = first_name + "-" + last_name
            if User.objects.filter(username=username).exists():
                username += uuid.uuid4().hex[0:5]
            user = User.objects.create(
                username=username,
                email=email,
            )
            user.set_unusable_password()
            user.save()

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



