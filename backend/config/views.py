from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@ensure_csrf_cookie
def csrf(request):
    """Setea la cookie `csrftoken` (legible por JS) para que el SPA la reenvíe
    como header X-CSRFToken en los métodos inseguros (CN-005). El front lo llama
    al iniciar."""
    return JsonResponse({"detail": "CSRF cookie set."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    from tenancy.branding_serializers import branding_payload
    u = request.user
    org = u.organization if u.organization_id else None
    return Response(
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "organization": org.name if org else None,
            "branding": branding_payload(org, request) if org else None,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"ok": True})