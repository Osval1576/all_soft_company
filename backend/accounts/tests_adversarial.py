from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from tenancy.testing import create_org
from accounts.models import Invitation

User = get_user_model()


class InvitationAdversarialTests(TestCase):
    def setUp(self):
        self.org_a = create_org("ADA")
        self.org_b = create_org("ADB")
        self.admin_a = User.objects.create_user("ada_adm", email="ada@x.com", role="ADMIN",
                                                 organization=self.org_a)
        self.admin_b = User.objects.create_user("adb_adm", email="adb@x.com", role="ADMIN",
                                                 organization=self.org_b)

    def _invite(self, admin, email, role="AGENT"):
        c = APIClient(); c.force_authenticate(admin)
        c.post("/api/invitations/", {"email": email, "role": role}, format="json")
        return Invitation.objects.get(email=email)

    def test_accept_ignora_role_y_org_del_body(self):
        inv = self._invite(self.admin_a, "victim@x.com", role="CUSTOMER")
        pub = APIClient()
        r = pub.post(f"/api/auth/invitation/{inv.token}/accept/", {
            "first_name": "V", "password": "s3cretpass",
            "role": "ADMIN", "organization": self.org_b.id}, format="json")
        self.assertEqual(r.status_code, 200)
        u = User.objects.get(email="victim@x.com")
        self.assertEqual(u.role, "CUSTOMER")            # del token, no del body
        self.assertEqual(u.organization_id, self.org_a.id)  # del token, no del body

    def test_admin_no_revoca_invitacion_de_otra_org(self):
        inv_b = self._invite(self.admin_b, "b_guy@x.com")
        c = APIClient(); c.force_authenticate(self.admin_a)
        self.assertEqual(c.delete(f"/api/invitations/{inv_b.id}/").status_code, 404)
        inv_b.refresh_from_db()
        self.assertEqual(inv_b.status, "pending")

    def test_token_expirado_no_acepta(self):
        inv = self._invite(self.admin_a, "late@x.com")
        inv.expires_at = timezone.now() - timedelta(days=1); inv.save()
        r = APIClient().post(f"/api/auth/invitation/{inv.token}/accept/",
                             {"first_name": "L", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 410)
        self.assertFalse(User.objects.filter(email="late@x.com").exists())

    def test_token_reusado_no_crea_segundo_user(self):
        inv = self._invite(self.admin_a, "once@x.com")
        pub = APIClient()
        pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                 {"first_name": "O", "password": "s3cretpass"}, format="json")
        r2 = pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                      {"first_name": "O2", "password": "s3cretpass"}, format="json")
        self.assertIn(r2.status_code, (400, 410))
        self.assertEqual(User.objects.filter(email="once@x.com").count(), 1)

    def test_get_invitation_publico_no_expone_demas(self):
        inv = self._invite(self.admin_a, "peek@x.com")
        data = APIClient().get(f"/api/auth/invitation/{inv.token}/").json()
        self.assertEqual(set(data), {"organization", "role", "email"})

    def test_doble_invitacion_pendiente_400(self):
        c = APIClient(); c.force_authenticate(self.admin_a)
        r1 = c.post("/api/invitations/", {"email": "x@y.com", "role": "AGENT"}, format="json")
        self.assertEqual(r1.status_code, 201)
        r2 = c.post("/api/invitations/", {"email": "x@y.com", "role": "AGENT"}, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(
            Invitation.objects.filter(organization=self.org_a, email__iexact="x@y.com",
                                      status="pending").count(),
            1)

    def test_agent_no_puede_invitar(self):
        agent_a = User.objects.create_user("ada_agt", email="ada_agt@x.com", role="AGENT",
                                           organization=self.org_a)
        c = APIClient(); c.force_authenticate(agent_a)
        r = c.post("/api/invitations/", {"email": "sneaky@x.com", "role": "AGENT"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Invitation.objects.filter(email="sneaky@x.com").exists())

    def test_customer_no_puede_invitar(self):
        customer_a = User.objects.create_user("ada_cus", email="ada_cus@x.com", role="CUSTOMER",
                                              organization=self.org_a)
        c = APIClient(); c.force_authenticate(customer_a)
        r = c.post("/api/invitations/", {"email": "sneaky2@x.com", "role": "AGENT"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Invitation.objects.filter(email="sneaky2@x.com").exists())

    def test_accept_con_email_tomado_en_carrera_devuelve_409(self):
        # Invitación creada mientras el email todavía estaba libre...
        inv = self._invite(self.admin_a, "taken@x.com")
        # ...pero alguien se registra/crea con ese mismo email antes del accept (carrera).
        User.objects.create_user("taken@x.com", email="taken@x.com", role="CUSTOMER",
                                 organization=self.org_b)
        pub = APIClient()
        r = pub.post(f"/api/auth/invitation/{inv.token}/accept/",
                     {"first_name": "T", "password": "s3cretpass"}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(User.objects.filter(email__iexact="taken@x.com").count(), 1)

    def test_lista_invitaciones_no_incluye_otra_org(self):
        self._invite(self.admin_a, "a_guy@x.com")
        self._invite(self.admin_b, "b_guy2@x.com")
        c = APIClient(); c.force_authenticate(self.admin_a)
        r = c.get("/api/invitations/")
        self.assertEqual(r.status_code, 200)
        emails = {inv["email"] for inv in r.json()}
        self.assertIn("a_guy@x.com", emails)
        self.assertNotIn("b_guy2@x.com", emails)
