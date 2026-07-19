from django.http import JsonResponse


class OrganizationMiddleware:
    """Setea request.organization y aplica fail-closed en /api/.

    - Usuario autenticado sin org y sin is_superuser -> 403 (cuenta mal provisionada).
    - Org suspendida (is_active=False) -> 403.
    - Superuser de plataforma (org=None) pasa, pero con request.organization=None:
      los helpers de scoping devuelven vacio -> no ve datos de tenants por la API.
    Exentos: /api/health/, /api/auth/ (login/refresh/logout necesitan funcionar)
    y /api/billing/webhook/ (endpoint público firmado por Stripe, sin org: el resto
    de /api/billing/ NO es exento).

    La API se autentica via JWT en cookie (config.authentication.CookieJWTAuthentication),
    no via sesion de Django: AuthenticationMiddleware pobla request.user desde la
    sesion, que para un request de API sin sesion queda anonimo aunque la cookie
    "access" sea valida. Si este middleware confiara solo en request.user quedaria
    fail-open (nunca bloquearia a nadie) para el flujo de auth real de la app. Por
    eso resuelve el usuario de API el mismo, reusando el authenticator de DRF, y
    tambien respeta request._force_auth_user (asi es como
    rest_framework.test.APIClient.force_authenticate() inyecta el usuario en los
    tests, tambien sin pasar por sesion).
    """

    EXEMPT_PREFIXES = ("/api/health/", "/api/auth/", "/api/billing/webhook/")

    def __init__(self, get_response):
        self.get_response = get_response

    def _api_user(self, request):
        forced = getattr(request, "_force_auth_user", None)
        if forced is not None:
            return forced
        if request.user.is_authenticated:
            return request.user
        from config.authentication import CookieJWTAuthentication
        try:
            result = CookieJWTAuthentication().authenticate(request)
        except Exception:
            result = None
        return result[0] if result else request.user

    def __call__(self, request):
        path = request.path
        is_api = path.startswith("/api/") and not path.startswith(self.EXEMPT_PREFIXES)
        user = self._api_user(request) if is_api else request.user
        org = getattr(user, "organization", None) if user.is_authenticated else None
        request.organization = org
        if is_api and user.is_authenticated:
            if org is None and not user.is_superuser:
                return JsonResponse({"detail": "Cuenta sin organización."}, status=403)
            if org is not None and not org.is_active:
                return JsonResponse({"detail": "Organización suspendida."}, status=403)
        return self.get_response(request)
