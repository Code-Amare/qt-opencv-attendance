from rest_framework import serializers
from .models import SiteSettings


class SiteSettingsSerializer(serializers.Serializer):
    class Meta:
        model = SiteSettings
        fields = "__all__"
