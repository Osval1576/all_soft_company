from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.scoping import org_tickets
from tickets_t.permissions import can_access_ticket

from . import services
from .gateway import AiNotConfigured

_NOT_CONFIGURED = Response(
    {"detail": "El servicio de IA no está configurado. Contactá al administrador."},
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
)


class _BaseTicketAiView(APIView):
    """Gating común de las features de IA sobre un ticket.

    AGENT/ADMIN con acceso al ticket + plan pago (Pro/Business). Un CUSTOMER o un
    plan free reciben 403; un ticket de otra org, 404 (sin fuga de existencia).
    Las subclases implementan `run(ticket)` con la llamada de IA concreta.
    """
    permission_classes = [IsAuthenticated]

    def _resolve(self, request, ticket_id):
        """Devuelve (ticket, None) o (None, respuesta_de_error)."""
        user = request.user
        org = getattr(request, "organization", None) or getattr(user, "organization", None)

        if getattr(user, "role", None) not in ("AGENT", "ADMIN"):
            return None, Response(
                {"detail": "Solo agentes o administradores pueden usar la IA."},
                status=status.HTTP_403_FORBIDDEN)

        if not services.ai_enabled(org):
            return None, Response(
                {"detail": "La asistencia con IA está disponible en los planes Pro y Business.",
                 "upsell": True},
                status=status.HTTP_403_FORBIDDEN)

        ticket = get_object_or_404(org_tickets(org), id=ticket_id)
        if not can_access_ticket(user, ticket):
            return None, Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return ticket, None

    def post(self, request, ticket_id):
        ticket, err = self._resolve(request, ticket_id)
        if err is not None:
            return err
        try:
            return Response(self.run(ticket))
        except AiNotConfigured:
            return _NOT_CONFIGURED

    def run(self, ticket):  # pragma: no cover - implementado por subclases
        raise NotImplementedError


class TicketAiDraftView(_BaseTicketAiView):
    """POST /api/ai/tickets/<id>/draft/ -> {"draft": "..."}"""

    def run(self, ticket):
        return {"draft": services.draft_reply(ticket)}


class TicketAiSummaryView(_BaseTicketAiView):
    """POST /api/ai/tickets/<id>/summary/ -> {"summary": "..."}

    Resume el hilo del ticket para ponerse al día al reasignar/escalar (2A).
    """

    def run(self, ticket):
        return {"summary": services.summarize_ticket(ticket)}
