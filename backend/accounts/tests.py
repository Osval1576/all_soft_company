from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tenancy.testing import create_org
from accounts.models import EmailVerificationToken, Invitation

User = get_user_model()


class TokenModelTests(TestCase):
    def setUp(self):
        self.org = create_org("ACC")
        self.user = User.objects.create_user("u1", email="u1@x.com",
                                              role="ADMIN", organization=self.org, is_active=False)

    def test_verification_token_valido_y_expira(self):
        t = EmailVerificationToken.objects.create(user=self.user)
        self.assertTrue(t.token)
        self.assertTrue(t.is_valid())
        t.expires_at = timezone.now() - timedelta(hours=1)
        self.assertFalse(t.is_valid())
        t.expires_at = timezone.now() + timedelta(hours=1)
        t.used_at = timezone.now()
        self.assertFalse(t.is_valid())

    def test_invitation_basica(self):
        inv = Invitation.objects.create(organization=self.org, email="a@x.com", role="AGENT")
        self.assertTrue(inv.token)
        self.assertEqual(inv.status, "pending")
        self.assertTrue(inv.is_acceptable())
        # La unicidad de invitaciones PENDIENTES por (org, email) se valida en el
        # serializer (H2-T3): MySQL no soporta UniqueConstraint condicional (W036).


from rest_framework.test import APIClient
from accounts.models import EmailVerificationToken


class RegisterFlowTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def test_registro_crea_org_admin_inactivo_y_token(self):
        r = self.c.post("/api/auth/register/", {
            "org_name": "Acme Corp", "first_name": "Ana", "last_name": "Paz",
            "email": "ana@acme.com", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 201)
        u = User.objects.get(email="ana@acme.com")
        self.assertFalse(u.is_active)
        self.assertEqual(u.role, "ADMIN")
        self.assertIsNotNone(u.organization)
        self.assertTrue(EmailVerificationToken.objects.filter(user=u).exists())

    def test_email_duplicado_400(self):
        User.objects.create_user("x", email="dup@x.com", organization=create_org("DUP"))
        r = self.c.post("/api/auth/register/", {
            "org_name": "Otra", "first_name": "a", "last_name": "b",
            "email": "dup@x.com", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_verificar_activa_y_permite_login(self):
        self.c.post("/api/auth/register/", {
            "org_name": "Beta", "first_name": "a", "last_name": "b",
            "email": "beta@x.com", "password": "s3cretpass"}, format="json")
        tok = EmailVerificationToken.objects.get(user__email="beta@x.com")
        r = self.c.post("/api/auth/verify-email/", {"token": tok.token}, format="json")
        self.assertEqual(r.status_code, 200)
        tok.refresh_from_db()
        self.assertIsNotNone(tok.used_at)
        self.assertTrue(User.objects.get(email="beta@x.com").is_active)
        # token reusado -> 400
        self.assertEqual(self.c.post("/api/auth/verify-email/", {"token": tok.token},
                                     format="json").status_code, 400)

    def test_resend_no_revela_existencia(self):
        r1 = self.c.post("/api/auth/resend-verification/", {"email": "nadie@x.com"}, format="json")
        self.assertEqual(r1.status_code, 200)
