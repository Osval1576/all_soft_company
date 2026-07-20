from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


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
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
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