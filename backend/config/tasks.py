"""Task genérica de Celery: ejecuta una función por su ruta punteada.

Permite mantener la interfaz `run_async(fn, *args)` sin registrar una task por
cada hook: se encola el path (p. ej. "tickets_t.ai_hooks.run_auto_triage") + los
args (ids/strings, JSON-serializables) y el worker importa y llama.
"""
import importlib
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="config.run_task", acks_late=True)
def run_task(dotted_path, args=None, kwargs=None):
    module_path, _, attr = dotted_path.rpartition(".")
    try:
        fn = getattr(importlib.import_module(module_path), attr)
    except (ImportError, AttributeError):
        logger.exception("run_task: no se pudo resolver %s", dotted_path)
        return
    fn(*(args or []), **(kwargs or {}))
