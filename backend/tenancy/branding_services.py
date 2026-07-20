def branding_enabled(org):
    """True si la org tiene plan pago (Pro/Business) según el estado efectivo."""
    if org is None:
        return False
    sub = getattr(org, "subscription", None)
    if sub is None:
        return False
    return sub.effective_plan.key in ("pro", "business")
