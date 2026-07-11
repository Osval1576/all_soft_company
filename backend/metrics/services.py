# backend/metrics/services.py
from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate
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


def _avg(pairs, cal):
    from sla.calendar_engine import business_minutes_between
    mins = [business_minutes_between(a, b, cal) for a, b in pairs]
    return (sum(mins) / len(mins)) if mins else None


def avg_times(qs, cal):
    fr = qs.filter(sla__first_response_met_at__isnull=False).values_list(
        "created_at", "sla__first_response_met_at")
    res = qs.filter(sla__resolved_at__isnull=False).values_list(
        "created_at", "sla__resolved_at")
    return {"first_response_min": _avg(fr, cal), "resolution_min": _avg(res, cal)}


def compliance(qs):
    fr_done = Q(sla__first_response_met_at__isnull=False, sla__first_response_due_at__isnull=False)
    res_done = Q(sla__resolved_at__isnull=False, sla__resolution_due_at__isnull=False)
    agg = qs.aggregate(
        fr_total=Count("id", filter=fr_done),
        fr_ok=Count("id", filter=fr_done & Q(sla__first_response_met_at__lte=F("sla__first_response_due_at"))),
        res_total=Count("id", filter=res_done),
        res_ok=Count("id", filter=res_done & Q(sla__resolved_at__lte=F("sla__resolution_due_at"))),
    )
    return {
        "first_response": (agg["fr_ok"] / agg["fr_total"]) if agg["fr_total"] else None,
        "resolution": (agg["res_ok"] / agg["res_total"]) if agg["res_total"] else None,
    }


def trend(qs, window):
    start = (timezone.now() - timedelta(days=window)).date()
    end = timezone.now().date()
    created_map = {r["d"]: r["n"] for r in
                   qs.annotate(d=TruncDate("created_at")).values("d").annotate(n=Count("id"))}
    resolved_map = {r["d"]: r["n"] for r in
                    qs.filter(sla__resolved_at__isnull=False)
                      .annotate(d=TruncDate("sla__resolved_at")).values("d").annotate(n=Count("id"))}
    series, d = [], start
    while d <= end:
        series.append({"date": d.isoformat(),
                       "created": created_map.get(d, 0),
                       "resolved": resolved_map.get(d, 0)})
        d += timedelta(days=1)
    return series
