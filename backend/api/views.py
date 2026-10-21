from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from .models import DesktopRelease, DesktopReleaseAsset, SiteSettings
from attendance.models import AttendanceSession, Attendance
from attendance.serializers import AttendanceSerializer, AttendanceSessionSerializer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from .serializers import (
    DesktopReleaseAssetSerializer,
    DesktopReleaseSerializer,
    PublicReleaseSerializer,
    SiteSettingsSerializer,
)

User = get_user_model()


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


class ReleaseListCreateView(generics.ListCreateAPIView):
    queryset = DesktopRelease.objects.prefetch_related("assets")
    serializer_class = DesktopReleaseSerializer
    permission_classes = [IsAdminUser]


class ReleaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DesktopRelease.objects.prefetch_related("assets")
    serializer_class = DesktopReleaseSerializer
    permission_classes = [IsAdminUser]


class ReleasePublishView(APIView):

    permission_classes = [IsAdminUser]
    publish = True

    def post(self, request, pk):
        release = get_object_or_404(
            DesktopRelease.objects.prefetch_related("assets"), pk=pk
        )

        if self.publish:
            if not release.assets.exists():
                return Response(
                    {"error": "Add at least one download before publishing."},
                    status=400,
                )
            if not release.is_published:
                release.is_published = True
                release.published_at = timezone.now()
        elif release.is_published:
            release.is_published = False
            release.published_at = None

        release.save(update_fields=["is_published", "published_at", "updated_at"])
        return Response(DesktopReleaseSerializer(release).data)


class AssetListCreateView(generics.ListCreateAPIView):

    serializer_class = DesktopReleaseAssetSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = DesktopReleaseAsset.objects.select_related("release")
        release_id = self.request.query_params.get("release")
        if release_id and release_id.isdigit():
            qs = qs.filter(release_id=release_id)
        return qs.order_by("release_id", "platform", "architecture")


class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DesktopReleaseAsset.objects.select_related("release")
    serializer_class = DesktopReleaseAssetSerializer
    permission_classes = [IsAdminUser]


def latest_published_release():
    return (
        DesktopRelease.objects.filter(is_published=True)
        .prefetch_related("assets")
        .order_by("-published_at", "-created_at")
        .first()
    )


class LatestReleaseView(APIView):

    authentication_classes = []  # a stale JWT must not cause a 401 here
    permission_classes = [AllowAny]

    def get(self, request):
        release = latest_published_release()
        if release is None:
            return Response({"error": "No release is available yet."}, status=404)
        return Response(PublicReleaseSerializer(release).data)


class LatestDownloadView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        platform = request.query_params.get("platform", "windows")
        arch = request.query_params.get("arch", "x64")

        release = latest_published_release()
        asset = (
            release.assets.filter(platform=platform, architecture=arch).first()
            if release
            else None
        )
        if asset is None:
            return Response({"error": "No download for that platform."}, status=404)
        return HttpResponseRedirect(asset.download_url)


class HomeStatsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale JWT must not cause a 401 here

    def get(self, request):
        data = cache.get("home_stats")
        if data is None:
            data = self.build()
            cache.set("home_stats", data, 60)
        return Response(data)

    def build(self):
        A = Attendance.Status

        counts = Attendance.objects.aggregate(
            present=Count("id", filter=Q(status=A.PRESENT)),
            late=Count("id", filter=Q(status=A.LATE)),
            absent=Count("id", filter=Q(status=A.ABSENT)),
        )

        return {
            "sessions": AttendanceSession.objects.exclude(
                status=AttendanceSession.Status.CANCELLED
            ).count(),
            "enrolled": User.objects.filter(is_staff=False)
            .exclude(face_embeddings__isnull=True)
            .count(),
            **counts,
        }
