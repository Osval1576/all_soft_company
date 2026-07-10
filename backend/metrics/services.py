# backend/metrics/services.py
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone


def _parse_window(request):
    try:
        w = int(request.query_params.get("window", 30))
    except (TypeError, ValueError):
        w = 30
    return w if w in (7, 30, 90) else 30


def windowed_tickets(window):
    from tickets_t.models import Ticket
    cutoff = timezone.now() - timedelta(days=window)
    return (Ticket.objects
            .select_related("sla", "csat")
            .filter(created_at__gte=cutoff))


def volume_totals(qs):
    agg = qs.aggregate(
        total=Count("id"),
        resolved=Count("id", filter=Q(estado__in=["RESOLVED", "CLOSED"])),
        open=Count("id", filter=Q(estado__in=["OPEN", "IN_PROGRESS"])),
    )
    return {"total": agg["total"], "resolved": agg["resolved"], "open": agg["open"]}


def csat_summary(qs):
    agg = qs.aggregate(average=Avg("csat__score"), count=Count("csat"))
    distribution = {i: 0 for i in range(1, 6)}
    for row in (qs.filter(csat__isnull=False)
                  .values("csat__score")
                  .annotate(n=Count("csat__score"))):
        distribution[row["csat__score"]] = row["n"]
    return {"average": agg["average"], "count": agg["count"], "distribution": distribution}
