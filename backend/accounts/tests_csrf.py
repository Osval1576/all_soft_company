"""CN-005: la auth por cookie JWT debe exigir token CSRF en métodos inseguros.

Sin esto, como la cookie `access` viaja automáticamente en cada request, un sitio
malicioso podría forzar acciones autenticadas (CSRF). Los métodos seguros
(GET/HEAD/OPTIONS) quedan exentos; login/refresh/logout también (no autentican
por la cookie access).
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org

User = get_user_model()


class CookieJwtCsrfTests(TestCase):
    def setUp(self):
        cache.clear()  # evita chocar con el throttle de login
        self.org = create_org("CSRF")
        self.user = User.objects.create_user(
            "csrf_u", email="csrf@x.com", password="pw12345678",
            role="ADMIN", organization=self.org, is_active=True)

    def _logged_client(self):
        # enforce_csrf_checks=True: sin esto el test client marca la request como
        # exenta de CSRF y el check nunca corre.
        c = APIClient(enforce_csrf_checks=True)
        r = c.post("/api/auth/login-cookie/",
                   {"username": "csrf_u", "password": "pw12345678"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)  # login no requiere CSRF
        return c

    def test_safe_method_ok_without_csrf(self):
        c = self._logged_client()
        r = c.get("/api/me/")
        self.assertEqual(r.status_code, 200, r.content)

    def test_unsafe_method_blocked_without_csrf(self):
        c = self._logged_client()
        r = c.patch(f"/api/users/users/{self.user.id}/",
                    {"first_name": "Nuevo"}, format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_unsafe_method_ok_with_csrf_token(self):
        c = self._logged_client()
        c.get("/api/auth/csrf/")  # setea la cookie csrftoken
        token = c.cookies["csrftoken"].value
        r = c.patch(f"/api/users/users/{self.user.id}/",
                    {"first_name": "Nuevo"}, format="json",
                    HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200, r.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Nuevo")
