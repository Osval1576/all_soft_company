from django.db import models
from .managers import SingletonManager
from .validators import validate_image_file


class _SingletonBase(models.Model):
    objects = SingletonManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class HeroContent(_SingletonBase):
    title_es = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    subtitle_es = models.TextField(blank=True)
    subtitle_en = models.TextField(blank=True)

    primary_cta_label_es = models.CharField(max_length=50, default="Iniciar sesión")
    primary_cta_label_en = models.CharField(max_length=50, default="Sign in")
    primary_cta_url = models.CharField(max_length=200, default="/login")

    secondary_cta_label_es = models.CharField(max_length=50, default="Contactar")
    secondary_cta_label_en = models.CharField(max_length=50, default="Contact us")
    secondary_cta_url = models.CharField(max_length=200, default="#contacto")

    updated_at = models.DateTimeField(auto_now=True)


class AboutContent(_SingletonBase):
    mission_es = models.TextField(blank=True)
    mission_en = models.TextField(blank=True)
    vision_es = models.TextField(blank=True)
    vision_en = models.TextField(blank=True)
    values_es = models.TextField(blank=True)
    values_en = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class SiteSettings(_SingletonBase):
    logo = models.ImageField(
        upload_to="site/", blank=True, null=True,
        validators=[validate_image_file],
    )
    footer_text_es = models.TextField(blank=True)
    footer_text_en = models.TextField(blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    google_maps_api_key = models.CharField(max_length=100, blank=True)
