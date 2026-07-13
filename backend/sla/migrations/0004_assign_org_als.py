from django.db import migrations


def assign_org(apps, schema_editor):
    """Asigna la SlaConfig/SlaPolicy/Holiday pre-existentes (globales, sin
    organizacion) a la org semilla ALS. La crea con get_or_create por si la
    DB (p.ej. de test) no corrio la migracion semilla de tenancy. Si no
    existe una SlaConfig global aun (nunca se llamo get_solo()), la crea
    aqui para que ALS quede provisionada igual que cualquier org nueva.
    Idempotente.
    """
    Organization = apps.get_model("tenancy", "Organization")
    SlaConfig = apps.get_model("sla", "SlaConfig")
    SlaPolicy = apps.get_model("sla", "SlaPolicy")
    Holiday = apps.get_model("sla", "Holiday")

    org, _ = Organization.objects.get_or_create(slug="ALS", defaults={"name": "AllSafe"})

    SlaConfig.objects.filter(organization__isnull=True).update(organization=org)
    SlaConfig.objects.get_or_create(organization=org)

    SlaPolicy.objects.filter(organization__isnull=True).update(organization=org)
    Holiday.objects.filter(organization__isnull=True).update(organization=org)


def unassign_org(apps, schema_editor):
    SlaConfig = apps.get_model("sla", "SlaConfig")
    SlaPolicy = apps.get_model("sla", "SlaPolicy")
    Holiday = apps.get_model("sla", "Holiday")
    Organization = apps.get_model("tenancy", "Organization")
    try:
        org = Organization.objects.get(slug="ALS")
    except Organization.DoesNotExist:
        return
    SlaConfig.objects.filter(organization=org).update(organization=None)
    SlaPolicy.objects.filter(organization=org).update(organization=None)
    Holiday.objects.filter(organization=org).update(organization=None)


class Migration(migrations.Migration):

    dependencies = [
        ("sla", "0003_holiday_organization_slaconfig_organization_and_more"),
        ("tenancy", "0002_seed_org"),
    ]

    operations = [
        migrations.RunPython(assign_org, unassign_org),
    ]
