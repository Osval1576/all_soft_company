"""Fuente UNICA de querysets scoped por organizacion.

Toda vista/consumer/servicio que liste o busque recursos de un tenant DEBE
pasar por estos helpers. El guard de CI (tenancy/tests.py) falla si aparece
un queryset crudo de Ticket fuera de este modulo y su allowlist.
org=None (staff de plataforma en la API in-app) -> queryset vacio, siempre.
"""
from django.contrib.auth import get_user_model


def _User():
    return get_user_model()


def user_org(user):
    return getattr(user, "organization", None)


def org_users(org):
    qs = _User().objects.all().order_by("id")
    return qs.filter(organization=org) if org is not None else qs.none()


def org_agents(org):
    return org_users(org).filter(role="AGENT")


def org_admins(org):
    return org_users(org).filter(role="ADMIN")


def org_tickets(org):
    from tickets_t.models import Ticket
    qs = Ticket.objects.select_related("sla", "csat")
    return qs.filter(organization=org) if org is not None else qs.none()
