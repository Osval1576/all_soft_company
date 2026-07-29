"""Adapter de email entrante (email-to-ticket, Fase 5.1 extendida).

Patrón webhook: un servicio de inbound-parse (SendGrid Inbound Parse, Mailgun
Routes, Postmark, etc.) recibe el mail, lo parsea y lo POSTea acá. Normalizamos
los campos comunes; la respuesta automática sale por el email backend de Django.
"""
import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _addr(value):
    """Extrae la dirección 'pelada' de un 'Nombre <mail@x>' -> 'mail@x' (lower)."""
    return (parseaddr(value or "")[1] or "").strip().lower()


def _name(value):
    return (parseaddr(value or "")[0] or "").strip()


def _first(data, *keys):
    for k in keys:
        v = data.get(k)
        if v:
            return v
    return ""


def parse_inbound(data):
    """Normaliza el payload de un servicio de inbound-parse a:
    {account_external_id (el 'to' / buzón de soporte), contact_external_id (el
    'from'), contact_name, subject, text}. Tolera las variantes de nombre de campo
    más comunes (SendGrid/Mailgun/Postmark)."""
    to_raw = _first(data, "to", "recipient", "To")
    from_raw = _first(data, "from", "sender", "From")
    subject = _first(data, "subject", "Subject")
    text = _first(data, "text", "body-plain", "TextBody", "stripped-text", "plain")
    return {
        "account_external_id": _addr(to_raw),
        "contact_external_id": _addr(from_raw),
        "contact_name": _name(from_raw),
        "subject": subject.strip(),
        "text": text,
    }


def send_reply(to, subject, text):
    """Envía la respuesta automática por email. Best-effort: loguea y no levanta."""
    try:
        send_mail(
            subject=subject or "Re: tu consulta",
            message=text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.warning("fallo enviando email de respuesta a %s", to, exc_info=True)
        return False
