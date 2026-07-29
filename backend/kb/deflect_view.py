from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .deflection import run_deflection


class DeflectView(APIView):
    """POST /api/kb/deflect/ {"query": "..."} -> respuesta desde la KB de la org.

    Antes de abrir un ticket, intenta resolver la consulta con los artículos
    PUBLICADOS de la organización del usuario. Gateado por plan; resiliente
    (si la IA no está o falla, devuelve resolved=False para seguir al ticket).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = getattr(request, "organization", None) or getattr(request.user, "organization", None)
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"detail": "Falta la consulta."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(run_deflection(org, query))
