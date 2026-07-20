from django.core.validators import RegexValidator
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=12, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.slug = (self.slug or "").upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="El color debe ser hex de 6 dígitos, ej. #0038FF.",
)


class OrganizationBranding(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="branding"
    )
    display_name = models.CharField(max_length=80, blank=True)
    accent_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR])
    logo = models.ImageField(upload_to="branding/logos/", blank=True, null=True)
    default_dark = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def effective_display_name(self):
        return self.display_name or self.organization.name

    def __str__(self):
        return f"Branding · {self.organization.name}"
