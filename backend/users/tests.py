import importlib

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

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
        User = get_user_model()
        legacy_super = User.objects.create_user("gsuper", is_superuser=True, role="CUSTOMER")
        legacy_staff = User.objects.create_user("gstaff", is_staff=True, role="CUSTOMER")
        ok_admin = User.objects.create_user("gadmin", role="ADMIN")
        ok_customer = User.objects.create_user("gcust", role="CUSTOMER")

        from django.apps import apps as global_apps
        mod = importlib.import_module("users.migrations.0002_backfill_roles")
        mod.backfill_roles(global_apps, None)

        legacy_super.refresh_from_db(); legacy_staff.refresh_from_db()
        ok_admin.refresh_from_db(); ok_customer.refresh_from_db()
        self.assertEqual(legacy_super.role, "ADMIN")
        self.assertEqual(legacy_staff.role, "AGENT")
        self.assertEqual(ok_admin.role, "ADMIN")
        self.assertEqual(ok_customer.role, "CUSTOMER")
