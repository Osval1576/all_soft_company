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
app.autodiscover_tasks()
