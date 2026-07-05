from django.db import migrations

SEED = [
    ("URGENT", 30, 240),
    ("HIGH", 60, 480),
    ("MEDIUM", 120, 960),
    ("LOW", 240, 1920),
]


def seed(apps, schema_editor):
    SlaPolicy = apps.get_model("sla", "SlaPolicy")
    for prio, fr, res in SEED:
        SlaPolicy.objects.get_or_create(
            priority=prio,
            defaults={"first_response_minutes": fr, "resolution_minutes": res},
        )


def unseed(apps, schema_editor):
    SlaPolicy = apps.get_model("sla", "SlaPolicy")
    SlaPolicy.objects.filter(priority__in=[s[0] for s in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [("sla", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
