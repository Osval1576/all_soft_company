from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response(
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
            "role": u.role,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"ok": True})