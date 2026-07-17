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
