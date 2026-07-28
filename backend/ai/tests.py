import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tickets_t.models import Ticket, TicketMessage
from ai import gateway
from ai.gateway import AiNotConfigured

User = get_user_model()

DRAFT = "Hola, gracias por escribir. Probá limpiar la caché y contanos si sigue."


class GatewayDispatchTests(SimpleTestCase):
    """Gateway multi-proveedor: elección de proveedor/modelo por env, sin DB."""

    def test_provider_aliases(self):
        cases = [("claude", "anthropic"), ("anthropic", "anthropic"),
                 ("google", "gemini"), ("gemini", "gemini"),
                 ("chatgpt", "openai"), ("gpt", "openai"), ("openai", "openai")]
        for raw, canon in cases:
            with patch.dict(os.environ, {"AI_PROVIDER": raw}):
                self.assertEqual(gateway._provider(), canon)

    def test_model_defaults_and_env_override(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_GEMINI_QUALITY_MODEL", None)
            os.environ.pop("AI_ANTHROPIC_FAST_MODEL", None)
            self.assertEqual(gateway._model_for("gemini", "quality"), "gemini-flash-latest")
            self.assertEqual(gateway._model_for("anthropic", "fast"), "claude-haiku-4-5")
        with patch.dict(os.environ, {"AI_OPENAI_QUALITY_MODEL": "gpt-custom"}):
            self.assertEqual(gateway._model_for("openai", "quality"), "gpt-custom")

    def test_generate_dispatches_by_provider_and_tier(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "gemini"}), \
             patch("ai.gateway._gemini", return_value="ok") as mg, \
             patch("ai.gateway._anthropic") as ma, \
             patch("ai.gateway._openai") as mo:
            out = gateway.generate(system="s", user_prompt="u", tier="fast")
        self.assertEqual(out, "ok")
        ma.assert_not_called()
        mo.assert_not_called()
        # el adapter recibe el modelo resuelto por (proveedor, tier)
        self.assertEqual(mg.call_args.args[2], "gemini-flash-lite-latest")

    def test_missing_key_raises_not_configured(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "openai"}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with self.assertRaises(AiNotConfigured):
                gateway.generate(system="s", user_prompt="u", tier="quality")

    def test_unknown_provider_raises(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "llama-local"}):
            with self.assertRaises(AiNotConfigured):
                gateway.generate(system="s", user_prompt="u")


def _url(ticket_id):
    return f"/api/ai/tickets/{ticket_id}/draft/"


class AiDraftTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.org = create_org("AITEST")  # Business por defecto (provision_test_org)
        self.admin = User.objects.create_user("ai_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("ai_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("ai_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.ticket = Ticket.objects.create(
            reference="AI-1", titulo="No carga el panel",
            descripcion="El panel de reportes no me carga desde ayer.",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org, estado="IN_PROGRESS")
        TicketMessage.objects.create(ticket=self.ticket, sender=self.customer,
                                     content="Sigue sin cargar, ya reinicié.")

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_agent_gets_draft_with_ticket_context(self, mock_gen):
        self.c.force_authenticate(self.agent)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["draft"], DRAFT)
        mock_gen.assert_called_once()
        # el prompt lleva la descripción y el mensaje del cliente
        prompt = mock_gen.call_args.kwargs["user_prompt"]
        self.assertIn("no me carga desde ayer", prompt)
        self.assertIn("Sigue sin cargar", prompt)

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_admin_gets_draft(self, mock_gen):
        self.c.force_authenticate(self.admin)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 200, r.content)

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_customer_forbidden(self, mock_gen):
        self.c.force_authenticate(self.customer)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 403)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_free_plan_forbidden_with_upsell(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        self.c.force_authenticate(self.agent)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.data.get("upsell"))
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_cross_org_404(self, mock_gen):
        other = create_org("AIOTHER")
        outsider = User.objects.create_user("ai_out", role="ADMIN",
                                             organization=other, is_active=True)
        self.c.force_authenticate(outsider)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 404)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_agent_not_assigned_cannot_draft(self, mock_gen):
        # un agente de la misma org pero NO asignado al ticket -> 404 (can_access_ticket)
        other_agent = User.objects.create_user("ai_agent2", role="AGENT",
                                                organization=self.org, is_active=True)
        self.c.force_authenticate(other_agent)
        r = self.c.post(_url(self.ticket.id))
        self.assertEqual(r.status_code, 404)
        mock_gen.assert_not_called()


SUMMARY = "El cliente no puede entrar al panel. Se le pidió reiniciar; sigue igual. Falta escalar a infra."


class AiSummaryTests(TestCase):
    """Fase 2A — resumen del hilo del ticket."""

    def setUp(self):
        self.c = APIClient()
        self.org = create_org("AISUM")  # Business por defecto
        self.admin = User.objects.create_user("sum_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("sum_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("sum_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.ticket = Ticket.objects.create(
            reference="SUM-1", titulo="No entro al panel",
            descripcion="No puedo entrar al panel desde ayer.",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org, estado="IN_PROGRESS")
        TicketMessage.objects.create(ticket=self.ticket, sender=self.customer,
                                     content="Ya reinicié y sigue sin entrar.")

    def _url(self, ticket_id):
        return f"/api/ai/tickets/{ticket_id}/summary/"

    @patch("ai.gateway.generate", return_value=SUMMARY)
    def test_agent_gets_summary_with_thread(self, mock_gen):
        self.c.force_authenticate(self.agent)
        r = self.c.post(self._url(self.ticket.id))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["summary"], SUMMARY)
        prompt = mock_gen.call_args.kwargs["user_prompt"]
        self.assertIn("No puedo entrar al panel", prompt)
        self.assertIn("Ya reinicié", prompt)

    @patch("ai.gateway.generate", return_value=SUMMARY)
    def test_customer_forbidden(self, mock_gen):
        self.c.force_authenticate(self.customer)
        r = self.c.post(self._url(self.ticket.id))
        self.assertEqual(r.status_code, 403)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value=SUMMARY)
    def test_free_plan_forbidden_with_upsell(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        self.c.force_authenticate(self.agent)
        r = self.c.post(self._url(self.ticket.id))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.data.get("upsell"))
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value=SUMMARY)
    def test_cross_org_404(self, mock_gen):
        other = create_org("SUMOTHER")
        outsider = User.objects.create_user("sum_out", role="ADMIN",
                                             organization=other, is_active=True)
        self.c.force_authenticate(outsider)
        r = self.c.post(self._url(self.ticket.id))
        self.assertEqual(r.status_code, 404)
        mock_gen.assert_not_called()


class AiTriageTests(TestCase):
    """Fase 1B — auto-triage de prioridad al crear el ticket."""

    def setUp(self):
        self.org = create_org("AITRIAGE")  # Business por defecto
        self.customer = User.objects.create_user("tri_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.c = APIClient()
        self.c.force_authenticate(self.customer)

    def _create(self, **extra):
        data = {"titulo": "Se cayó el sitio", "descripcion": "Todo el portal está caído."}
        data.update(extra)
        return self.c.post("/api/tickets_t/", data, format="json")

    @patch("ai.gateway.generate", return_value="URGENT")
    def test_autotriage_sets_priority_and_logs_event(self, mock_gen):
        r = self._create(prioridad="MEDIUM")
        self.assertEqual(r.status_code, 201, r.content)
        t = Ticket.objects.get(id=r.data["id"])
        self.assertEqual(t.prioridad, "URGENT")
        ev = t.events.filter(kind="priority_changed").first()
        self.assertIsNotNone(ev)
        self.assertTrue(ev.payload.get("auto"))
        self.assertEqual(ev.payload.get("from"), "MEDIUM")
        self.assertEqual(ev.payload.get("to"), "URGENT")
        mock_gen.assert_called_once()

    @patch("ai.gateway.generate", return_value="URGENT")
    def test_free_plan_skips_autotriage(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        r = self._create(prioridad="LOW")
        self.assertEqual(r.status_code, 201, r.content)
        t = Ticket.objects.get(id=r.data["id"])
        self.assertEqual(t.prioridad, "LOW")
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", side_effect=RuntimeError("boom"))
    def test_autotriage_failure_does_not_break_creation(self, mock_gen):
        r = self._create(prioridad="LOW")
        self.assertEqual(r.status_code, 201, r.content)
        t = Ticket.objects.get(id=r.data["id"])
        self.assertEqual(t.prioridad, "LOW")  # fallback al valor enviado

    @patch("ai.gateway.generate", return_value="banana")
    def test_autotriage_invalid_response_ignored(self, mock_gen):
        r = self._create(prioridad="MEDIUM")
        self.assertEqual(r.status_code, 201, r.content)
        t = Ticket.objects.get(id=r.data["id"])
        self.assertEqual(t.prioridad, "MEDIUM")


class AiSentimentEscalationTests(TestCase):
    """Fase 2B — sentimiento del mensaje del cliente sube la prioridad (nunca la baja)."""

    def setUp(self):
        self.org = create_org("AISENT")  # Business por defecto
        self.customer = User.objects.create_user("sent_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.agent = User.objects.create_user("sent_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.ticket = Ticket.objects.create(
            reference="SENT-1", titulo="Pago rechazado",
            descripcion="No puedo pagar la suscripción.",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org, estado="IN_PROGRESS", prioridad="MEDIUM")

    @patch("ai.gateway.generate", return_value="URGENT")
    def test_negative_sentiment_raises_priority(self, mock_gen):
        from tickets_t.ai_hooks import apply_sentiment_escalation
        result = apply_sentiment_escalation(
            self.ticket, "Esto es un desastre, llevo días esperando y nadie responde!!")
        self.ticket.refresh_from_db()
        self.assertEqual(result, "URGENT")
        self.assertEqual(self.ticket.prioridad, "URGENT")
        ev = self.ticket.events.filter(kind="priority_changed").first()
        self.assertIsNotNone(ev)
        self.assertTrue(ev.payload.get("auto"))
        self.assertEqual(ev.payload.get("reason"), "sentiment")
        self.assertEqual(ev.payload.get("from"), "MEDIUM")
        self.assertEqual(ev.payload.get("to"), "URGENT")
        prompt = mock_gen.call_args.kwargs["user_prompt"]
        self.assertIn("nadie responde", prompt)

    @patch("ai.gateway.generate", return_value="LOW")
    def test_never_lowers_priority(self, mock_gen):
        self.ticket.prioridad = "HIGH"
        self.ticket.save()
        from tickets_t.ai_hooks import apply_sentiment_escalation
        result = apply_sentiment_escalation(self.ticket, "gracias, ya está resuelto")
        self.ticket.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(self.ticket.prioridad, "HIGH")
        self.assertFalse(self.ticket.events.filter(kind="priority_changed").exists())

    @patch("ai.gateway.generate", return_value="URGENT")
    def test_free_plan_no_escalation(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        from tickets_t.ai_hooks import apply_sentiment_escalation
        result = apply_sentiment_escalation(self.ticket, "esto es urgentísimo!!")
        self.ticket.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(self.ticket.prioridad, "MEDIUM")
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", side_effect=RuntimeError("boom"))
    def test_ai_failure_is_silent(self, mock_gen):
        from tickets_t.ai_hooks import apply_sentiment_escalation
        result = apply_sentiment_escalation(self.ticket, "algo pasó")
        self.ticket.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(self.ticket.prioridad, "MEDIUM")


class AiInsightsTests(TestCase):
    """Fase 4 — insights de negocio sobre métricas/CSAT."""

    URL = "/api/ai/insights/"

    def setUp(self):
        self.org = create_org("AIINS")  # Business por defecto
        self.admin = User.objects.create_user("ins_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("ins_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("ins_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        for i in range(3):
            Ticket.objects.create(
                reference=f"INS-{i}", titulo="Problema con el pago",
                descripcion="El pago falló nuevamente en el checkout.",
                creado_por=self.customer, organization=self.org, estado="OPEN")
        self.c = APIClient()

    @patch("ai.gateway.generate", return_value="- Tendencia: subieron los tickets de pago.")
    def test_admin_gets_insights_with_themes(self, mock_gen):
        self.c.force_authenticate(self.admin)
        r = self.c.post(self.URL)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data["insights"])
        terms = [t["term"] for t in r.data["snapshot"]["themes"]]
        self.assertIn("pago", terms)
        self.assertEqual(r.data["snapshot"]["totals"]["total"], 3)
        # el prompt lleva el snapshot (con los totales)
        prompt = mock_gen.call_args.kwargs["user_prompt"]
        self.assertIn("total", prompt)

    @patch("ai.gateway.generate", return_value="x")
    def test_agent_forbidden(self, mock_gen):
        self.c.force_authenticate(self.agent)
        self.assertEqual(self.c.post(self.URL).status_code, 403)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value="x")
    def test_customer_forbidden(self, mock_gen):
        self.c.force_authenticate(self.customer)
        self.assertEqual(self.c.post(self.URL).status_code, 403)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value="x")
    def test_free_plan_forbidden_with_upsell(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        self.c.force_authenticate(self.admin)
        r = self.c.post(self.URL)
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.data.get("upsell"))
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", side_effect=AiNotConfigured("no key"))
    def test_not_configured_returns_503(self, mock_gen):
        self.c.force_authenticate(self.admin)
        self.assertEqual(self.c.post(self.URL).status_code, 503)
