from django.apps import AppConfig


class SlaAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla"

    def ready(self):
        from . import signals  # noqa: F401
        import os
        # Sólo en el proceso principal (evita duplicado con el autoreloader de runserver).
        if os.environ.get("RUN_MAIN") == "true":
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception:
                pass
