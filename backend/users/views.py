from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

from .serializers import UserCreateSerializer

User = get_user_model()


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
