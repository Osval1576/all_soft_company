from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Organization
from .scoping import org_admins, org_agents, org_users, user_org

User = get_user_model()


class OrganizationModelTests(TestCase):
    def test_slug_unico_y_str(self):
        org = Organization.objects.create(name="Acme Corp", slug="ACME")
        self.assertEqual(str(org), "Acme Corp")
        self.assertTrue(org.is_active)
        with self.assertRaises(Exception):
            Organization.objects.create(name="Otra", slug="ACME")

    def test_slug_uppercase_on_save(self):
        org = Organization.objects.create(name="x", slug="acme")
        self.assertEqual(org.slug, "ACME")


class ScopingUserTests(TestCase):
    def setUp(self):
        self.a = Organization.objects.create(name="A", slug="AAA")
        self.b = Organization.objects.create(name="B", slug="BBB")
        self.admin_a = User.objects.create_user("adm_a", role="ADMIN", organization=self.a)
        self.agent_a = User.objects.create_user("agt_a", role="AGENT", organization=self.a)
        self.cust_b = User.objects.create_user("cus_b", role="CUSTOMER", organization=self.b)

    def test_org_users_no_cruza(self):
        self.assertEqual(set(org_users(self.a)), {self.admin_a, self.agent_a})
        self.assertEqual(set(org_users(self.b)), {self.cust_b})
        self.assertEqual(org_users(None).count(), 0)

    def test_org_agents_y_admins(self):
        self.assertEqual(list(org_agents(self.a)), [self.agent_a])
        self.assertEqual(list(org_admins(self.a)), [self.admin_a])

    def test_user_org(self):
        self.assertEqual(user_org(self.admin_a), self.a)
        platform = User.objects.create_user("plat", is_superuser=True)
        self.assertIsNone(user_org(platform))


import importlib


class SeedMigrationTests(TestCase):
    def test_seed_asigna_usuarios_sin_org_a_la_semilla(self):
        # User.organization sigue nullable; Ticket.organization es NOT NULL desde
        # T7, asi que ya NO se puede reproducir un ticket sin org con el modelo
        # real (esa garantia la impone ahora el schema, no este test). Se cubre la
        # rama de usuarios legacy, que sigue siendo el caso reproducible.
        u = User.objects.create_user("legacy_user", role="CUSTOMER")
        self.assertIsNone(u.organization)
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        u.refresh_from_db()
        self.assertIsNotNone(u.organization)
        self.assertEqual(u.organization.slug, "ALS")

    def test_seed_idempotente(self):
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        mod.seed_org(global_apps, None)
        self.assertEqual(Organization.objects.filter(slug="ALS").count(), 1)


from rest_framework.test import APIClient


class MiddlewareTests(TestCase):
    def setUp(self):
        from .testing import create_org
        self.org = create_org("MWA")
        self.client_api = APIClient()

    def test_user_sin_org_403(self):
        u = User.objects.create_user("sinorg", role="CUSTOMER")
        self.client_api.force_authenticate(u)
        r = self.client_api.get("/api/tickets_t/")
        self.assertEqual(r.status_code, 403)
        self.assertIn("organización", r.json()["detail"].lower())

    def test_org_suspendida_403(self):
        self.org.is_active = False
        self.org.save()
        u = User.objects.create_user("susp", role="CUSTOMER", organization=self.org)
        self.client_api.force_authenticate(u)
        r = self.client_api.get("/api/tickets_t/")
        self.assertEqual(r.status_code, 403)

    def test_health_y_auth_exentos(self):
        self.assertEqual(self.client_api.get("/api/health/").status_code, 200)


import pathlib


class RawQuerysetGuardTests(TestCase):
    """Anti-regresion: nadie debe consultar Ticket sin pasar por org_tickets().

    Un queryset crudo de Ticket.objects fuera de tenancy/scoping.py es, por
    definicion, un candidato a fuga cross-tenant (nada garantiza que este
    filtrado por organizacion). Allowlist minimo y justificado UNA POR UNA:
    """
    ALLOWED = {
        "tenancy/scoping.py",            # fuente unica
        "tickets_t/serializers.py",      # contador de referencia por prefijo (org-scoped por slug)
    }

    def test_sin_ticket_objects_crudo_fuera_del_allowlist(self):
        backend = pathlib.Path(__file__).resolve().parent.parent
        offenders = []
        for path in backend.rglob("*.py"):
            rel = path.relative_to(backend).as_posix()
            if ("migrations" in rel or rel.startswith("tenancy/tests")
                    or "/tests/" in rel  # p.ej. landing_cms/tests/test_*.py: paquete de tests
                    or rel.endswith(("tests.py", "tests_isolation.py"))
                    or rel in self.ALLOWED):
                continue
            if "Ticket.objects" in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"Queryset crudo de Ticket fuera de tenancy/scoping.py: {offenders}")
