"""API admin de la configuración de IA por tenant (Fase 0 — guardrails).

El ADMIN de la org ve/edita su `OrgAiSettings` (opt-in + topes de rate limit).
Scoped por org: siempre opera sobre la config de la organización del request.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets_t.permissions import IsAdmin

from .models import OrgAiSettings
from .serializers import OrgAiSettingsSerializer


class OrgAiSettingsView(APIView):
    """GET/PATCH /api/admin/ai/settings/ — config de IA de la org del admin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _row(self, request):
        org = getattr(request, "organization", None)
        obj, _ = OrgAiSettings.objects.get_or_create(organization=org)
        return obj

    def get(self, request):
        return Response(OrgAiSettingsSerializer(self._row(request)).data)

    def patch(self, request):
        obj = self._row(request)
        ser = OrgAiSettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
