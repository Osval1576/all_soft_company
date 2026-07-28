import json
import logging
import os

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import whatsapp
from .models import Channel
from .services import handle_inbound_message

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """Webhook de WhatsApp Cloud API.

    GET  -> verificación del webhook (Meta manda hub.challenge al configurarlo).
    POST -> mensajes entrantes: se procesan y, si la KB los resuelve, se responde
            automáticamente por WhatsApp.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        expected = os.environ.get("WHATSAPP_VERIFY_TOKEN")
        if mode == "subscribe" and expected and token == expected:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("forbidden", status=403)

    def post(self, request):
        if not whatsapp.verify_signature(request.body,
                                         request.headers.get("X-Hub-Signature-256")):
            return Response({"detail": "firma inválida"}, status=403)
        try:
            payload = json.loads(request.body or b"{}")
        except ValueError:
            return Response({"detail": "payload inválido"}, status=400)

        for m in whatsapp.parse_webhook(payload):
            try:
                result = handle_inbound_message(
                    channel=Channel.WHATSAPP,
                    account_external_id=m["account_external_id"],
                    contact_external_id=m["contact_external_id"],
                    contact_name=m["contact_name"],
                    text=m["text"])
            except Exception:
                logger.exception("fallo procesando mensaje entrante de WhatsApp")
                continue
            if result and result.get("reply"):
                whatsapp.send_message(m["contact_external_id"], result["reply"])

        # Meta espera 200 rápido siempre (reintenta ante no-2xx).
        return Response({"status": "ok"})
