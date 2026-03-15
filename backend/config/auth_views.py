from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer


COOKIE_ACCESS_NAME = "access"
COOKIE_REFRESH_NAME = "refresh"

def cookie_settings():
    # En local normalmente NO hay https, entonces secure=False.
    # En producción: secure=True y probablemente SameSite=None.
    return {
        "httponly": True,
        "secure": False,
        "samesite": "Lax",
        "path": "/",
    }

class LoginCookieView(APIView):
    permission_classes = [AllowAny]

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
    def post(self, request):
        resp = Response({"ok": True}, status=status.HTTP_200_OK)
        resp.delete_cookie(COOKIE_ACCESS_NAME, path="/")
        resp.delete_cookie(COOKIE_REFRESH_NAME, path="/")
        return resp