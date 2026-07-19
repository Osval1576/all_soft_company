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
    explicitamente.

    Importante: usa `org.subscription` (el accessor reverso), no una query aparte,
    para mutar el MISMO objeto Python que Django cachea en `org`. El signal
    post_save de Organization crea la Subscription inicial (trial/pro) asignando
    `Subscription(organization=org, ...)`, y el descriptor OneToOne reverso de
    Django cachea esa instancia en `org` en ese momento. Si acá se hiciera un
    `Subscription.objects.get_or_create(...)` aparte, se actualizaría la fila en
    la BD pero el objeto ya cacheado en `org` (y en cualquier FK que apunte a esa
    misma instancia de `org`, como `user.organization` en tests con
    force_authenticate) seguiría viendo el plan viejo.
    """
    from .models import Plan, Subscription
    seed_plans()
    business = Plan.objects.get(key="business")
    try:
        sub = org.subscription
    except Subscription.DoesNotExist:
        sub = Subscription.objects.create(
            organization=org, plan=business, status=Subscription.Status.ACTIVE)
        org.subscription = sub
        return sub
    if sub.plan.key != "business":
        sub.plan = business
        sub.status = Subscription.Status.ACTIVE
        sub.save()
    return sub
