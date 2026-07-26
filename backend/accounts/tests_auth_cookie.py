"""Los endpoints de auth por cookie deben funcionar aunque el navegador mande
una cookie `access` vencida/inválida de una sesión anterior.

Bug: CookieJWTAuthentication (authenticator por defecto) lanza 401 ante un
access token inválido, y corría también sobre login/refresh/logout —endpoints
que NO dependen del access token—, dejando al usuario sin poder re-loguearse
ni refrescar sin borrar cookies a mano.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org

User = get_user_model()

_STALE = "garbage.expired.token"


class AuthCookieStaleTokenTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.org = create_org("AUTHCK")
        self.user = User.objects.create_user(
            "cookie_user", email="cookie@x.com", password="pw12345678",
            role="ADMIN", organization=self.org, is_active=True)
        self.creds = {"username": "cookie_user", "password": "pw12345678"}

    def test_login_cookie_works_with_stale_access_cookie(self):
        self.c.cookies["access"] = _STALE
        resp = self.c.post("/api/auth/login-cookie/", self.creds, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("access", resp.cookies)

    def test_refresh_cookie_works_with_stale_access_cookie(self):
        login = self.c.post("/api/auth/login-cookie/", self.creds, format="json")
        self.assertEqual(login.status_code, 200, login.content)
        # El access "vence": lo reemplazamos por basura; el refresh sigue vigente.
        self.c.cookies["access"] = _STALE
        resp = self.c.post("/api/auth/refresh-cookie/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("access", resp.cookies)

    def test_logout_works_with_stale_access_cookie(self):
        self.c.cookies["access"] = _STALE
        resp = self.c.post("/api/auth/logout/")
        self.assertEqual(resp.status_code, 200, resp.content)
