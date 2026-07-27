from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


def _enforce_csrf(request):
    """Corre el check CSRF de Django (double-submit cookie) igual que hace
    SessionAuthentication de DRF. Necesario porque la auth por cookie JWT viaja
    automáticamente en cada request: sin esto sería vulnerable a CSRF (CN-005)."""
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """
    Lee el access token desde la cookie 'access' en vez del header Authorization.
    Al autenticar por cookie, exige token CSRF en métodos inseguros (POST/PUT/
    PATCH/DELETE); los métodos seguros (GET/HEAD/OPTIONS) quedan exentos.
    """
    def authenticate(self, request):
        raw_token = request.COOKIES.get("access")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        _enforce_csrf(request)
        return user, validated_token
