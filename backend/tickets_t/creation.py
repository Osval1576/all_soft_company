"""Helpers de creación de tickets reutilizables fuera del serializer (p. ej. la
ingesta omnicanal). La generación de referencia replica el formato del
TicketCreateSerializer: <slug>-<YYYYMMDD>-<NNNNNN>, correlativo por org y día.
"""
from django.utils import timezone

from .models import Ticket


def generate_reference(org):
    """Devuelve la próxima referencia para la org. Usar dentro de transaction.atomic
    (hace select_for_update para evitar colisiones de correlativo)."""
    prefix = f"{org.slug}-" + timezone.localdate().strftime("%Y%m%d") + "-"
    last = (Ticket.objects.select_for_update()
            .filter(reference__startswith=prefix)
            .order_by("-reference")
            .first())
    next_num = int(last.reference.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{next_num:06d}"


def create_ticket(org, *, creado_por, titulo, descripcion, estado="OPEN"):
    """Crea un ticket con referencia correlativa. La organización va explícita, así
    que no es una consulta cruda que pueda fugar entre tenants. Usar dentro de
    transaction.atomic (generate_reference hace select_for_update)."""
    return Ticket.objects.create(
        reference=generate_reference(org),
        titulo=titulo, descripcion=descripcion,
        creado_por=creado_por, organization=org, estado=estado)
