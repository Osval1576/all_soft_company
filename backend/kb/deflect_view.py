import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .search import search_articles

logger = logging.getLogger(__name__)


def _payload(available, resolved=False, answer=None, sources=None):
    return {
        "available": available,
        "resolved": resolved,
        "answer": answer,
        "sources": sources or [],
    }


class DeflectView(APIView):
    """POST /api/kb/deflect/ {"query": "..."} -> respuesta desde la KB de la org.

    Antes de abrir un ticket, intenta resolver la consulta con los artículos
    PUBLICADOS de la organización del usuario (retrieval + generación restringida
    a esos artículos). Gateado por plan (Pro/Business). Resiliente: si la IA no
    está disponible o falla, devuelve resolved=False para que el flujo siga a la
    creación del ticket — nunca bloquea al cliente.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org = getattr(request, "organization", None) or getattr(request.user, "organization", None)
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"detail": "Falta la consulta."}, status=status.HTTP_400_BAD_REQUEST)

        from ai.services import ai_enabled, answer_from_kb
        if not ai_enabled(org):
            return Response(_payload(available=False))

        articles = search_articles(org, query)
        if not articles:
            return Response(_payload(available=True))

        try:
            answer = answer_from_kb(query, articles)
        except Exception:
            logger.warning("deflección IA falló para org %s",
                           getattr(org, "id", None), exc_info=True)
            return Response(_payload(available=True))

        if not answer:
            return Response(_payload(available=True))

        sources = [{"id": a.id, "title": a.title, "slug": a.slug} for a in articles]
        return Response(_payload(available=True, resolved=True, answer=answer, sources=sources))
