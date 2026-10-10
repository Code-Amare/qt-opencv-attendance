from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.middleware.csrf import get_token
from .serializers import UserCreateSerializer, UserSerializer

User = get_user_model()

def get_tokens_for_user(user, request):
    refresh = RefreshToken.for_user(user)

    access_token = refresh.access_token
    csrf_token = get_token(request)

    return {
        "user": UserSerializer(user).data,
        "tokens": {
            "access": str(access_token),
            "refresh": str(refresh),
            "csrf": csrf_token,
        }
    }


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

        return Response(get_tokens_for_user(user, request), status=status.HTTP_200_OK)

