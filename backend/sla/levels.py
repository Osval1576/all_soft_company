from .calendar_engine import business_minutes_between


def _level(now, due_at, met_at, budget_min, cal):
    if met_at is not None:
        return "met"
    if due_at is None or budget_min is None:
        return "ok"
    if now > due_at:
        return "breached"
    remaining = business_minutes_between(now, due_at, cal)
    if remaining <= (cal.at_risk_pct / 100.0) * budget_min:
        return "at_risk"
    return "ok"


def compute_levels(ticket_sla, now, cal):
    return {
        "fr": _level(now, ticket_sla.first_response_due_at,
                     ticket_sla.first_response_met_at,
                     ticket_sla.first_response_budget_min, cal),
        "res": _level(now, ticket_sla.resolution_due_at,
                      ticket_sla.resolved_at,
                      ticket_sla.resolution_budget_min, cal),
    }
