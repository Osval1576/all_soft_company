from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.scoping import org_tickets
from tickets_t.permissions import can_access_ticket, IsAdmin

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


class InsightsView(APIView):
    """POST /api/ai/insights/ -> {"insights": "...", "snapshot": {...}}

    Análisis ejecutivo de la operación de soporte de la org (Fase 4): tendencias,
    temas recurrentes y acciones recomendadas sobre métricas/CSAT. Solo ADMIN del
    tenant + plan pago. 503 si la IA no está configurada.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        org = getattr(request, "organization", None)
        if not services.ai_enabled(org):
            return Response(
                {"detail": "El análisis con IA está disponible en los planes Pro y Business.",
                 "upsell": True},
                status=status.HTTP_403_FORBIDDEN)

        from metrics.services import insights_snapshot, _parse_window
        from sla.calendar_engine import get_calendar
        window = _parse_window(request)
        snapshot = insights_snapshot(org, window, get_calendar(org))
        try:
            text = services.generate_insights(snapshot)
        except AiNotConfigured:
            return _NOT_CONFIGURED
        return Response({"insights": text, "snapshot": snapshot})


class TranslateView(APIView):
    """POST /api/ai/translate/ {"text": "...", "target_lang": "es"} -> {"translated"}

    Traducción para el agente (multilingüe, Fase 5.3): traducir el mensaje del
    cliente al español, o su respuesta al idioma del cliente. AGENT/ADMIN + plan.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        org = getattr(request, "organization", None) or getattr(user, "organization", None)
        if getattr(user, "role", None) not in ("AGENT", "ADMIN"):
            return Response({"detail": "Solo agentes o administradores pueden usar la IA."},
                            status=status.HTTP_403_FORBIDDEN)
        if not services.ai_enabled(org):
            return Response({"detail": "La traducción con IA está disponible en los planes Pro y Business.",
                             "upsell": True}, status=status.HTTP_403_FORBIDDEN)
        text = (request.data.get("text") or "").strip()
        target = (request.data.get("target_lang") or "es").strip()
        if not text:
            return Response({"detail": "Falta el texto."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            translated = services.translate_text(text, target)
        except AiNotConfigured:
            return _NOT_CONFIGURED
        return Response({"translated": translated})
