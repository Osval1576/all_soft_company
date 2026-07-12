from django.db import migrations


def backfill_roles(apps, schema_editor):
    """Anti-lockout para el switch del front a role: usuarios legacy creados via
    createsuperuser/flags quedaron con role=CUSTOMER (default)."""
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).exclude(role="ADMIN").update(role="ADMIN")
    User.objects.filter(is_staff=True, is_superuser=False, role="CUSTOMER").update(role="AGENT")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_roles, migrations.RunPython.noop),
    ]
