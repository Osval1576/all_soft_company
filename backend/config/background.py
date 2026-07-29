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
    """Corre fn(*args, **kwargs) en un thread daemon (o inline si AI_ASYNC=False).
    Resiliente: loguea excepciones y cierra la conexión DB del thread al terminar."""
    if not getattr(settings, "AI_ASYNC", True):
        fn(*args, **kwargs)
        return

    def _wrap():
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("tarea async falló: %s", getattr(fn, "__name__", fn))
        finally:
            close_old_connections()

    threading.Thread(target=_wrap, daemon=True).start()
