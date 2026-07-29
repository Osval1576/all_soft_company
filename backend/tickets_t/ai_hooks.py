"""Hooks de IA sobre el ciclo de vida del ticket (Fase 2B).

Escalada de prioridad por sentimiento: cuando el cliente manda un mensaje que
denota frustración/urgencia, la IA sugiere una prioridad y — si es mayor a la
actual — se sube (nunca se baja). Resiliente por diseño: cualquier fallo del
servicio de IA se loguea y se ignora; el chat/ticket nunca depende de la IA.
"""
import logging

from .models import Ticket, TicketEvent

logger = logging.getLogger(__name__)

# Orden de severidad para la comparación "nunca bajar".
_PRIORITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "URGENT": 3}


def apply_auto_triage(ticket):
    """1B: al crear, la IA sugiere la prioridad (si el plan lo habilita). Sube o
    cambia la prioridad y registra el evento. Resiliente: nunca levanta."""
    try:
        from ai import services as ai_services
        if not ai_services.ai_enabled(ticket.organization):
            return None
        suggested = ai_services.triage_priority(ticket)
    except Exception:
        logger.warning("auto-triage IA falló para ticket %s", ticket.id, exc_info=True)
        return None
    if not suggested or suggested == ticket.prioridad:
        return None
    old = ticket.prioridad
    ticket.prioridad = suggested
    ticket.save(update_fields=["prioridad"])
    TicketEvent.objects.create(
        ticket=ticket, kind="priority_changed", actor=None,
        payload={"from": old, "to": suggested, "auto": True})
    return suggested


# --- entrypoints para ejecución async (toman id y re-fetchean) ---------------

def run_auto_triage(ticket_id):
    t = Ticket.objects.filter(id=ticket_id).select_related("organization").first()
    if t:
        apply_auto_triage(t)


def run_sentiment_escalation(ticket_id, message_text):
    t = Ticket.objects.filter(id=ticket_id).select_related("organization").first()
    if t:
        apply_sentiment_escalation(t, message_text)


def run_sentiment_escalation_for_customer(user_id, ticket_id, message_text):
    """Escala solo si el autor del mensaje es CUSTOMER (para el chat, donde también
    escriben agentes)."""
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.filter(id=user_id).first()
    if not user or getattr(user, "role", None) != "CUSTOMER":
        return
    run_sentiment_escalation(ticket_id, message_text)


def apply_sentiment_escalation(ticket, message_text):
    """Sube la prioridad del ticket si el sentimiento del mensaje amerita más
    urgencia. Nunca la baja ni la mantiene. Devuelve la nueva prioridad si
    cambió, o None. Resiliente: nunca levanta.
    """
    try:
        from ai import services as ai_services
        if not ai_services.ai_enabled(ticket.organization):
            return None
        suggested = ai_services.assess_sentiment_priority(ticket, message_text)
    except Exception:
        logger.warning("sentiment-escalation IA falló para ticket %s", ticket.id, exc_info=True)
        return None

    if not suggested:
        return None
    cur_rank = _PRIORITY_RANK.get(ticket.prioridad, _PRIORITY_RANK["MEDIUM"])
    new_rank = _PRIORITY_RANK.get(suggested, cur_rank)
    if new_rank <= cur_rank:
        return None  # nunca baja ni mantiene

    old = ticket.prioridad
    ticket.prioridad = suggested
    ticket.save(update_fields=["prioridad"])
    # Evento auditable, sin notificación (actor de sistema = None).
    TicketEvent.objects.create(
        ticket=ticket, kind="priority_changed", actor=None,
        payload={"from": old, "to": suggested, "auto": True, "reason": "sentiment"},
    )
    return suggested
