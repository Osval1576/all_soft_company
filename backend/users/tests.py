import importlib

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from config.checks import prod_settings_check


class ProdSettingsCheckTests(TestCase):
    @override_settings(DEBUG=False, SECRET_KEY="CHANGE_ME__PUT_YOUR_OWN_SECRET_KEY_HERE")
    def test_prod_con_placeholder_falla(self):
        errors = prod_settings_check(None)
        self.assertTrue(any(e.id == "config.E001" for e in errors))

    @override_settings(DEBUG=False, SECRET_KEY="k" * 50, ALLOWED_HOSTS=[])
    def test_prod_sin_hosts_falla(self):
        errors = prod_settings_check(None)
        self.assertTrue(any(e.id == "config.E002" for e in errors))

    @override_settings(DEBUG=True)
    def test_dev_pasa_sin_errores(self):
        self.assertEqual(prod_settings_check(None), [])


class HealthEndpointTests(TestCase):
    def test_health_sin_auth_devuelve_ok(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})


class BackfillRolesTests(TestCase):
    def test_backfill_corrige_legacy_y_no_toca_correctos(self):
        from tenancy.testing import create_org
        org = create_org("USR")
        User = get_user_model()
        # superuser de plataforma: queda sin org a propósito
        legacy_super = User.objects.create_user("gsuper", is_superuser=True, role="CUSTOMER")
        legacy_staff = User.objects.create_user("gstaff", is_staff=True, role="CUSTOMER", organization=org)
        ok_admin = User.objects.create_user("gadmin", role="ADMIN", organization=org)
        ok_customer = User.objects.create_user("gcust", role="CUSTOMER", organization=org)

        from django.apps import apps as global_apps
        mod = importlib.import_module("users.migrations.0002_backfill_roles")
        mod.backfill_roles(global_apps, None)

        legacy_super.refresh_from_db(); legacy_staff.refresh_from_db()
        ok_admin.refresh_from_db(); ok_customer.refresh_from_db()
        self.assertEqual(legacy_super.role, "ADMIN")
        self.assertEqual(legacy_staff.role, "AGENT")
        self.assertEqual(ok_admin.role, "ADMIN")
        self.assertEqual(ok_customer.role, "CUSTOMER")


class TenantUserAdminTests(TestCase):
    def test_admin_solo_lista_y_crea_en_su_org(self):
        from tenancy.testing import create_org
        User = get_user_model()
        a, b = create_org("UTA"), create_org("UTB")
        admin_a = User.objects.create_user("uta_adm", role="ADMIN", organization=a)
        User.objects.create_user("utb_user", role="CUSTOMER", organization=b)
        c = APIClient(); c.force_authenticate(admin_a)
        usernames = {u["username"] for u in c.get("/api/users/users/").json()}
        self.assertNotIn("utb_user", usernames)
        r = c.post("/api/users/users/", {"username": "nuevo_uta", "password": "x9!k2#pQ7",
                                         "role": "CUSTOMER"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(User.objects.get(username="nuevo_uta").organization_id, a.id)
