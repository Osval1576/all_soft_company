from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
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


class WebhookTests(TestCase):
    def setUp(self):
        seed_plans()
        self.org = create_org("WHK")
        self.sub = self.org.subscription
        self.sub.plan = Plan.objects.get(key="pro"); self.sub.status = "trial"
        self.sub.stripe_customer_id = "cus_123"; self.sub.save()
        self.c = APIClient()

    def _event(self, etype, data, eid="evt_1"):
        return {"id": eid, "type": etype, "data": {"object": data}}

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook")
    def test_checkout_completed_activa(self, mock_verify):
        Plan.objects.filter(key="pro").update(stripe_price_id="price_pro")
        mock_verify.return_value = self._event(
            "checkout.session.completed",
            {"client_reference_id": str(self.org.id), "customer": "cus_123",
             "subscription": "sub_999"})
        r = self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="t=1,v1=x")
        self.assertEqual(r.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")
        self.assertEqual(self.sub.stripe_subscription_id, "sub_999")

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook")
    def test_subscription_deleted_baja_a_free(self, mock_verify):
        self.sub.status = "active"; self.sub.stripe_subscription_id = "sub_999"; self.sub.save()
        mock_verify.return_value = self._event(
            "customer.subscription.deleted", {"id": "sub_999"}, eid="evt_2")
        self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="sig")
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.plan.key, "free")

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook",
                side_effect=ValueError("bad sig"))
    def test_firma_invalida_400(self, _):
        r = self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="mala")
        self.assertEqual(r.status_code, 400)

    @mock.patch("billing.views._handle_event")
    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook")
    def test_idempotencia_mismo_event_id(self, mock_verify, mock_handle):
        self.sub.status = "active"; self.sub.stripe_subscription_id = "sub_999"; self.sub.save()
        ev = self._event("customer.subscription.deleted", {"id": "sub_999"}, eid="evt_dup")
        mock_verify.return_value = ev
        self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="s")
        self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="s")  # re-entrega del mismo event.id
        # el handler real solo corre una vez pese a las 2 entregas
        self.assertEqual(mock_handle.call_count, 1)

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook")
    def test_updated_past_due_no_reactiva(self, mock_verify):
        self.sub.status = "active"; self.sub.stripe_subscription_id = "sub_999"; self.sub.save()
        Plan.objects.filter(key="pro").update(stripe_price_id="price_pro")
        mock_verify.return_value = self._event(
            "customer.subscription.updated",
            {"id": "sub_999", "status": "past_due",
             "items": {"data": [{"price": {"id": "price_pro"}}]}},
            eid="evt_pd")
        r = self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="s")
        self.assertEqual(r.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "past_due")

    @mock.patch("billing.views.stripe_gateway.verify_and_parse_webhook")
    def test_updated_aplica_plan_business(self, mock_verify):
        self.sub.status = "active"; self.sub.stripe_subscription_id = "sub_999"; self.sub.save()
        Plan.objects.filter(key="business").update(stripe_price_id="price_biz")
        mock_verify.return_value = self._event(
            "customer.subscription.updated",
            {"id": "sub_999", "status": "active",
             "items": {"data": [{"price": {"id": "price_biz"}}]}},
            eid="evt_biz")
        r = self.c.post("/api/billing/webhook/", data="{}", content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="s")
        self.assertEqual(r.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.plan.key, "business")


class TrialExpiryTests(TestCase):
    def setUp(self):
        seed_plans()

    def test_expira_trials_vencidos_a_free(self):
        org = create_org("EXP")
        sub = org.subscription
        sub.plan = Plan.objects.get(key="pro"); sub.status = "trial"
        sub.trial_ends_at = timezone.now() - timedelta(days=1); sub.save()
        from billing.services import expire_trials
        n = expire_trials()
        sub.refresh_from_db()
        self.assertEqual(sub.plan.key, "free")
        self.assertEqual(sub.status, "active")
        self.assertGreaterEqual(n, 1)

    def test_no_toca_trials_vigentes_ni_pagas(self):
        org = create_org("KEEP")
        sub = org.subscription
        sub.plan = Plan.objects.get(key="pro"); sub.status = "trial"
        sub.trial_ends_at = timezone.now() + timedelta(days=5); sub.save()
        from billing.services import expire_trials
        expire_trials()
        sub.refresh_from_db()
        self.assertEqual(sub.plan.key, "pro")

    @mock.patch("billing.management.commands.check_trials.time.sleep")
    def test_command_loop_max_loops(self, sleep_mock):
        out = StringIO()
        call_command("check_trials", "--loop", "--max-loops=2", stdout=out)
        self.assertEqual(out.getvalue().count("trials"), 2)
        sleep_mock.assert_called_once()
