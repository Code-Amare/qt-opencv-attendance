from django.db import models
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100)
    site_logo = CloudinaryField("logos", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings instance is allowed.")

        return super().save(*args, **kwargs)
