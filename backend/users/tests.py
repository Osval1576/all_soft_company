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
