# Migracion final de la secuencia de "SLA por organizacion": tras 0004
# (que asigna toda fila pre-existente a la org semilla ALS), se puede volver
# NOT NULL sin riesgo de dejar filas huerfanas.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sla", "0004_assign_org_als"),
        ("tenancy", "0002_seed_org"),
    ]

    operations = [
        migrations.AlterField(
            model_name="slaconfig",
            name="organization",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sla_config", to="tenancy.organization",
            ),
        ),
        migrations.AlterField(
            model_name="slapolicy",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tenancy.organization",
            ),
        ),
        migrations.AlterField(
            model_name="holiday",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tenancy.organization",
            ),
        ),
    ]
