import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SlaAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sla"

    def ready(self):
        from . import signals  # noqa: F401
        import os
        # Thread in-process sólo en dev (runserver): en prod el scheduler es un
        # servicio dedicado (manage.py check_sla --loop) y aquí va MODE=off.
        mode = os.environ.get("SLA_SCHEDULER_MODE", "thread")
        if mode == "thread" and os.environ.get("RUN_MAIN") == "true":
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception:
                logger.exception("no se pudo iniciar el scheduler de SLA")
