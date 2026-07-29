import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tickets_t.models import Ticket, TicketMessage
from ai import gateway
from ai.gateway import AiNotConfigured

User = get_user_model()

DRAFT = "Hola, gracias por escribir. Probá limpiar la caché y contanos si sigue."

# Helpers para los tests de run_async / cola (necesitan ser de módulo para que
# se resuelva su ruta punteada).
_RESULTS = []


def _append_result(x):
    _RESULTS.append(x)


def _noop_task(*args, **kwargs):
    pass


class RunAsyncQueueTests(SimpleTestCase):
    """Ruteo de run_async: inline (tests) / Celery (prod) / dispatcher genérico."""

    def test_inline_when_ai_async_false(self):
        from config.background import run_async
        box = []
        run_async(box.append, "x")  # AI_ASYNC=False por defecto en tests
        self.assertEqual(box, ["x"])

    @override_settings(AI_ASYNC=True, AI_TASK_QUEUE="celery")
    def test_enqueues_to_celery_when_configured(self):
        from config.background import run_async
        with patch("config.tasks.run_task.delay") as delay:
            run_async(_noop_task, 5, x=1)
        delay.assert_called_once()
        path, args, kwargs = delay.call_args.args
        self.assertTrue(path.endswith("ai.tests._noop_task"))
        self.assertEqual(args, [5])
        self.assertEqual(kwargs, {"x": 1})

    def test_run_task_dispatcher_imports_and_calls(self):
        from config.tasks import run_task
        _RESULTS.clear()
        run_task("ai.tests._append_result", ["hola"], {})
        self.assertEqual(_RESULTS, ["hola"])

    def test_run_task_registered_in_celery_app(self):
        # `config` no es una app de INSTALLED_APPS: si celery.py deja de importar
        # config.tasks, el worker rechazaría los mensajes ("unregistered task").
        from config.celery import app
        self.assertIn("config.run_task", app.tasks)
        self.assertEqual(app.conf.task_default_queue, "allsafe")


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
             patch("ai.gateway._gemini", return_value=("ok", None)) as mg, \
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


class AiTranslateTests(TestCase):
    """Fase 5.3 — traducción (multilingüe)."""

    URL = "/api/ai/translate/"

    def setUp(self):
        self.org = create_org("AITR")  # Business
        self.agent = User.objects.create_user("tr_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("tr_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.c = APIClient()

    @patch("ai.gateway.generate", return_value="Hello, how can I help you?")
    def test_agent_translates(self, mock_gen):
        self.c.force_authenticate(self.agent)
        r = self.c.post(self.URL, {"text": "Hola, ¿en qué te ayudo?", "target_lang": "en"},
                        format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["translated"], "Hello, how can I help you?")
        self.assertIn("Hola", mock_gen.call_args.kwargs["user_prompt"])

    @patch("ai.gateway.generate", return_value="x")
    def test_customer_forbidden(self, mock_gen):
        self.c.force_authenticate(self.customer)
        r = self.c.post(self.URL, {"text": "hi"}, format="json")
        self.assertEqual(r.status_code, 403)
        mock_gen.assert_not_called()

    @patch("ai.gateway.generate", return_value="x")
    def test_free_plan_forbidden_with_upsell(self, mock_gen):
        from billing.models import Plan
        from billing.testing import seed_plans
        seed_plans()
        self.org.subscription.plan = Plan.objects.get(key="free")
        self.org.subscription.save()
        self.c.force_authenticate(self.agent)
        r = self.c.post(self.URL, {"text": "hi"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.data.get("upsell"))
        mock_gen.assert_not_called()

    def test_missing_text_400(self):
        self.c.force_authenticate(self.agent)
        r = self.c.post(self.URL, {"target_lang": "en"}, format="json")
        self.assertEqual(r.status_code, 400)

    @patch("ai.gateway.generate", side_effect=AiNotConfigured("no key"))
    def test_not_configured_503(self, mock_gen):
        self.c.force_authenticate(self.agent)
        r = self.c.post(self.URL, {"text": "hola", "target_lang": "en"}, format="json")
        self.assertEqual(r.status_code, 503)


# --- Fase 0 guardrails: OrgAiSettings + rate limiting -------------------------

from django.core.cache import cache

from ai.models import OrgAiSettings
from ai import ratelimit, services


class OrgAiSettingsModelTests(TestCase):
    def test_get_for_returns_defaults_when_no_row(self):
        org = create_org("SETDEF")
        s = OrgAiSettings.get_for(org)
        self.assertIsNone(s.pk)  # default sin persistir
        self.assertTrue(s.enabled)
        self.assertEqual(s.rate_limit_per_min, 30)
        self.assertEqual(s.public_rate_limit_per_hour, 60)

    def test_get_for_returns_existing_row(self):
        org = create_org("SETROW")
        OrgAiSettings.objects.create(organization=org, rate_limit_per_min=5)
        s = OrgAiSettings.get_for(org)
        self.assertIsNotNone(s.pk)
        self.assertEqual(s.rate_limit_per_min, 5)

    def test_get_for_none_org_is_default(self):
        s = OrgAiSettings.get_for(None)
        self.assertIsNone(s.pk)
        self.assertTrue(s.enabled)


class AiEnabledOptInTests(TestCase):
    def setUp(self):
        self.org = create_org("OPTIN")  # Business por defecto

    def test_enabled_by_default(self):
        self.assertTrue(services.ai_enabled(self.org))

    def test_opt_out_disables_ai(self):
        OrgAiSettings.objects.create(organization=self.org, enabled=False)
        self.assertFalse(services.ai_enabled(self.org))


class RateLimitUnitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = create_org("RLUNIT")

    def test_allow_user_blocks_after_limit(self):
        OrgAiSettings.objects.create(organization=self.org, rate_limit_per_min=2)
        self.assertTrue(ratelimit.allow_user(self.org, 1))
        self.assertTrue(ratelimit.allow_user(self.org, 1))
        self.assertFalse(ratelimit.allow_user(self.org, 1))
        # otro usuario tiene su propio contador
        self.assertTrue(ratelimit.allow_user(self.org, 2))

    def test_allow_public_blocks_after_limit(self):
        OrgAiSettings.objects.create(organization=self.org, public_rate_limit_per_hour=1)
        self.assertTrue(ratelimit.allow_public(self.org))
        self.assertFalse(ratelimit.allow_public(self.org))

    def test_zero_limit_is_unlimited(self):
        OrgAiSettings.objects.create(
            organization=self.org, rate_limit_per_min=0, public_rate_limit_per_hour=0)
        for _ in range(50):
            self.assertTrue(ratelimit.allow_user(self.org, 9))
            self.assertTrue(ratelimit.allow_public(self.org))


class AiViewRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.c = APIClient()
        self.org = create_org("RLVIEW")
        self.agent = User.objects.create_user("rl_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.customer = User.objects.create_user("rl_cust", role="CUSTOMER",
                                                  organization=self.org, is_active=True)
        self.ticket = Ticket.objects.create(
            reference="RL-1", titulo="t", descripcion="d",
            creado_por=self.customer, asignado_a=self.agent,
            organization=self.org, estado="IN_PROGRESS")
        OrgAiSettings.objects.create(organization=self.org, rate_limit_per_min=1)

    @patch("ai.gateway.generate", return_value=DRAFT)
    def test_draft_view_429_over_limit(self, mock_gen):
        self.c.force_authenticate(self.agent)
        url = _url(self.ticket.id)
        r1 = self.c.post(url)
        self.assertEqual(r1.status_code, 200, r1.content)
        r2 = self.c.post(url)
        self.assertEqual(r2.status_code, 429)
        self.assertEqual(mock_gen.call_count, 1)  # no gastó IA en la 2da


class PublicDeflectionRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = create_org("RLPUB")
        from kb.models import Article
        Article.objects.create(
            organization=self.org, title="Reiniciar el panel",
            body="Para reiniciar el panel de reportes seguí estos pasos.",
            is_published=True)
        OrgAiSettings.objects.create(organization=self.org, public_rate_limit_per_hour=1)

    @patch("ai.services.answer_from_kb", return_value="Reiniciá así.")
    def test_deflection_stops_calling_ai_over_limit(self, mock_ans):
        from kb.deflection import run_deflection
        q = "como reiniciar el panel de reportes"
        first = run_deflection(self.org, q)
        self.assertTrue(first["resolved"])
        second = run_deflection(self.org, q)
        self.assertFalse(second["resolved"])
        self.assertTrue(second["available"])
        self.assertEqual(mock_ans.call_count, 1)  # 2da consulta no llegó a la IA


class OrgAiSettingsAdminApiTests(TestCase):
    URL = "/api/admin/ai/settings/"

    def setUp(self):
        self.c = APIClient()
        self.org = create_org("SETADMIN")
        self.admin = User.objects.create_user("set_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("set_agent", role="AGENT",
                                               organization=self.org, is_active=True)

    def test_get_returns_defaults(self):
        self.c.force_authenticate(self.admin)
        r = self.c.get(self.URL)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data["enabled"])
        self.assertEqual(r.data["public_rate_limit_per_hour"], 60)

    def test_patch_updates_and_persists(self):
        self.c.force_authenticate(self.admin)
        r = self.c.patch(self.URL, {"enabled": False, "rate_limit_per_min": 10},
                         format="json")
        self.assertEqual(r.status_code, 200, r.content)
        s = OrgAiSettings.objects.get(organization=self.org)
        self.assertFalse(s.enabled)
        self.assertEqual(s.rate_limit_per_min, 10)

    def test_agent_forbidden(self):
        self.c.force_authenticate(self.agent)
        self.assertEqual(self.c.get(self.URL).status_code, 403)
        self.assertEqual(self.c.patch(self.URL, {"enabled": False},
                                      format="json").status_code, 403)


# --- Fase 0: metering de costo + presupuesto mensual -------------------------

from decimal import Decimal

from ai import metering, pricing
from ai.models import AiUsage


class PricingTests(SimpleTestCase):
    def test_cost_for_known_model(self):
        # opus-4-8: $5/1M in, $25/1M out. 1000 in + 500 out.
        cost = pricing.cost_for("anthropic", "claude-opus-4-8", 1000, 500)
        self.assertEqual(cost, Decimal("0.005") + Decimal("0.0125"))

    def test_unknown_model_is_zero(self):
        self.assertEqual(pricing.cost_for("anthropic", "modelo-raro", 1000, 1000),
                         Decimal("0"))

    def test_env_override(self):
        with patch.dict(os.environ, {"AI_PRICE_OPENAI_GPT-X_IN": "2",
                                     "AI_PRICE_OPENAI_GPT-X_OUT": "8"}):
            self.assertEqual(pricing.cost_for("openai", "gpt-x", 1_000_000, 1_000_000),
                             Decimal("10"))


class MeteringTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = create_org("METER")

    def test_record_creates_row_and_sums_month(self):
        metering.record(self.org, provider="anthropic", model="claude-opus-4-8",
                        tier="quality", source="draft",
                        usage={"input": 1000, "output": 500})
        self.assertEqual(AiUsage.objects.filter(organization=self.org).count(), 1)
        self.assertEqual(metering.month_cost(self.org), Decimal("0.0175"))

    def test_record_noop_without_usage_or_org(self):
        metering.record(self.org, provider="anthropic", model="x", tier="fast",
                        source="triage", usage=None)
        metering.record(None, provider="anthropic", model="x", tier="fast",
                        source="triage", usage={"input": 10, "output": 10})
        self.assertEqual(AiUsage.objects.count(), 0)

    def test_over_budget(self):
        OrgAiSettings.objects.create(organization=self.org, monthly_budget_usd=Decimal("0.01"))
        self.assertFalse(metering.over_budget(self.org))
        metering.record(self.org, provider="anthropic", model="claude-opus-4-8",
                        tier="quality", source="draft",
                        usage={"input": 1000, "output": 500})  # $0.0175 > $0.01
        self.assertTrue(metering.over_budget(self.org))

    def test_zero_budget_never_over(self):
        OrgAiSettings.objects.create(organization=self.org, monthly_budget_usd=0)
        metering.record(self.org, provider="anthropic", model="claude-opus-4-8",
                        tier="quality", source="draft",
                        usage={"input": 10_000_000, "output": 10_000_000})
        self.assertFalse(metering.over_budget(self.org))


class GatewayMeteringTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = create_org("GWMETER")

    def test_generate_records_usage_when_org_given(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "anthropic"}), \
             patch("ai.gateway._anthropic",
                   return_value=("hola", {"input": 200, "output": 100})):
            out = gateway.generate(system="s", user_prompt="u", tier="quality",
                                   org=self.org, source="draft")
        self.assertEqual(out, "hola")
        row = AiUsage.objects.get(organization=self.org)
        self.assertEqual(row.input_tokens, 200)
        self.assertEqual(row.output_tokens, 100)
        self.assertEqual(row.source, "draft")

    def test_generate_no_metering_without_org(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "anthropic"}), \
             patch("ai.gateway._anthropic",
                   return_value=("hola", {"input": 200, "output": 100})):
            gateway.generate(system="s", user_prompt="u", tier="quality")
        self.assertEqual(AiUsage.objects.count(), 0)


class BudgetGatingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = create_org("BUDGET")  # Business por defecto

    def test_ai_disabled_when_over_budget(self):
        OrgAiSettings.objects.create(organization=self.org, monthly_budget_usd=Decimal("0.01"))
        self.assertTrue(services.ai_enabled(self.org))
        AiUsage.objects.create(organization=self.org, provider="anthropic",
                               model="claude-opus-4-8", cost_usd=Decimal("0.05"))
        cache.clear()  # invalida el gasto cacheado del mes
        self.assertFalse(services.ai_enabled(self.org))

    def test_admin_get_exposes_budget_and_cost(self):
        c = APIClient()
        admin = User.objects.create_user("bud_admin", role="ADMIN",
                                         organization=self.org, is_active=True)
        c.force_authenticate(admin)
        r = c.get("/api/admin/ai/settings/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("monthly_budget_usd", r.data)
        self.assertIn("current_month_cost_usd", r.data)
