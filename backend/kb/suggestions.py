"""KB auto-alimentada (Fase 5.2): al resolver un ticket, la IA propone un artículo
de KB que el admin revisa/acepta. Resiliente: cualquier fallo se loguea y se
ignora — resolver un ticket nunca depende de la IA.
"""
import logging

from .models import ArticleSuggestion

logger = logging.getLogger(__name__)


def maybe_suggest_from_ticket(ticket):
    """Genera una sugerencia de KB desde el ticket (si el plan lo habilita). Evita
    duplicar: una sola sugerencia pendiente por ticket. Devuelve la ArticleSuggestion
    creada o None."""
    try:
        from ai.services import ai_enabled, suggest_kb_article
        if not ai_enabled(ticket.organization):
            return None
        if ArticleSuggestion.objects.filter(
                source_ticket=ticket, status=ArticleSuggestion.Status.PENDING).exists():
            return None
        result = suggest_kb_article(ticket)
    except Exception:
        logger.warning("sugerencia de KB falló para ticket %s", ticket.id, exc_info=True)
        return None

    if not result:
        return None
    title, body = result
    return ArticleSuggestion.objects.create(
        organization=ticket.organization, title=title, body=body,
        source_ticket=ticket, status=ArticleSuggestion.Status.PENDING)
