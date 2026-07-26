"""CN-003: los endpoints de login deben limitar los intentos por IP para
frenar la fuerza bruta de credenciales. Sin throttle, un atacante puede probar
contraseñas sin límite contra /api/auth/login/ y /api/auth/login-cookie/.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org

User = get_user_model()


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()  # el throttle guarda el conteo en el cache default
        self.c = APIClient()
        self.org = create_org("THR")
        self.user = User.objects.create_user(
            "thr_user", email="thr@x.com", password="pw12345678",
            role="ADMIN", organization=self.org, is_active=True)

    def tearDown(self):
        cache.clear()

    def test_login_cookie_throttled_after_limit(self):
        bad = {"username": "thr_user", "password": "wrong"}
        statuses = [
            self.c.post("/api/auth/login-cookie/", bad, format="json").status_code
            for _ in range(6)
        ]
        self.assertEqual(statuses[-1], 429, statuses)

    def test_token_login_throttled_after_limit(self):
        bad = {"username": "thr_user", "password": "wrong"}
        statuses = [
            self.c.post("/api/auth/login/", bad, format="json").status_code
            for _ in range(6)
        ]
        self.assertEqual(statuses[-1], 429, statuses)

    def test_valid_login_not_blocked_within_limit(self):
        good = {"username": "thr_user", "password": "pw12345678"}
        r = self.c.post("/api/auth/login-cookie/", good, format="json")
        self.assertEqual(r.status_code, 200, r.content)
