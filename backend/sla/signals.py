import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .calendar_engine import get_calendar, add_business_time

logger = logging.getLogger(__name__)


def _agent_or_admin(user):
    r = getattr(user, "role", None)
    return r in ("AGENT", "ADMIN") or getattr(user, "is_superuser", False)


def create_ticket_sla(ticket):
    from .models import SlaPolicy, TicketSla
    policy = SlaPolicy.objects.filter(priority=ticket.prioridad).first()
    if policy is None:
        logger.warning("sin SlaPolicy para prioridad %s", ticket.prioridad)
        return None
    cal = get_calendar()
    start = ticket.created_at
    return TicketSla.objects.create(
        ticket=ticket,
        first_response_budget_min=policy.first_response_minutes,
        first_response_due_at=add_business_time(start, policy.first_response_minutes, cal),
        resolution_budget_min=policy.resolution_minutes,
        resolution_due_at=add_business_time(start, policy.resolution_minutes, cal),
    )


@receiver(post_save, sender="tickets_t.Ticket")
def on_ticket_saved(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        create_ticket_sla(instance)
    except Exception:
        logger.exception("no se pudo crear TicketSla para %s", instance.pk)


@receiver(post_save, sender="tickets_t.TicketMessage")
def on_message_saved(sender, instance, created, **kwargs):
    if not created or not _agent_or_admin(instance.sender):
        return
    try:
        ts = getattr(instance.ticket, "sla", None)
        if ts and ts.first_response_met_at is None:
            ts.first_response_met_at = instance.created_at
            ts.fr_level = "met"
            ts.save(update_fields=["first_response_met_at", "fr_level"])
    except Exception:
        logger.exception("no se pudo marcar 1a respuesta para ticket %s", instance.ticket_id)


@receiver(post_save, sender="tickets_t.TicketEvent")
def on_event_saved(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        ts = getattr(instance.ticket, "sla", None)
        if ts is None:
            return
        if instance.kind == "status_changed" and (instance.payload or {}).get("to") == "RESOLVED":
            if ts.resolved_at is None:
                ts.resolved_at = timezone.now()
                ts.res_level = "met"
                ts.save(update_fields=["resolved_at", "res_level"])
        elif instance.kind == "priority_changed":
            _recompute_unmet(ts, instance.ticket)
    except Exception:
        logger.exception("error en on_event_saved para ticket %s", instance.ticket_id)


def _recompute_unmet(ts, ticket):
    from .models import SlaPolicy
    policy = SlaPolicy.objects.filter(priority=ticket.prioridad).first()
    if policy is None:
        return
    cal = get_calendar()
    start = ticket.created_at
    fields = []
    if ts.first_response_met_at is None:
        ts.first_response_budget_min = policy.first_response_minutes
        ts.first_response_due_at = add_business_time(start, policy.first_response_minutes, cal)
        fields += ["first_response_budget_min", "first_response_due_at"]
    if ts.resolved_at is None:
        ts.resolution_budget_min = policy.resolution_minutes
        ts.resolution_due_at = add_business_time(start, policy.resolution_minutes, cal)
        fields += ["resolution_budget_min", "resolution_due_at"]
    if fields:
        ts.save(update_fields=fields)
