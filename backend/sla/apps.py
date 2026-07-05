from django.apps import AppConfig


class SlaAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla"

    def ready(self):
        from . import signals  # noqa: F401
