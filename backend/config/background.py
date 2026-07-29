"""Ejecución en background de tareas fire-and-forget (hooks de IA).

Mismo enfoque que el envío async de emails del proyecto: un thread daemon, sin
sumar infra (Celery/colas). Bajo tests (`AI_ASYNC=False`) corre inline, así los
asserts síncronos siguen valiendo. En runtime desacopla la IA del request/webhook.

Las tareas deben tomar IDs (no instancias) y re-fetchear: el thread tiene su
propia conexión a la DB, y así se evita estado en memoria de otro thread.
"""
import logging
import threading

from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)


def run_async(fn, *args, **kwargs):
    """Ejecuta fn(*args, **kwargs) fuera del request, en cascada según config:

    - AI_ASYNC=False (tests)            -> inline.
    - AI_TASK_QUEUE="celery" (prod)     -> se encola en Celery (worker aparte).
    - si no                            -> thread daemon (dev/single-process).

    Los args deben ser JSON-serializables (ids/strings) para el path de Celery.
    Resiliente: si el encolado falla, cae al thread.
    """
    if not getattr(settings, "AI_ASYNC", True):
        fn(*args, **kwargs)
        return

    if getattr(settings, "AI_TASK_QUEUE", "") == "celery":
        try:
            from config.tasks import run_task
            path = f"{fn.__module__}.{fn.__name__}"
            run_task.delay(path, list(args), dict(kwargs))
            return
        except Exception:
            logger.warning("no se pudo encolar en Celery; fallback a thread", exc_info=True)

    def _wrap():
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("tarea async falló: %s", getattr(fn, "__name__", fn))
        finally:
            close_old_connections()

    threading.Thread(target=_wrap, daemon=True).start()
