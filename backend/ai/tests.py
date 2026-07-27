from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tickets_t.models import Ticket, TicketMessage

User = get_user_model()

DRAFT = "Hola, gracias por escribir. Probá limpiar la caché y contanos si sigue."


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
