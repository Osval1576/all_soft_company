import logging

from django.utils import timezone

from .calendar_engine import get_calendar
from .levels import compute_levels

logger = logging.getLogger(__name__)

_RANK = {"ok": 0, "at_risk": 1, "breached": 2, "met": 0}
_CLOCK_LABEL = {"fr": "primera respuesta", "res": "resolución"}


def run_sla_check():
    from tickets_t.models import Ticket
    from .models import TicketSla

    cal = get_calendar()
    now = timezone.now()
    result = {"checked": 0, "notified": 0}

    qs = TicketSla.objects.select_related("ticket").filter(
        ticket__estado__in=["OPEN", "IN_PROGRESS"]
    )
    for ts in qs:
        result["checked"] += 1
        levels = compute_levels(ts, now, cal)
        for clock, field in (("fr", "fr_level"), ("res", "res_level")):
            new = levels[clock]
            stored = getattr(ts, field)
            if new == "met":
                continue
            if _RANK[new] > _RANK.get(stored, 0):
                _notify(ts.ticket, clock, new)
                setattr(ts, field, new)
                ts.save(update_fields=[field])
                result["notified"] += 1
    return result


def _notify(ticket, clock, level):
    from notifications.services import dispatch
    kind = "sla_breached" if level == "breached" else "sla_at_risk"
    try:
        dispatch(kind, ticket, actor=None, extra={"clock": _CLOCK_LABEL[clock]})
    except Exception:
        logger.exception("no se pudo notificar SLA para ticket %s", ticket.pk)
