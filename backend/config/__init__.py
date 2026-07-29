# Expone la app de Celery para que las tasks se registren al iniciar Django.
# Guardado: si Celery no está instalado (deploy sin cola), no rompe nada.
try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except Exception:  # pragma: no cover
    pass
