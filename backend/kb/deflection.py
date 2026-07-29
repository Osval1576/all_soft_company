"""Lógica de deflección reutilizable (3B): resolver una consulta con la KB
publicada de una org. La usan el endpoint autenticado (`DeflectView`) y el
widget web público. Resiliente: nunca levanta.
"""
import logging

from .search import search_articles

logger = logging.getLogger(__name__)


def payload(available, resolved=False, answer=None, sources=None):
    return {"available": available, "resolved": resolved,
            "answer": answer, "sources": sources or []}


def run_deflection(org, query):
    """Intenta resolver `query` con la KB publicada de `org`. Devuelve el payload
    {available, resolved, answer, sources}. Gateado por plan; resiliente."""
    from ai.services import ai_enabled, answer_from_kb
    from ai.ratelimit import allow_public
    if not ai_enabled(org):
        return payload(available=False)

    articles = search_articles(org, query)
    if not articles:
        return payload(available=True)

    # Guardrail de costo/abuso: el endpoint público corre una llamada de IA por
    # consulta. Si la org superó su tope horario, no gastamos IA y degradamos a
    # "no resuelto" (escala a un humano).
    if not allow_public(org):
        logger.info("deflección pública rate-limited para org %s", getattr(org, "id", None))
        return payload(available=True)

    try:
        answer = answer_from_kb(query, articles, org=org)
    except Exception:
        logger.warning("deflección IA falló para org %s", getattr(org, "id", None), exc_info=True)
        return payload(available=True)

    if not answer:
        return payload(available=True)

    sources = [{"id": a.id, "title": a.title, "slug": a.slug} for a in articles]
    return payload(available=True, resolved=True, answer=answer, sources=sources)
