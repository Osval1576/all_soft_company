# Migracion final de "Ticket.organization": tras 0007 (columna nullable) y la
# semilla de tenancy/0002_seed_org (que asigna toda fila pre-existente a ALS),
# ya no puede quedar ninguna fila huerfana -> se puede volver NOT NULL sin riesgo.
# Mismo patron que sla/migrations/0005_organization_not_null.py.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tickets_t", "0007_ticket_organization_and_more"),
        ("tenancy", "0002_seed_org"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ticket",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tickets", to="tenancy.organization",
            ),
        ),
    ]
