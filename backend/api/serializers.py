from rest_framework import serializers
from .models import SiteSettings


class SiteSettingsSerializer:
    class Meta:
        model = SiteSettings
        fields = "__all__"
