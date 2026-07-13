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
    def test_seed_asigna_todo_a_la_org_semilla(self):
        from tickets_t.models import Ticket
        u = User.objects.create_user("legacy_user", role="CUSTOMER")
        t = Ticket.objects.create(reference="LEG-001", titulo="t", descripcion="d",
                                  creado_por=u)
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        u.refresh_from_db(); t.refresh_from_db()
        self.assertIsNotNone(u.organization)
        self.assertEqual(u.organization.slug, "ALS")
        self.assertEqual(t.organization_id, u.organization_id)

    def test_seed_idempotente(self):
        mod = importlib.import_module("tenancy.migrations.0002_seed_org")
        from django.apps import apps as global_apps
        mod.seed_org(global_apps, None)
        mod.seed_org(global_apps, None)
        self.assertEqual(Organization.objects.filter(slug="ALS").count(), 1)
