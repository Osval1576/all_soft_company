from django.conf import settings
from django.core.checks import Error, register

# Hosts que consideramos "de desarrollo/test": si ALLOWED_HOSTS solo tiene estos
# (o está vacío), no estamos en producción.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "testserver"}


def _looks_like_production():
    hosts = [h for h in getattr(settings, "ALLOWED_HOSTS", []) if h]
    return any(h not in _LOCAL_HOSTS for h in hosts)


@register()
def production_hardening_check(app_configs, **kwargs):
    """Red de seguridad que corre SIEMPRE (no solo con --deploy).

    Si ALLOWED_HOSTS incluye un host de producción, la app se niega a arrancar
    con configuración insegura por defecto: DEBUG=True (CN-004) o credenciales
    de BD por defecto root/root (CN-006). En dev (solo hosts locales) no dispara.
    """
    errors = []
    if not _looks_like_production():
        return errors
    if settings.DEBUG:
        errors.append(Error(
            "DJANGO_DEBUG=false es obligatorio cuando ALLOWED_HOSTS incluye un "
            "host de producción.",
            hint="Definí DJANGO_DEBUG=false en el entorno de producción.",
            id="config.E010",
        ))
    db = settings.DATABASES.get("default", {})
    if (db.get("USER"), db.get("PASSWORD")) == ("root", "root"):
        errors.append(Error(
            "Credenciales de base de datos por defecto (root/root) no están "
            "permitidas en producción.",
            hint="Definí DB_USER y DB_PASSWORD con credenciales dedicadas.",
            id="config.E011",
        ))
    return errors


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
