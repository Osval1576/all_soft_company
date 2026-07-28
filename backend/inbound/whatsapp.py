"""Adapter de WhatsApp Cloud API (Meta): parseo del webhook y envío saliente.

Es el único lugar que conoce el formato de Meta. `send_message` es best-effort y
lee las credenciales del entorno (config de despliegue, como las keys de IA):
WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_BASE.
"""
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)


def parse_webhook(payload):
    """Normaliza el payload del webhook a una lista de mensajes de texto:
    {account_external_id, contact_external_id, contact_name, text}."""
    out = []
    for entry in (payload or {}).get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name", "")
                     for c in value.get("contacts", []) or []}
            for msg in value.get("messages", []) or []:
                if msg.get("type") != "text":
                    continue  # (media/plantillas: fuera de este slice)
                frm = msg.get("from")
                out.append({
                    "account_external_id": phone_number_id,
                    "contact_external_id": frm,
                    "contact_name": names.get(frm, ""),
                    "text": (msg.get("text") or {}).get("body", ""),
                })
    return out


def verify_signature(raw_body, header_signature):
    """Verifica X-Hub-Signature-256 (HMAC-SHA256 con WHATSAPP_APP_SECRET). Si no hay
    secret configurado (dev), no se exige firma."""
    secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not secret:
        return True
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_signature.split("=", 1)[1])


def send_message(to, text):
    """Envía un texto por WhatsApp Cloud API. Best-effort: loguea y no levanta.
    Devuelve True si se envió."""
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id:
        logger.info("WhatsApp no configurado (WHATSAPP_TOKEN/PHONE_NUMBER_ID); no se envía")
        return False
    import httpx
    base = os.environ.get("WHATSAPP_API_BASE", "https://graph.facebook.com/v21.0")
    try:
        r = httpx.post(
            f"{base}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"messaging_product": "whatsapp", "to": to,
                  "type": "text", "text": {"body": text}},
            timeout=15)
        r.raise_for_status()
        return True
    except Exception:
        logger.warning("fallo enviando WhatsApp a %s", to, exc_info=True)
        return False
