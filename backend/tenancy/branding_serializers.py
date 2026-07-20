from rest_framework import serializers

from .models import OrganizationBranding

_MAX_LOGO_BYTES = 512 * 1024
_ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}


class BrandingSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    effective_display_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationBranding
        fields = ["display_name", "accent_color", "logo", "default_dark",
                  "logo_url", "effective_display_name"]
        extra_kwargs = {"logo": {"write_only": True, "required": False}}

    def get_logo_url(self, obj):
        if not obj.pk or not obj.logo:
            return None
        request = self.context.get("request")
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url

    def get_effective_display_name(self, obj):
        return obj.effective_display_name if obj.pk else \
            self.context["organization"].name

    def validate_logo(self, value):
        if value is None:
            return value
        if value.size > _MAX_LOGO_BYTES:
            raise serializers.ValidationError("El logo no puede superar 512 KB.")
        fmt = getattr(getattr(value, "image", None), "format", None)
        if fmt not in _ALLOWED_FORMATS:
            raise serializers.ValidationError("Formato no soportado (usá PNG, JPEG o WebP).")
        return value


def branding_payload(org, request):
    """Payload público mínimo o None si no aplica (sin plan pago o sin branding)."""
    from .branding_services import branding_enabled
    if not branding_enabled(org):
        return None
    branding = getattr(org, "branding", None)
    if branding is None:
        return None
    logo_url = None
    if branding.logo:
        logo_url = request.build_absolute_uri(branding.logo.url) if request else branding.logo.url
    return {
        "display_name": branding.effective_display_name,
        "accent_color": branding.accent_color,
        "logo_url": logo_url,
        "default_dark": branding.default_dark,
    }
