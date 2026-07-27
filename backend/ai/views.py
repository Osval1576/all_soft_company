from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.scoping import org_tickets
from tickets_t.permissions import can_access_ticket

from . import services
from .gateway import AiNotConfigured


class TicketAiDraftView(APIView):
    """POST /api/ai/tickets/<id>/draft/ -> {"draft": "..."}

    Genera un borrador de respuesta para el agente. Gateado a AGENT/ADMIN con
    acceso al ticket + plan pago (Pro/Business). Un CUSTOMER o un plan free
    reciben 403; un ticket de otra org, 404 (sin fuga de existencia).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        user = request.user
        org = getattr(request, "organization", None) or getattr(user, "organization", None)

        if getattr(user, "role", None) not in ("AGENT", "ADMIN"):
            return Response({"detail": "Solo agentes o administradores pueden usar la IA."},
                            status=status.HTTP_403_FORBIDDEN)

        if not services.ai_enabled(org):
            return Response({"detail": "La asistencia con IA está disponible en los planes Pro y Business.",
                             "upsell": True},
                            status=status.HTTP_403_FORBIDDEN)

        ticket = get_object_or_404(org_tickets(org), id=ticket_id)
        if not can_access_ticket(user, ticket):
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            draft = services.draft_reply(ticket)
        except AiNotConfigured:
            return Response(
                {"detail": "El servicio de IA no está configurado. Contactá al administrador."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"draft": draft})
