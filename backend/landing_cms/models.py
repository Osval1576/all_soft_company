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


class _Ordered(models.Model):
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class Feature(_Ordered):
    icon = models.CharField(max_length=50)
    title_es = models.CharField(max_length=100)
    title_en = models.CharField(max_length=100)
    description_es = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    def __str__(self):
        return self.title_es or self.title_en


class TeamMember(_Ordered):
    photo = models.ImageField(
        upload_to="team/", blank=True, null=True,
        validators=[validate_image_file],
    )
    name = models.CharField(max_length=100)
    role_es = models.CharField(max_length=100, blank=True)
    role_en = models.CharField(max_length=100, blank=True)
    bio_es = models.TextField(blank=True)
    bio_en = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Location(_Ordered):
    class Type(models.TextChoices):
        SUCURSAL = "SUCURSAL", "Sucursal"
        OFICINA = "OFICINA", "Oficina"
        CENTRO = "CENTRO", "Centro de servicio"

    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    hours_es = models.CharField(max_length=200, blank=True)
    hours_en = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(
        upload_to="locations/", blank=True, null=True,
        validators=[validate_image_file],
    )
    description_es = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.OFICINA)

    def __str__(self):
        return self.name
