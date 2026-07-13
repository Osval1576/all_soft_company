from django.conf import settings
from django.core.checks import Error, register


@register(deploy=True)
def prod_settings_check(app_configs, **kwargs):
    """Con DEBUG=false, exige configuración de producción real."""
    errors = []
    if settings.DEBUG:
        return errors
    placeholder = getattr(settings, "DEV_SECRET_KEY_PLACEHOLDER", "")
    if not settings.SECRET_KEY or settings.SECRET_KEY == placeholder:
        errors.append(Error(
            "DJANGO_SECRET_KEY es obligatoria (y distinta del placeholder) con DJANGO_DEBUG=false.",
            id="config.E001",
        ))
    if not settings.ALLOWED_HOSTS:
        errors.append(Error(
            "DJANGO_ALLOWED_HOSTS es obligatoria con DJANGO_DEBUG=false.",
            id="config.E002",
        ))
    return errors
