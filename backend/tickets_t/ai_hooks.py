"""Hooks de IA sobre el ciclo de vida del ticket (Fase 2B).

Escalada de prioridad por sentimiento: cuando el cliente manda un mensaje que
denota frustración/urgencia, la IA sugiere una prioridad y — si es mayor a la
actual — se sube (nunca se baja). Resiliente por diseño: cualquier fallo del
servicio de IA se loguea y se ignora; el chat/ticket nunca depende de la IA.
"""
import logging

from .models import TicketEvent

logger = logging.getLogger(__name__)

# Orden de severidad para la comparación "nunca bajar".
_PRIORITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "URGENT": 3}


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
