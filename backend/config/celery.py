"""App de Celery para AllSafe.

Broker por defecto: REDIS_URL (el mismo Redis que usan Channels/cache). Se activa
por despliegue con AI_TASK_QUEUE=celery; sin eso, run_async cae al thread daemon.
El worker se corre aparte: `celery -A config worker -l info`
(en Windows dev: agregar `--pool=solo`).
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("allsafe")
# Toma la config CELERY_* de Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")
# Descubre tasks.py de las apps instaladas.
app.autodiscover_tasks()
# Registro explícito del dispatcher genérico: `config` NO es una app de
# INSTALLED_APPS, así que autodiscover no lo alcanza. Sin este import el worker no
# registraría `config.run_task` (lo que usa run_async) y rechazaría los mensajes
# encolados ("Received unregistered task"). El import perezoso evita ciclos al
# cargar celery.py desde config/__init__.py.
from config import tasks as _tasks  # noqa: E402,F401
