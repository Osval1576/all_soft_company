import logging
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

from .emails import send_notification_email
from .models import Notification, NotificationPreference
from .presence import is_online

User = get_user_model()

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "OPEN": "Abierto", "IN_PROGRESS": "En proceso",
    "RESOLVED": "Resuelto", "CLOSED": "Cerrado",
}


def _admins():
    return User.objects.filter(models.Q(is_superuser=True) | models.Q(role="ADMIN"))


def _agents():
    return User.objects.filter(role="AGENT")


def _push(user_id, notification):
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "type": "notify.message",
        "data": {
            "id": notification.id,
            "kind": notification.kind,
            "ticket": notification.ticket_id,
            "title": notification.title,
            "body": notification.body,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        },
    }
    try:
        async_to_sync(layer.group_send)(f"user_{user_id}", payload)
    except Exception:
        logger.exception("notify group_send failed for user_%s", user_id)


def _send_email(recipient, subject, body):
    if getattr(settings, "NOTIFICATIONS_EMAIL_ASYNC", True):
        threading.Thread(
            target=send_notification_email, args=(recipient, subject, body), daemon=True
        ).start()
    else:
        send_notification_email(recipient, subject, body)


def _recipients_for(kind, ticket, actor, extra):
    """Devuelve una lista de dicts:
    {user, title, body, email(bool), pref_field(str), subject, email_body, offline_only(bool)}
    """
    ref = ticket.reference
    specs = []

    if kind == "ticket_created":
        for admin in _admins():
            specs.append({
                "user": admin,
                "title": f"Nuevo ticket {ref}",
                "body": ticket.titulo,
                "email": True,
                "pref_field": "email_on_ticket_created",
                "subject": f"[AllSafe] Nuevo ticket {ref}",
                "email_body": f"Entró un ticket nuevo: {ref} — {ticket.titulo}.",
                "offline_only": False,
            })
        for agent in _agents():
            specs.append({
                "user": agent, "title": f"Ticket sin asignar: {ref}",
                "body": ticket.titulo, "email": False, "pref_field": None,
                "subject": "", "email_body": "", "offline_only": False,
            })

    elif kind == "assigned":
        if ticket.creado_por_id:
            specs.append({
                "user": ticket.creado_por,
                "title": f"Tu ticket {ref} fue asignado",
                "body": "Un técnico se está ocupando de tu caso.",
                "email": True, "pref_field": "email_on_assigned",
                "subject": f"[AllSafe] Tu ticket {ref} fue asignado",
                "email_body": f"Tu ticket {ref} ya tiene un técnico asignado. Pronto vas a tener novedades.",
                "offline_only": False,
            })
        if ticket.asignado_a_id:
            specs.append({
                "user": ticket.asignado_a,
                "title": f"Se te asignó el ticket {ref}",
                "body": ticket.titulo, "email": False, "pref_field": None,
                "subject": "", "email_body": "", "offline_only": False,
            })

    elif kind == "new_message":
        preview = (extra or {}).get("content", "")
        for user in (ticket.creado_por, ticket.asignado_a):
            if not user:
                continue
            specs.append({
                "user": user,
                "title": f"Nuevo mensaje en {ref}",
                "body": preview[:120],
                "email": True, "pref_field": "email_on_new_message",
                "subject": f"[AllSafe] Nuevo mensaje en tu ticket {ref}",
                "email_body": f"Tenés un mensaje nuevo en el ticket {ref}. Entrá a AllSafe para responder.",
                "offline_only": True,
            })

    elif kind == "status_changed":
        if ticket.creado_por_id:
            label = STATUS_LABELS.get(ticket.estado, ticket.estado)
            specs.append({
                "user": ticket.creado_por,
                "title": f"Tu ticket {ref} cambió de estado",
                "body": f"Ahora está: {label}.",
                "email": True, "pref_field": "email_on_status_changed",
                "subject": f"[AllSafe] Tu ticket {ref} ahora está {label}",
                "email_body": f"El estado de tu ticket {ref} cambió a: {label}.",
                "offline_only": False,
            })

    elif kind in ("sla_at_risk", "sla_breached"):
        clock = (extra or {}).get("clock", "SLA")
        if kind == "sla_at_risk":
            title = f"SLA en riesgo: {ref}"
            body = f"El ticket {ref} está por vencer su SLA de {clock}."
        else:
            title = f"SLA vencido: {ref}"
            body = f"El ticket {ref} venció su SLA de {clock}."
        targets = []
        if ticket.asignado_a_id:
            targets.append(ticket.asignado_a)
        targets.extend(_admins())
        seen = set()
        for user in targets:
            if user.id in seen:
                continue
            seen.add(user.id)
            specs.append({
                "user": user, "title": title, "body": body,
                "email": False, "pref_field": None,
                "subject": "", "email_body": "", "offline_only": False,
            })

    return specs


def dispatch(kind, ticket, actor=None, extra=None):
    actor_id = actor.id if actor else None
    for spec in _recipients_for(kind, ticket, actor, extra):
        user = spec["user"]
        if actor_id and user.id == actor_id:
            continue
        notif = Notification.objects.create(
            recipient=user, kind=kind, ticket=ticket, actor=actor,
            title=spec["title"], body=spec.get("body", ""),
        )
        _push(user.id, notif)
        if not spec.get("email"):
            continue
        if spec.get("offline_only") and is_online(user.id):
            continue
        prefs = NotificationPreference.for_user(user)
        if getattr(prefs, spec["pref_field"], True):
            _send_email(user, spec["subject"], spec["email_body"])


EVENT_TO_KIND = {"created": "ticket_created", "assigned": "assigned"}


def notify_for_event(ticket, event_kind, actor, payload=None):
    payload = payload or {}

    def _run():
        if event_kind in ("status_changed", "reopened"):
            if ticket.estado in ("RESOLVED", "CLOSED"):
                dispatch("status_changed", ticket, actor, payload)
            return
        mapped = EVENT_TO_KIND.get(event_kind)
        if mapped:
            dispatch(mapped, ticket, actor, payload)

    transaction.on_commit(_run)
