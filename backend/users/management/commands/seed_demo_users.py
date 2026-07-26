"""Crea/actualiza usuarios demo para navegar la app en desarrollo.

Idempotente: podés correrlo las veces que quieras. Reasigna rol, organización,
password y estado activo en cada corrida. Los flags is_staff/is_superuser
quedan en False a propósito (el front gatea por `role`, no por esos flags).

    python manage.py seed_demo_users

Guarda de seguridad: se bloquea con DEBUG=False (password conocido); usá --force
si de verdad querés correrlo fuera de desarrollo.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from tenancy.models import Organization

User = get_user_model()

# (username, role, email)
DEMO_USERS = [
    ("demo_admin", "ADMIN", "admin@demo.local"),
    ("demo_tech", "AGENT", "tech@demo.local"),
    ("demo_tech2", "AGENT", "tech2@demo.local"),
    ("demo_cliente", "CUSTOMER", "cliente@demo.local"),
]


class Command(BaseCommand):
    help = "Crea/actualiza usuarios demo para navegar la app en desarrollo (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo1234",
                            help="Password para todos los usuarios demo (default: demo1234).")
        parser.add_argument("--org-slug", default="ALS",
                            help="Slug de la organización a asignar (default: ALS).")
        parser.add_argument("--force", action="store_true",
                            help="Permitir correr con DEBUG=False (por defecto se bloquea).")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError(
                "seed_demo_users está pensado para desarrollo (DEBUG=True). "
                "Usá --force si de verdad querés correrlo con DEBUG=False.")

        try:
            org = Organization.objects.get(slug=opts["org_slug"])
        except Organization.DoesNotExist:
            raise CommandError(
                f"No existe la organización con slug '{opts['org_slug']}'. "
                "Corré las migraciones primero (crean la org ALS).")

        password = opts["password"]
        for username, role, email in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "role": role,
                          "organization": org, "is_active": True},
            )
            user.email = email
            user.role = role
            user.organization = org
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.set_password(password)
            user.save()
            verb = "creado" if created else "actualizado"
            self.stdout.write(f"  {verb}: {username:14s} role={role:8s} org={org.slug}")

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(DEMO_USERS)} usuarios demo en '{org.slug}' (password: {password})."))
