"""Helpers de fixtures multi-org para las suites. NO usar seeds de migracion."""
from .models import Organization

_DEFAULT_POLICIES = [("URGENT", 30, 240), ("HIGH", 60, 480),
                     ("MEDIUM", 120, 960), ("LOW", 240, 1920)]


def create_org(slug="TST", name=None):
    """Crea una org. Idempotente por slug."""
    org, created = Organization.objects.get_or_create(
        slug=slug, defaults={"name": name or f"Org {slug}"})
    # El signal post_save de tenancy.Organization (sla/signals.provision_org_sla)
    # ya provisiona SlaConfig/SlaPolicy al crear la org; este bloque es un
    # refuerzo idempotente (get_or_create) por si el signal no corrio (p.ej.
    # organization ya existia de una corrida anterior sin fixtures limpios).
    from sla.models import SlaConfig, SlaPolicy
    SlaConfig.objects.get_or_create(organization=org)
    for prio, fr, res in _DEFAULT_POLICIES:
        SlaPolicy.objects.get_or_create(
            organization=org, priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res})
    try:
        from billing.testing import provision_test_org
        provision_test_org(org)
    except ImportError:
        pass
    return org
