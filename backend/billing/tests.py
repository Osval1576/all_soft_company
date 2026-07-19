from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from tenancy.models import Organization
from tenancy.testing import create_org
from billing.models import Plan, Subscription
from billing.testing import seed_plans

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        seed_plans()

    def test_seed_planes(self):
        self.assertEqual(Plan.objects.get(key="free").max_agents, 2)
        self.assertEqual(Plan.objects.get(key="pro").max_agents, 10)
        self.assertIsNone(Plan.objects.get(key="business").max_agents)

    def test_org_nueva_arranca_trial_pro(self):
        org = Organization.objects.create(name="Nueva Co", slug="NEWCO")
        sub = org.subscription
        self.assertEqual(sub.plan.key, "pro")
        self.assertEqual(sub.status, "trial")
        self.assertTrue(sub.is_trial_active)

    def test_effective_plan_trial_vencido_es_free(self):
        org = Organization.objects.create(name="Vieja Co", slug="OLDCO")
        sub = org.subscription
        sub.trial_ends_at = timezone.now() - timedelta(days=1)
        sub.save()
        self.assertEqual(sub.effective_plan.key, "free")


class AgentLimitTests(TestCase):
    def setUp(self):
        seed_plans()
        self.org = create_org("LIM")   # arranca Business (ilimitada)
        self.admin = User.objects.create_user("lim_adm", email="lim@x.com", role="ADMIN",
                                               organization=self.org)
        self.c = APIClient(); self.c.force_authenticate(self.admin)

    def _set_plan(self, key):
        sub = self.org.subscription
        sub.plan = Plan.objects.get(key=key)
        sub.status = "active"
        sub.save()

    def _make_agents(self, n):
        for i in range(n):
            User.objects.create_user(f"ag{i}", email=f"ag{i}@x.com", role="AGENT",
                                     organization=self.org, is_active=True)

    def test_free_bloquea_tercer_agente_en_invitacion(self):
        self._set_plan("free")   # max 2
        self._make_agents(2)
        r = self.c.post("/api/invitations/", {"email": "extra@x.com", "role": "AGENT"},
                        format="json")
        self.assertEqual(r.status_code, 400)

    def test_free_permite_invitar_customer(self):
        self._set_plan("free")
        self._make_agents(2)
        r = self.c.post("/api/invitations/", {"email": "cli@x.com", "role": "CUSTOMER"},
                        format="json")
        self.assertEqual(r.status_code, 201)

    def test_business_ilimitado(self):
        self._make_agents(15)
        r = self.c.post("/api/invitations/", {"email": "more@x.com", "role": "AGENT"},
                        format="json")
        self.assertEqual(r.status_code, 201)

    def test_activar_agente_over_limit_falla(self):
        self._set_plan("free")
        self._make_agents(2)
        inactivo = User.objects.create_user("inact", email="in@x.com", role="AGENT",
                                            organization=self.org, is_active=False)
        r = self.c.patch(f"/api/users/users/{inactivo.id}/", {"is_active": True}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_downgrade_no_borra_agentes(self):
        self._make_agents(5)     # en Business
        self._set_plan("free")   # ahora over-limit
        self.assertEqual(User.objects.filter(organization=self.org, role="AGENT",
                                             is_active=True).count(), 5)
        from billing.services import can_add_agent
        self.assertFalse(can_add_agent(self.org))


class BillingEndpointsTests(TestCase):
    def setUp(self):
        seed_plans()
        self.org = create_org("BEP")
        self.admin = User.objects.create_user("bep_adm", email="bep@x.com", role="ADMIN",
                                               organization=self.org)
        self.c = APIClient(); self.c.force_authenticate(self.admin)

    def test_subscription_get_devuelve_plan_uso_y_planes(self):
        r = self.c.get("/api/billing/subscription/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("plan", r.data)
        self.assertIn("agent_count", r.data)
        self.assertIn("agent_limit", r.data)
        self.assertEqual(len(r.data["plans"]), 3)

    @mock.patch("billing.views.stripe_gateway.is_configured", return_value=False)
    def test_checkout_sin_stripe_config_503(self, _):
        r = self.c.post("/api/billing/checkout/", {"plan_key": "pro"}, format="json")
        self.assertEqual(r.status_code, 503)

    @mock.patch("billing.views.stripe_gateway.is_configured", return_value=True)
    @mock.patch("billing.views.stripe_gateway.create_checkout_session",
                return_value="https://checkout.stripe.test/abc")
    def test_checkout_devuelve_url(self, mock_create, _):
        r = self.c.post("/api/billing/checkout/", {"plan_key": "pro"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["url"], "https://checkout.stripe.test/abc")

    def test_checkout_free_400(self):
        with mock.patch("billing.views.stripe_gateway.is_configured", return_value=True):
            r = self.c.post("/api/billing/checkout/", {"plan_key": "free"}, format="json")
        self.assertEqual(r.status_code, 400)
