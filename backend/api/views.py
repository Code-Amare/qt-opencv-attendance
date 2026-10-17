from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import SiteSettings



class TestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "API Working!"}, status=status.HTTP_200_OK)


class SiteSettingsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        site = SiteSettings.objects.filter(id=1).first()

        if not site:
            return Response(
                {"error": "Site setting not set yet."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"site": SiteSettingsSerializer(site).data}, status=status.HTTP_200_OK
        )
