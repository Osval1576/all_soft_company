from django.db import migrations


def seed(apps, schema_editor):
    Ticket = apps.get_model("tickets_t", "Ticket")
    TicketEvent = apps.get_model("tickets_t", "TicketEvent")
    for t in Ticket.objects.all():
        if not TicketEvent.objects.filter(ticket=t, kind="created").exists():
            TicketEvent.objects.create(
                ticket=t,
                kind="created",
                actor_id=t.creado_por_id,
                payload={"seed": True},
            )


def unseed(apps, schema_editor):
    TicketEvent = apps.get_model("tickets_t", "TicketEvent")
    TicketEvent.objects.filter(kind="created", payload__seed=True).delete()


class Migration(migrations.Migration):
    dependencies = [("tickets_t", "0003_ticketevent")]
    operations = [migrations.RunPython(seed, unseed)]
