from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

@database_sync_to_async
def get_user_from_jwt(token: str):
    try:
        auth = JWTAuthentication()
        validated = auth.get_validated_token(token)
        return auth.get_user(validated)
    except Exception:
        return AnonymousUser()

class JwtCookieAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        headers = dict(scope.get("headers") or [])
        cookie_header = headers.get(b"cookie", b"").decode("utf-8")

        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies[k] = v

        token = cookies.get("access")
        if token:
            scope["user"] = await get_user_from_jwt(token)

        return await super().__call__(scope, receive, send)