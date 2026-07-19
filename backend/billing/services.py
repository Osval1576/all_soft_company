def active_agent_count(org):
    from tenancy.scoping import org_agents
    return org_agents(org).filter(is_active=True).count()


def agent_limit(org):
    sub = getattr(org, "subscription", None)
    if sub is None:
        from .models import Plan
        p = Plan.objects.filter(key="free").first()
        return p.max_agents if p else 0
    return sub.effective_plan.max_agents  # None = ilimitado


def can_add_agent(org):
    limit = agent_limit(org)
    if limit is None:
        return True
    return active_agent_count(org) < limit


def expire_trials():
    """Baja a Free los trials vencidos. Idempotente."""
    from django.utils import timezone
    from .models import Plan, Subscription
    free = Plan.objects.filter(key="free").first()
    if free is None:
        return 0
    qs = Subscription.objects.filter(status="trial", trial_ends_at__lt=timezone.now())
    n = 0
    for sub in qs:
        sub.plan = free
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["plan", "status"])
        n += 1
    return n
