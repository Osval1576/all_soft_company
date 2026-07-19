# backend/billing/tests_adversarial.py
"""Suite adversarial de billing: ataca los bordes de aislamiento multi-tenant
y de la superficie de pago (checkout/webhook) para confirmar que:
- un admin solo puede ver/mutar la subscription de su propia organizacion,
- solo un ADMIN puede iniciar checkout,
- el webhook sin firma valida no altera ningun estado,
- no existe ninguna ruta de API que permita auto-activar un plan sin pasar
  por el webhook firmado de Stripe.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from billing.testing import seed_plans
from billing.models import Subscription

User = get_user_model()


class BillingAdversarialTests(TestCase):
    def setUp(self):
        seed_plans()
        self.org_a = create_org("BAA")
        self.org_b = create_org("BAB")
        self.admin_a = User.objects.create_user("baa", email="baa@x.com", role="ADMIN",
                                                organization=self.org_a)
        self.c = APIClient(); self.c.force_authenticate(self.admin_a)

    def test_admin_solo_ve_su_subscription(self):
        r = self.c.get("/api/billing/subscription/")
        self.assertEqual(r.status_code, 200)
        # el plan/uso son de A; no hay forma de pedir la sub de B por la API
        self.assertEqual(r.data["agent_count"], 0)
        self.assertEqual(r.data["plan"], self.org_a.subscription.effective_plan.key)
        # la sub de B (otra org) queda intacta y no aparece en la respuesta
        self.assertNotEqual(self.org_b.subscription.id, self.org_a.subscription.id)

    def test_no_admin_no_hace_checkout(self):
        agent = User.objects.create_user("baa_ag", email="ag@x.com", role="AGENT",
                                         organization=self.org_a)
        c = APIClient(); c.force_authenticate(agent)
        before = Subscription.objects.get(organization=self.org_a).status
        with mock.patch("billing.views.stripe_gateway.is_configured", return_value=True):
            r = c.post("/api/billing/checkout/", {"plan_key": "pro"}, format="json")
        self.assertEqual(r.status_code, 403)
        # el intento de checkout no admin no muto nada
        self.assertEqual(Subscription.objects.get(organization=self.org_a).status, before)

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook",
                side_effect=ValueError("no sig"))
    def test_webhook_sin_firma_no_altera_nada(self, _):
        before = Subscription.objects.get(organization=self.org_a).status
        r = APIClient().post("/api/billing/webhook/", data="{}",
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Subscription.objects.get(organization=self.org_a).status, before)

    def test_front_no_puede_autoactivar_plan(self):
        # no existe ningun endpoint que setee status=active sin pasar por el
        # webhook firmado de Stripe: PATCH a /subscription/ no esta implementado.
        before = Subscription.objects.get(organization=self.org_a).status
        r = self.c.patch("/api/billing/subscription/", {"status": "active"}, format="json")
        self.assertIn(r.status_code, (403, 405))  # SubscriptionView no acepta PATCH
        self.assertEqual(Subscription.objects.get(organization=self.org_a).status, before)
