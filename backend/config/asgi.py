import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 1) Primero inicializa Django (carga apps)
django_asgi_app = get_asgi_application()

# 2) Después importa cosas que dependen de modelos/apps
from tickets_t.routing import websocket_urlpatterns  # noqa: E402
from .ws_auth import JwtCookieAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtCookieAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    }
)