"""Ingesta de mensajes entrantes desde canales externos (omnicanal, Fase 5.1).

Punto único, agnóstico del canal: WhatsApp, email, etc. entregan un mensaje
normalizado y este servicio resuelve la org, arma/continúa el ticket del contacto
y dispara la IA (escalada por sentimiento + deflección RAG sobre la KB).
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from tickets_t.models import TicketMessage
from tickets_t.creation import create_ticket
from .models import ChannelAccount, ChannelThread

logger = logging.getLogger(__name__)
User = get_user_model()

_OPEN_STATES = ("OPEN", "IN_PROGRESS")


def resolve_org(channel, account_external_id):
    """Org dueña de la cuenta de canal (o None si es desconocida/inactiva)."""
    acc = (ChannelAccount.objects
           .filter(channel=channel, external_id=account_external_id, is_active=True)
           .select_related("organization").first())
    return acc.organization if acc else None


def _contact_user(org, channel, contact_external_id, name):
    """Usuario CUSTOMER sintético que representa al contacto externo (para ser
    creado_por del ticket y aparecer en el hilo). Idempotente por (org, canal, id)."""
    username = f"{channel}:{org.id}:{contact_external_id}"
    user = User.objects.filter(username=username).first()
    if user:
        return user
    return User.objects.create_user(
        username=username, role="CUSTOMER", organization=org,
        is_active=True, first_name=(name or "")[:150])


def _thread_ticket(org, channel, contact_external_id, contact, text, title_hint=None):
    """Ticket abierto del contacto (reusa el del hilo si sigue abierto; si no,
    crea uno nuevo y reengancha el hilo). Devuelve (ticket, created)."""
    thread = (ChannelThread.objects
              .filter(organization=org, channel=channel, contact_external_id=contact_external_id)
              .select_related("ticket").first())
    if thread and thread.ticket.estado in _OPEN_STATES:
        return thread.ticket, False

    titulo = ((title_hint or text) or "").strip()[:120] or f"Consulta por {channel}"
    ticket = create_ticket(org, creado_por=contact, titulo=titulo, descripcion=(text or ""))
    if thread:
        thread.ticket = ticket
        thread.save(update_fields=["ticket", "updated_at"])
    else:
        ChannelThread.objects.create(
            organization=org, channel=channel,
            contact_external_id=contact_external_id, ticket=ticket)
    return ticket, True


@transaction.atomic
def handle_inbound_message(*, channel, account_external_id, contact_external_id,
                           text, contact_name="", subject=None):
    """Procesa un mensaje entrante. Devuelve {"ticket", "reply", "created"} o None
    si la cuenta no corresponde a ninguna org (mensaje ignorado).

    `subject` (opcional, p. ej. el asunto del email) se usa como título del ticket
    nuevo. `reply` es la respuesta automática de deflección (el caller la envía por
    el canal) o None si no se resolvió con la KB (queda para un agente humano).
    """
    text = (text or "").strip()
    if not text:
        return None

    org = resolve_org(channel, account_external_id)
    if org is None:
        logger.warning("mensaje de canal %s para cuenta desconocida %s (ignorado)",
                       channel, account_external_id)
        return None

    contact = _contact_user(org, channel, contact_external_id, contact_name)
    ticket, created = _thread_ticket(org, channel, contact_external_id, contact, text, subject)
    TicketMessage.objects.create(ticket=ticket, sender=contact, content=text)

    # 2B: escalada por sentimiento (resiliente, nunca rompe la ingesta).
    from tickets_t.ai_hooks import apply_sentiment_escalation
    apply_sentiment_escalation(ticket, text)

    reply = _try_deflect(org, text)
    return {"ticket": ticket, "reply": reply, "created": created}


def _try_deflect(org, text):
    """3B sobre el canal: intenta resolver con la KB publicada de la org. Devuelve
    el texto de respuesta o None (sin KB / sin plan / la IA no alcanza / falla)."""
    try:
        from ai.services import ai_enabled, answer_from_kb
        from ai.ratelimit import allow_public
        from kb.search import search_articles
        if not ai_enabled(org):
            return None
        articles = search_articles(org, text)
        if not articles:
            return None
        # Guardrail de costo/abuso del canal público (mismo tope que el widget).
        if not allow_public(org):
            logger.info("deflección de canal rate-limited para org %s", getattr(org, "id", None))
            return None
        return answer_from_kb(text, articles)
    except Exception:
        logger.warning("deflección de canal falló para org %s",
                       getattr(org, "id", None), exc_info=True)
        return None
