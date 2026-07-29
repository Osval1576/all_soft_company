import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from tenancy.testing import create_org
from tickets_t.models import Ticket
from kb.models import Article
from inbound.models import Channel, ChannelAccount
from inbound import services

User = get_user_model()
WA = Channel.WHATSAPP


class HandleInboundTests(TestCase):
    def setUp(self):
        self.org = create_org("INB")  # Business por defecto
        ChannelAccount.objects.create(organization=self.org, channel=WA, external_id="PID1")

    @patch("ai.gateway.generate", return_value="NO_SE")  # KB no resuelve -> sin auto-reply
    def test_creates_ticket_contact_and_message(self, _g):
        r = services.handle_inbound_message(
            channel=WA, account_external_id="PID1",
            contact_external_id="549110000001", contact_name="Juan",
            text="Hola, no puedo entrar a mi cuenta")
        self.assertIsNotNone(r)
        self.assertTrue(r["created"])
        t = r["ticket"]
        self.assertEqual(t.organization_id, self.org.id)
        self.assertEqual(t.creado_por.username, f"whatsapp:{self.org.id}:549110000001")
        self.assertEqual(t.creado_por.role, "CUSTOMER")
        self.assertEqual(t.messages.count(), 1)
        self.assertIsNone(r["reply"])

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_threads_into_same_open_ticket(self, _g):
        r1 = services.handle_inbound_message(channel=WA, account_external_id="PID1",
                                             contact_external_id="549110", text="primero")
        r2 = services.handle_inbound_message(channel=WA, account_external_id="PID1",
                                             contact_external_id="549110", text="segundo")
        self.assertEqual(r1["ticket"].id, r2["ticket"].id)
        self.assertFalse(r2["created"])
        self.assertEqual(r2["ticket"].messages.count(), 2)

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_new_ticket_when_previous_closed(self, _g):
        r1 = services.handle_inbound_message(channel=WA, account_external_id="PID1",
                                             contact_external_id="549111", text="primero")
        t1 = r1["ticket"]
        t1.estado = "CLOSED"
        t1.save()
        r2 = services.handle_inbound_message(channel=WA, account_external_id="PID1",
                                             contact_external_id="549111", text="segundo")
        self.assertNotEqual(r1["ticket"].id, r2["ticket"].id)
        self.assertTrue(r2["created"])

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_unknown_account_ignored(self, _g):
        r = services.handle_inbound_message(channel=WA, account_external_id="NOPE",
                                            contact_external_id="549112", text="hola")
        self.assertIsNone(r)
        self.assertEqual(Ticket.objects.count(), 0)

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_multitenant_isolation(self, _g):
        org2 = create_org("INB2")
        ChannelAccount.objects.create(organization=org2, channel=WA, external_id="PID2")
        r1 = services.handle_inbound_message(channel=WA, account_external_id="PID1",
                                             contact_external_id="549113", text="a")
        r2 = services.handle_inbound_message(channel=WA, account_external_id="PID2",
                                             contact_external_id="549113", text="b")
        self.assertEqual(r1["ticket"].organization_id, self.org.id)
        self.assertEqual(r2["ticket"].organization_id, org2.id)

    def test_deflection_reply_when_kb_resolves(self):
        Article.objects.create(organization=self.org, title="Restablecer contraseña",
                               body="Andá a Ajustes y restablecé.", is_published=True)
        with patch("ai.gateway.generate",
                   return_value="Andá a Ajustes y restablecé tu contraseña."):
            r = services.handle_inbound_message(
                channel=WA, account_external_id="PID1", contact_external_id="549114",
                text="cómo restablezco mi contraseña?")
        self.assertIsNotNone(r["reply"])
        self.assertIn("restablecé", r["reply"])


class WhatsAppWebhookTests(TestCase):
    def setUp(self):
        self.org = create_org("INBW")
        ChannelAccount.objects.create(organization=self.org, channel=WA, external_id="PID")
        self.c = APIClient()

    def test_get_verification_ok(self):
        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "secret123"}):
            r = self.c.get("/api/inbound/whatsapp/", {"hub.mode": "subscribe",
                           "hub.verify_token": "secret123", "hub.challenge": "CHAL"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "CHAL")

    def test_get_verification_wrong_token(self):
        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "secret123"}):
            r = self.c.get("/api/inbound/whatsapp/", {"hub.mode": "subscribe",
                           "hub.verify_token": "WRONG", "hub.challenge": "CHAL"})
        self.assertEqual(r.status_code, 403)

    @patch("inbound.views.whatsapp.send_message")
    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_post_creates_ticket_from_payload(self, _g, _send):
        payload = {"entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "PID"},
            "contacts": [{"wa_id": "549120", "profile": {"name": "Ana"}}],
            "messages": [{"from": "549120", "type": "text",
                          "text": {"body": "hola necesito ayuda"}}],
        }}]}]}
        r = self.c.post("/api/inbound/whatsapp/", data=payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ticket.objects.filter(organization=self.org).count(), 1)


class ChannelAccountAdminTests(TestCase):
    BASE = "/api/admin/inbound/accounts/"

    def setUp(self):
        self.org = create_org("INBADM")
        self.admin = User.objects.create_user("inb_admin", role="ADMIN",
                                               organization=self.org, is_active=True)
        self.agent = User.objects.create_user("inb_agent", role="AGENT",
                                               organization=self.org, is_active=True)
        self.c = APIClient()

    def test_admin_creates_and_lists_scoped(self):
        self.c.force_authenticate(self.admin)
        r = self.c.post(self.BASE, {"channel": "whatsapp", "external_id": "PID_A"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(ChannelAccount.objects.get(id=r.data["id"]).organization_id, self.org.id)
        # de otra org no aparece
        other = create_org("INBADM2")
        ChannelAccount.objects.create(organization=other, channel=WA, external_id="PID_B")
        rows = self.c.get(self.BASE).data
        self.assertEqual([a["external_id"] for a in rows], ["PID_A"])

    def test_agent_forbidden(self):
        self.c.force_authenticate(self.agent)
        self.assertEqual(self.c.get(self.BASE).status_code, 403)


class EmailParseTests(TestCase):
    def test_normalizes_fields(self):
        from inbound.email import parse_inbound
        m = parse_inbound({
            "from": "Ana Pérez <ANA@cliente.com>",
            "to": "Soporte <SOPORTE@org.com>",
            "subject": "  No puedo entrar  ",
            "body-plain": "Hola, no puedo iniciar sesión.",
        })
        self.assertEqual(m["contact_external_id"], "ana@cliente.com")
        self.assertEqual(m["account_external_id"], "soporte@org.com")
        self.assertEqual(m["contact_name"], "Ana Pérez")
        self.assertEqual(m["subject"], "No puedo entrar")
        self.assertEqual(m["text"], "Hola, no puedo iniciar sesión.")


class EmailInboundTests(TestCase):
    """Email-to-ticket: ingesta con subject + webhook."""

    def setUp(self):
        self.org = create_org("INBEM")  # Business
        ChannelAccount.objects.create(organization=self.org, channel=Channel.EMAIL,
                                      external_id="soporte@inbem.com")
        self.c = APIClient()

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_subject_used_as_ticket_title(self, _g):
        r = services.handle_inbound_message(
            channel=Channel.EMAIL, account_external_id="soporte@inbem.com",
            contact_external_id="cliente@x.com", subject="Problema con la factura",
            text="No me llega la factura de este mes.")
        self.assertEqual(r["ticket"].titulo, "Problema con la factura")

    @patch("inbound.views.email_channel.send_reply")
    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_webhook_creates_ticket(self, _g, _send):
        payload = {"from": "Juan <juan@x.com>", "to": "soporte@inbem.com",
                   "subject": "Ayuda", "text": "Necesito ayuda con mi cuenta."}
        r = self.c.post("/api/inbound/email/", data=payload, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        t = Ticket.objects.get(organization=self.org)
        self.assertEqual(t.titulo, "Ayuda")
        self.assertEqual(t.creado_por.username, f"email:{self.org.id}:juan@x.com")

    @patch("inbound.views.email_channel.send_reply")
    def test_webhook_deflection_sends_reply(self, mock_send):
        Article.objects.create(organization=self.org, title="Restablecer contraseña",
                               body="Andá a Ajustes y restablecé.", is_published=True)
        with patch("ai.gateway.generate", return_value="Andá a Ajustes y restablecé."):
            payload = {"from": "a@x.com", "to": "soporte@inbem.com",
                       "subject": "contraseña", "text": "cómo restablezco mi contraseña?"}
            r = self.c.post("/api/inbound/email/", data=payload, format="json")
        self.assertEqual(r.status_code, 200)
        mock_send.assert_called_once()

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_webhook_missing_addresses_400(self, _g):
        r = self.c.post("/api/inbound/email/", data={"subject": "x", "text": "y"}, format="json")
        self.assertEqual(r.status_code, 400)

    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_webhook_rejects_wrong_token(self, _g):
        with patch.dict(os.environ, {"INBOUND_EMAIL_SECRET": "s3cr3t"}):
            payload = {"from": "a@x.com", "to": "soporte@inbem.com", "text": "hola"}
            r = self.c.post("/api/inbound/email/?token=WRONG", data=payload, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Ticket.objects.count(), 0)

    @patch("inbound.views.email_channel.send_reply")
    @patch("ai.gateway.generate", return_value="NO_SE")
    def test_webhook_unknown_account_no_ticket(self, _g, _send):
        payload = {"from": "a@x.com", "to": "otra@desconocida.com", "text": "hola"}
        r = self.c.post("/api/inbound/email/", data=payload, format="json")
        self.assertEqual(r.status_code, 200)  # 200 para que el proveedor no reintente
        self.assertEqual(Ticket.objects.count(), 0)
