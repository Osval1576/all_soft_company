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
