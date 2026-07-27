"""Prueba adversarial: el login no debe ser vulnerable a SQL injection.

El camino de auth usa exclusivamente el ORM de Django (ModelBackend ->
get_by_natural_key -> queryset parametrizado), así que los payloads SQLi se
tratan como strings literales. Este test lo demuestra de punta a punta y queda
como guard de regresión.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org

User = get_user_model()

# Payloads SQLi clásicos (auth bypass + destructivos + comentarios/uniones).
PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1--",
    "admin'--",
    "admin' #",
    "' OR ''='",
    '" OR ""="',
    "') OR ('1'='1",
    "'; DROP TABLE users_user;--",
    "' UNION SELECT username, password FROM users_user--",
    "\\'; DROP TABLE users_user;--",
]

LOGIN_URLS = ("/api/auth/login/", "/api/auth/login-cookie/")


class LoginSqlInjectionTests(TestCase):
    def setUp(self):
        self.org = create_org("SQLI")
        self.user = User.objects.create_user(
            "legit_user", email="legit@x.com", password="Pw-legit-12345",
            role="ADMIN", organization=self.org, is_active=True)
        self.user_count = User.objects.count()

    def _post(self, url, username, password):
        cache.clear()  # cada intento parte sin throttle, para llegar a la auth
        return APIClient().post(url, {"username": username, "password": password},
                                format="json")

    def test_payload_en_username_no_autentica(self):
        for url in LOGIN_URLS:
            for p in PAYLOADS:
                r = self._post(url, p, "cualquier-cosa")
                self.assertNotEqual(r.status_code, 200, f"{url} autenticó con username={p!r}")
                self.assertNotIn("access", r.cookies, f"{url} seteó cookie con username={p!r}")

    def test_payload_en_password_no_autentica(self):
        for url in LOGIN_URLS:
            for p in PAYLOADS:
                r = self._post(url, "legit_user", p)
                self.assertNotEqual(r.status_code, 200, f"{url} autenticó con password={p!r}")
                self.assertNotIn("access", r.cookies, f"{url} seteó cookie con password={p!r}")

    def test_no_bypass_con_or_1_igual_1(self):
        # El bypass clásico contra el usuario real tampoco debe funcionar.
        for url in LOGIN_URLS:
            r = self._post(url, "legit_user", "' OR '1'='1")
            self.assertNotEqual(r.status_code, 200)

    def test_tabla_intacta_y_login_legitimo_sigue_ok(self):
        # Ningún payload destruyó/alteró la tabla de usuarios...
        self.assertEqual(User.objects.count(), self.user_count)
        self.assertTrue(User.objects.filter(username="legit_user").exists())
        # ...y las credenciales correctas siguen autenticando.
        r = self._post("/api/auth/login-cookie/", "legit_user", "Pw-legit-12345")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("access", r.cookies)
