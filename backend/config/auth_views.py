from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer


COOKIE_ACCESS_NAME = "access"
COOKIE_REFRESH_NAME = "refresh"

def cookie_settings():
    # secure=True en prod (DEBUG=false), False en dev http. SameSite Lax alcanza
    # porque en prod el front es same-origin detrás de Nginx.
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": "Lax",
        "path": "/",
    }

class LoginCookieView(APIView):
    permission_classes = [AllowAny]
    # No autenticar por la cookie `access`: este endpoint valida por
    # usuario/contraseña. Si el navegador manda un access vencido de una sesión
    # previa, no debe impedir re-loguearse.
    authentication_classes = []

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data["access"]
        refresh = serializer.validated_data["refresh"]

        resp = Response({"ok": True}, status=status.HTTP_200_OK)
        opts = cookie_settings()

        resp.set_cookie(COOKIE_ACCESS_NAME, access, **opts)
        resp.set_cookie(COOKIE_REFRESH_NAME, refresh, **opts)
        return resp


class RefreshCookieView(APIView):
    permission_classes = [AllowAny]
    # Refresca usando la cookie `refresh`; el access vencido es justamente el
    # motivo del refresh, así que no debe autenticarse contra él.
    authentication_classes = []

    def post(self, request):
        refresh = request.COOKIES.get(COOKIE_REFRESH_NAME)
        if not refresh:
            return Response({"detail": "No refresh cookie."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": refresh})
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data["access"]

        resp = Response({"ok": True}, status=status.HTTP_200_OK)
        opts = cookie_settings()
        resp.set_cookie(COOKIE_ACCESS_NAME, access, **opts)
        return resp


class LogoutView(APIView):
    # Logout solo borra cookies: debe funcionar siempre, incluso con una sesión
    # ya vencida (sin autenticar contra la cookie `access`).
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        resp = Response({"ok": True}, status=status.HTTP_200_OK)
        resp.delete_cookie(COOKIE_ACCESS_NAME, path="/")
        resp.delete_cookie(COOKIE_REFRESH_NAME, path="/")
        return resp