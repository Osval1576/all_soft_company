from datetime import timedelta
from django.db import migrations
from django.utils import timezone

_PLANS = [("free", "Free", 2, 0), ("pro", "Pro", 10, 1), ("business", "Business", None, 2)]


def seed(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Subscription = apps.get_model("billing", "Subscription")
    Organization = apps.get_model("tenancy", "Organization")
    for key, name, max_agents, order in _PLANS:
        Plan.objects.get_or_create(key=key, defaults={"name": name, "max_agents": max_agents, "order": order})
    business = Plan.objects.get(key="business")
    pro = Plan.objects.get(key="pro")
    for org in Organization.objects.all():
        if hasattr(org, "subscription"):
            continue
        if org.slug == "ALS":
            Subscription.objects.create(organization=org, plan=business, status="active")
        else:
            Subscription.objects.create(organization=org, plan=pro, status="trial",
                                        trial_ends_at=timezone.now() + timedelta(days=14))


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial"), ("tenancy", "0002_seed_org")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
