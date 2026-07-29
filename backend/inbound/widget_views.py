"""Widget web embebible (omnicanal, Fase 5.1 extendida).

Un visitante ANÓNIMO de la web del cliente pregunta; la deflección RAG (3B)
responde con la KB publicada de la org; si no resuelve, deja su email y se crea
un ticket (canal `widget`). La org se resuelve por la clave pública del widget
(ChannelAccount channel=widget, external_id=<clave>). Público + CORS abierto
(solo expone KB publicada y creación de ticket).
"""
import logging

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Channel, ChannelAccount
from .services import handle_inbound_message

logger = logging.getLogger(__name__)


def _cors(resp):
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Access-Control-Allow-Headers"] = "Content-Type"
    resp["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return resp


def _widget_org(key):
    acc = (ChannelAccount.objects
           .filter(channel=Channel.WIDGET, external_id=key, is_active=True)
           .select_related("organization").first())
    return acc.organization if acc else None


class _PublicWidgetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def options(self, request, *args, **kwargs):
        return _cors(Response())


class WidgetAskView(_PublicWidgetView):
    """POST /api/widget/<key>/ask/ {"query"} -> {available, resolved, answer, sources}"""

    def post(self, request, key):
        org = _widget_org(key)
        if org is None:
            return _cors(Response({"detail": "widget desconocido"}, status=404))
        query = (request.data.get("query") or "").strip()
        if not query:
            return _cors(Response({"detail": "falta la consulta"}, status=400))
        from kb.deflection import run_deflection
        data = run_deflection(org, query)
        # el widget público no expone ids/slug internos: solo títulos de fuente.
        data["sources"] = [{"title": s["title"]} for s in data.get("sources", [])]
        return _cors(Response(data))


class WidgetContactView(_PublicWidgetView):
    """POST /api/widget/<key>/contact/ {"query","email","name"} -> {reference}.

    Cuando la deflección no alcanza, el visitante deja su email y se crea el
    ticket (canal widget) para que un agente lo siga."""

    def post(self, request, key):
        if _widget_org(key) is None:
            return _cors(Response({"detail": "widget desconocido"}, status=404))
        email = (request.data.get("email") or "").strip().lower()
        query = (request.data.get("query") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not email or not query:
            return _cors(Response({"detail": "faltan email o consulta"}, status=400))
        result = handle_inbound_message(
            channel=Channel.WIDGET, account_external_id=key,
            contact_external_id=email, contact_name=name,
            subject=query[:80], text=query)
        ref = result["ticket"].reference if result else None
        return _cors(Response({"reference": ref}, status=201))


def widget_script(request):
    """GET /widget.js -> el snippet embebible (vanilla JS). Cache y CORS abierto."""
    from .widget_js import WIDGET_JS
    resp = HttpResponse(WIDGET_JS, content_type="application/javascript; charset=utf-8")
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Cache-Control"] = "public, max-age=3600"
    return resp
