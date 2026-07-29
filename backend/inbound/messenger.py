"""Adapter de Meta Messaging: Messenger (páginas de Facebook) e Instagram DM.

Ambos comparten la Graph API y el mismo shape de webhook (`entry[].messaging[]`
con `sender`/`recipient`), y se distinguen por el campo `object` del payload
(`page` → Messenger, `instagram` → Instagram). Único lugar que conoce el formato
de Meta para estos canales. Credenciales por entorno (config de despliegue):
MESSENGER_VERIFY_TOKEN, MESSENGER_TOKEN, MESSENGER_APP_SECRET, MESSENGER_API_BASE.
"""
import hashlib
import hmac
import logging
import os

from .models import Channel

logger = logging.getLogger(__name__)

_OBJ_CHANNEL = {"page": Channel.MESSENGER, "instagram": Channel.INSTAGRAM}


def parse_webhook(payload):
    """Normaliza el webhook a una lista de mensajes de texto:
    {channel, account_external_id (page/IG id), contact_external_id (sender id),
    contact_name, text}. Ignora echoes y no-texto."""
    out = []
    channel = _OBJ_CHANNEL.get((payload or {}).get("object"))
    if channel is None:
        return out
    for entry in payload.get("entry", []) or []:
        for ev in entry.get("messaging", []) or []:
            msg = ev.get("message") or {}
            text = msg.get("text")
            if not text or msg.get("is_echo"):
                continue
            out.append({
                "channel": channel,
                "account_external_id": (ev.get("recipient") or {}).get("id"),
                "contact_external_id": (ev.get("sender") or {}).get("id"),
                "contact_name": "",
                "text": text,
            })
    return out


def verify_signature(raw_body, header_signature):
    """Verifica X-Hub-Signature-256 con MESSENGER_APP_SECRET. Sin secret (dev),
    no se exige firma."""
    secret = os.environ.get("MESSENGER_APP_SECRET")
    if not secret:
        return True
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_signature.split("=", 1)[1])


def send_message(recipient_id, text):
    """Envía un texto por la Send API de Meta. Best-effort: loguea y no levanta."""
    token = os.environ.get("MESSENGER_TOKEN")
    if not token:
        logger.info("Messenger/IG no configurado (MESSENGER_TOKEN); no se envía")
        return False
    import httpx
    base = os.environ.get("MESSENGER_API_BASE", "https://graph.facebook.com/v21.0")
    try:
        r = httpx.post(
            f"{base}/me/messages",
            params={"access_token": token},
            json={"recipient": {"id": recipient_id},
                  "messaging_type": "RESPONSE", "message": {"text": text}},
            timeout=15)
        r.raise_for_status()
        return True
    except Exception:
        logger.warning("fallo enviando Messenger/IG a %s", recipient_id, exc_info=True)
        return False
