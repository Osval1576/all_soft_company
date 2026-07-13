from django.http import JsonResponse


class OrganizationMiddleware:
    """Setea request.organization y aplica fail-closed en /api/.

    - Usuario autenticado sin org y sin is_superuser -> 403 (cuenta mal provisionada).
    - Org suspendida (is_active=False) -> 403.
    - Superuser de plataforma (org=None) pasa, pero con request.organization=None:
      los helpers de scoping devuelven vacio -> no ve datos de tenants por la API.
    Exentos: /api/health/ y /api/auth/ (login/refresh/logout necesitan funcionar).
    """

    EXEMPT_PREFIXES = ("/api/health/", "/api/auth/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = getattr(request.user, "organization", None) if request.user.is_authenticated else None
        request.organization = org
        path = request.path
        if path.startswith("/api/") and not path.startswith(self.EXEMPT_PREFIXES):
            if request.user.is_authenticated:
                if org is None and not request.user.is_superuser:
                    return JsonResponse({"detail": "Cuenta sin organización."}, status=403)
                if org is not None and not org.is_active:
                    return JsonResponse({"detail": "Organización suspendida."}, status=403)
        return self.get_response(request)
