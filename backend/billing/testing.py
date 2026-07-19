"""Helpers de fixtures de billing. NO depender del seed de migracion."""
from django.utils import timezone


_PLANS = [
    ("free", "Free", 2, 0),
    ("pro", "Pro", 10, 1),
    ("business", "Business", None, 2),
]


def seed_plans():
    from .models import Plan
    for key, name, max_agents, order in _PLANS:
        Plan.objects.get_or_create(
            key=key, defaults={"name": name, "max_agents": max_agents, "order": order})


def provision_test_org(org):
    """Deja la org de test en Business (ilimitada) para no chocar con el limite de
    agentes en suites que crean varios tecnicos. Los tests de limite bajan el plan
    explicitamente."""
    from .models import Plan, Subscription
    seed_plans()
    business = Plan.objects.get(key="business")
    sub, _ = Subscription.objects.get_or_create(
        organization=org, defaults={"plan": business, "status": Subscription.Status.ACTIVE})
    if sub.plan.key != "business":
        sub.plan = business
        sub.status = Subscription.Status.ACTIVE
        sub.save()
    return sub
