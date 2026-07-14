from django.db import migrations


def seed_org(apps, schema_editor):
    """Barrido TOTAL a la org semilla: TODOS los users y tickets pre-existentes
    (superusers incluidos) quedan en ALS/"AllSafe" — sin excepciones. El operador
    de plataforma correcto se crea DESPUES de migrar, a mano, con
    `createsuperuser` y organization=None (ver spec H1). Idempotente.
    """
    Organization = apps.get_model("tenancy", "Organization")
    User = apps.get_model("users", "User")
    Ticket = apps.get_model("tickets_t", "Ticket")
    org, _ = Organization.objects.get_or_create(slug="ALS", defaults={"name": "AllSafe"})
    User.objects.filter(organization__isnull=True).update(organization=org)
    Ticket.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
        ("users", "0003_user_organization"),
        ("tickets_t", "0007_ticket_organization_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_org, migrations.RunPython.noop),
    ]
