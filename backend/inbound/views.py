import json
import logging
import os

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import email as email_channel
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


class EmailWebhookView(APIView):
    """Webhook de email entrante (email-to-ticket).

    Un servicio de inbound-parse (SendGrid/Mailgun/Postmark) POSTea el mail
    parseado. Se convierte en ticket; si la KB lo resuelve, se responde por email.
    Seguridad opcional: si INBOUND_EMAIL_SECRET está seteado, se exige que
    coincida el token (query `?token=` o header X-Inbound-Token).
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = os.environ.get("INBOUND_EMAIL_SECRET")
        if secret:
            token = request.query_params.get("token") or request.headers.get("X-Inbound-Token")
            if token != secret:
                return Response({"detail": "token inválido"}, status=403)

        m = email_channel.parse_inbound(request.data)
        if not m["account_external_id"] or not m["contact_external_id"]:
            return Response({"detail": "faltan from/to"}, status=400)

        try:
            result = handle_inbound_message(
                channel=Channel.EMAIL,
                account_external_id=m["account_external_id"],
                contact_external_id=m["contact_external_id"],
                contact_name=m["contact_name"],
                subject=m["subject"],
                text=m["text"])
        except Exception:
            logger.exception("fallo procesando email entrante")
            return Response({"status": "error"}, status=200)  # el proveedor no reintenta en loop

        if result and result.get("reply"):
            subject = m["subject"] or "tu consulta"
            email_channel.send_reply(m["contact_external_id"], f"Re: {subject}", result["reply"])
        return Response({"status": "ok"})
